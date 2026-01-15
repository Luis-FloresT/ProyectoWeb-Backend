import time
import socket
import subprocess
import sys
import os
from django.db import connections
from django.db.utils import OperationalError, InterfaceError
from django.core.cache import cache

class ReplicationRouter:
    """
    Router con patrón 'Circuit Breaker' (Disyuntor).
    Si 'default' está caído, se marca en caché por 120 segundos para evitar 
    esperar tiempos de conexión en cada solicitud.
    """
    
    _CACHE_KEY_DOWN = "db_default_is_down"
    _CACHE_TIMEOUT = 120  # 2 minutos de "circuito abierto" (usando solo 'espejo')
    
    # Caché interno rápido para una sola solicitud o ráfaga corta
    _last_check_time = 0
    _last_check_result = None
    _cache_duration = 1  # segundos
    _SYNC_LOCK_KEY = "db_sync_in_progress"
    _SYNC_LOCK_TIMEOUT = 600  # 10 minutos máximo por proceso de reserva

    def _get_active_db(self):
        
        current_time = time.time()
        
        # 🟢 PASO 1: Verificar el Circuit Breaker Global (Caché)
        if cache.get(self._CACHE_KEY_DOWN):
            # El circuito está ABIERTO (Default está caído). Usar 'espejo' de inmediato.
            if self._last_check_result != 'espejo':
                print("🛑 [Circuit Breaker] Base 'default' marcada como CAÍDA. Usando 'espejo' directamente.")
                self._last_check_result = 'espejo'
            return 'espejo'

        # 🟢 PASO 2: Usar caché interno a nivel de solicitud si está disponible
        if (self._last_check_result is not None and 
            current_time - self._last_check_time < self._cache_duration):
            return self._last_check_result
        
        # 🟢 PASO 3: Intentar conexión a 'default'
        try:
            db = connections['default']
            if db.connection is not None:
                db.close_if_unusable_or_obsolete()
            
            # Esto activa el tiempo de espera de 2s de settings.py si está caído
            db.ensure_connection()
            
            # Si estábamos en modo 'espejo' y ahora volvimos, registrarlo y sincronizar
            if self._last_check_result == 'espejo':
                print("🟢 [Circuit Breaker] Conexión reestablecida con 'default'. Disparando sincronización...")
                self._trigger_sync()

            self._last_check_time = current_time
            self._last_check_result = 'default'
            return 'default'
            
        except (OperationalError, InterfaceError, socket.timeout, OSError, Exception) as e:
            # 🔴 PASO 4: Activar el Circuit Breaker
            print(f"💥 [Circuit Breaker] Fallo en 'default' ({type(e).__name__}). Bloqueando reintentos por {self._CACHE_TIMEOUT}s.")
            
            # Marcar como caído en la caché global por 120 segundos
            cache.set(self._CACHE_KEY_DOWN, True, self._CACHE_TIMEOUT)
            
            try:
                connections['default'].close()
            except:
                pass
            
            self._last_check_time = current_time
            self._last_check_result = 'espejo'
            return 'espejo'

    def _trigger_sync(self):
        """
        Lanza el comando de sincronización en segundo plano si no hay uno ya en curso.
        """
        if cache.get(self._SYNC_LOCK_KEY):
            print("⏳ [Sync] Ya hay una sincronización en curso. Omitiendo disparador.")
            return

        # Marcar inicio de sincronización (bloqueo preventivo)
        cache.set(self._SYNC_LOCK_KEY, True, self._SYNC_LOCK_TIMEOUT)
        
        try:
            # Construir ruta al manage.py
            # Asumimos que manege.py está en el mismo nivel o superior
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            manage_py = os.path.join(base_dir, 'manage.py')
            
            # Ejecutar en segundo plano usando Popen
            # Python -u para salida sin buffer (útil para logs)
            subprocess.Popen(
                [sys.executable, manage_py, 'sync_databases'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True # En Linux, para que el proceso viva si el padre muere
            )
            print("🚀 [Sync] Proceso de sincronización lanzado en segundo plano.")
            
        except Exception as e:
            print(f"❌ [Sync] Error al lanzar el proceso: {e}")
            cache.delete(self._SYNC_LOCK_KEY)

    def db_for_read(self, model, **hints):
        return self._get_active_db()

    def db_for_write(self, model, **hints):
        return self._get_active_db()

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True
