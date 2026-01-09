# 🗄️ Guía Técnica: Sistema de Base de Datos Espejo (Failover)

Este documento explica el funcionamiento, la conexión y los procedimientos de mantenimiento para el sistema de base de datos dual (**Principal + Espejo**) implementado en este proyecto.

---

## 🏗️ Arquitectura del Sistema

El sistema utiliza dos instancias independientes de PostgreSQL corriendo en contenedores Docker:

*   **DB Principal (`db_contenedor`)**: Base de datos primaria para lectura y escritura.
*   **DB Espejo (`db_espejo`)**: Base de datos de respaldo (Mirror) que toma el control si la principal falla.

### ¿Cómo se conectan?
La conexión es gestionada por un **Router Inteligente** en Django (`eventos/eventos/router.py`). 

> [!IMPORTANT]
> Los comandos de Docker a continuación asumen que el servicio de Django en tu `docker-compose.yml` se llama **`django_backend`**.

---

## 🧠 El Router Inteligente (Circuit Breaker)

El sistema actúa como un "director de tráfico" automático para evitar que la web se bloquee:

1.  **Estado Normal**: Django envía todas las consultas a la DB Principal.
2.  **Detección de Fallo**: Si la Principal no responde (**timeout de 2s**), el Router activa el *Circuit Breaker*.
3.  **Bloqueo de Seguridad (120s)**: Durante 2 minutos, todas las peticiones se dirigen a la DB Espejo **instantáneamente**, sin intentar siquiera "llamar" a la principal para ahorrar tiempo de espera.
4.  **Auto-Recuperación**: Pasado el tiempo, el sistema reintenta conectar a la Principal automáticamente.

---

## 🛠️ Procedimiento de Sincronización

### 1. Ubicación de Comandos
Todos los comandos deben ejecutarse desde la raíz del repositorio (`ProyectoWeb-Backend/`), donde se encuentra el archivo `docker-compose.yml`.

### 2. Aplicar Migraciones (Estructura)
Es vital que ambas bases tengan las mismas tablas. Ejecuta estos dos comandos:

```bash
# Migrar base principal
docker exec -it django_backend python manage.py migrate

# Migrar base espejo
docker exec -it django_backend python manage.py migrate --database=espejo
```

### 3. Clonar Datos (Sincronización de Información)
Para copiar los datos reales de la Principal a la Espejo (limpiando datos viejos):

```bash
# 1. Generar respaldo limpio de la Principal
docker exec -t db_contenedor pg_dump -U postgres -d sandia --clean --no-owner > backup_data.sql

# 2. Restaurar en la Espejo
cat backup_data.sql | docker exec -i db_espejo psql -U postgres -d sandia_espejo
```

---

## 🔌 Conexión desde el PC (Herramientas Externas)

Para conectar DBeaver, TablePlus o pgAdmin desde fuera de Docker:

| Característica | DB Principal | DB Espejo |
| :--- | :--- | :--- |
| **Host** | `localhost` | `localhost` |
| **Puerto Host** | `5432` | **`5433`** |
| **Base de Datos** | `sandia` | `sandia_espejo` |
| **Usuario / Pass** | `postgres / 123456` | `postgres / 123456` |

---

## 📝 Notas Importantes

*   **Rutas**: Si tu archivo `manage.py` no está en la raíz del contenedor, ajusta la ruta en el comando `docker exec`.
*   **Consistencia**: Los datos escritos en la Espejo durante una caída de la Principal **no se sincronizan solos** al volver. Si hay registros críticos, deben moverse manualmente usando el proceso de "Clonar Datos" mencionado arriba.
*   **Logs**: Monitorea el estado en tiempo real con:
    ```bash
    docker logs -f django_backend
    ```
    (Busca los prefijos 🛑 o 💥 para fallos y 🟢 para recuperaciones).