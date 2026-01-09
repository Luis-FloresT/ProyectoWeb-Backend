import time
import socket
from django.db import connections
from django.db.utils import OperationalError, InterfaceError
from django.core.cache import cache

class ReplicationRouter:
    """
    Router with a 'Circuit Breaker' pattern.
    If 'default' is down, it's marked in cache for 120 seconds to avoid 
    waiting for connection timeouts on every request.
    """
    
    _CACHE_KEY_DOWN = "db_default_is_down"
    _CACHE_TIMEOUT = 120  # 2 minutes of "circuit open" (using espejo only)
    
    # Internal fast cache for a single request/short burst
    _last_check_time = 0
    _last_check_result = None
    _cache_duration = 1  # seconds

    def _get_active_db(self):
        """
        Determines the active database. Matches Circuit Breaker logic:
        1. Check if 'default' is marked as DOWN in global cache.
        2. If NOT marked down, try to connect (once).
        3. If connection fails, mark as DOWN for 2 minutes and use 'espejo'.
        4. If connection succeeds, use 'default'.
        """
        current_time = time.time()
        
        # 🟢 STEP 1: Check Global Circuit Breaker (Cache)
        if cache.get(self._CACHE_KEY_DOWN):
            # The circuit is OPEN (Default is down). Use espejo immediately.
            if self._last_check_result != 'espejo':
                print("🛑 [Circuit Breaker] Base 'default' marcada como CAÍDA. Usando 'espejo' directamente.")
                self._last_check_result = 'espejo'
            return 'espejo'

        # 🟢 STEP 2: Use internal request-level cache if available
        if (self._last_check_result is not None and 
            current_time - self._last_check_time < self._cache_duration):
            return self._last_check_result
        
        # 🟢 STEP 3: Attempt connection to 'default'
        try:
            db = connections['default']
            if db.connection is not None:
                db.close_if_unusable_or_obsolete()
            
            # This triggers the 2s timeout from settings.py if it's down
            db.ensure_connection()
            
            # If we were in 'espejo' mode and now we are back, log it
            if self._last_check_result == 'espejo':
                print("🟢 [Circuit Breaker] Conexión reestablecida con 'default'.")

            self._last_check_time = current_time
            self._last_check_result = 'default'
            return 'default'
            
        except (OperationalError, InterfaceError, socket.timeout, OSError, Exception) as e:
            # 🔴 STEP 4: Activate Circuit Breaker
            print(f"💥 [Circuit Breaker] Fallo en 'default' ({type(e).__name__}). Bloqueando reintentos por {self._CACHE_TIMEOUT}s.")
            
            # Mark as down in global cache for 120 seconds
            cache.set(self._CACHE_KEY_DOWN, True, self._CACHE_TIMEOUT)
            
            try:
                connections['default'].close()
            except:
                pass
            
            self._last_check_time = current_time
            self._last_check_result = 'espejo'
            return 'espejo'

    def db_for_read(self, model, **hints):
        return self._get_active_db()

    def db_for_write(self, model, **hints):
        return self._get_active_db()

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True
