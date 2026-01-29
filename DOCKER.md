# Stack de contenedores (Backend + Frontend + DB principal + DB espejo)

## Servicios
- db: PostgreSQL 15, base `sandia`, puerto 5432 (expuesto).
- db_espejo: PostgreSQL 15, base `sandia_espejo`, puerto 5433 (expuesto). Se usa como espejo/lectura; no replica automáticamente, ver sección de sincronización.
- backend: Django (puerto 8000), depende de db y db_espejo.
- frontend: Vite dev server (puerto 5173), depende de backend.

## Puertos locales
- 5432 → db (principal)
- 5433 → db_espejo (espejo)
- 8000 → backend Django
- 5173 → frontend Vite

## Requisitos previos
- Docker Desktop instalado y corriendo
- Git (si clonas el repo)

## Pasos para ejecutar los contenedores

### 1. Abrir terminal en la carpeta del proyecto
```bash
cd "c:\Users\adolf\OneDrive\Escritorio\Proyecto WEB II\BACK"
```

### 2. Construir y levantar todos los contenedores
```bash
docker-compose up --build
```
Esto:
- Construye las imágenes del backend y frontend
- Descarga PostgreSQL 15 si no la tienes
- Levanta los 4 contenedores (db, db_espejo, backend, frontend)
- Muestra los logs en tiempo real

### 3. Ejecutar en segundo plano (modo detached)
Si prefieres que no bloquee la terminal:
```bash
docker-compose up -d --build
```

### 4. Ver los logs
```bash
docker-compose logs -f
```
Para ver logs de un servicio específico:
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 5. Verificar que todo está corriendo
```bash
docker-compose ps
```
Deberías ver los 4 servicios con estado "Up".

## Credenciales por defecto
- Usuario: `postgres`
- Password: `123456`
- DB principal: `sandia`
- DB espejo: `sandia_espejo`

## Variables de entorno clave
Ajusta en docker-compose.yml o con un .env referenciado:
- `DB_HOST` (backend) → `db`
- `DB_NAME` (backend) → `sandia`
- `DB_USER` / `DB_PASSWORD` (backend) → credenciales Postgres
- `DB_PORT` → `5432`

## Sincronizar la base espejo
El contenedor `db_espejo` arranca vacío. Para clonarla desde la principal en caliente:
```bash
docker exec db_contenedor pg_dump -U postgres sandia \
  | docker exec -i db_espejo psql -U postgres sandia_espejo
```
Esto hace un dump lógico y lo restaura en el espejo. Repite cuando necesites refrescar el espejo.

## Acceder a los servicios
Una vez levantados los contenedores:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **Admin Django**: http://localhost:8000/admin
- **DB Principal**: `localhost:5432` (usuario: postgres, contraseña: 123456)
- **DB Espejo**: `localhost:5433` (usuario: postgres, contraseña: 123456)

## Detener los contenedores
```bash
docker-compose down
```
Para eliminar también los volúmenes (BORRA LOS DATOS):
```bash
docker-compose down -v
```

## Reiniciar un servicio específico
```bash
docker-compose restart backend
docker-compose restart frontend
```

## Ejecutar comandos dentro de los contenedores
Crear superusuario de Django:
```bash
docker exec -it django_backend python manage.py createsuperuser
```

Aplicar migraciones:
```bash
docker exec -it django_backend python manage.py migrate
```

Acceder a la shell de PostgreSQL (principal):
```bash
docker exec -it db_contenedor psql -U postgres -d sandia
```

Acceder a la shell de PostgreSQL (espejo):
```bash
docker exec -it db_espejo psql -U postgres -d sandia_espejo
```

## Conexión externa
- Principal: host `localhost`, puerto `5432`, db `sandia`, user `postgres`, pass `123456`.
- Espejo: host `localhost`, puerto `5433`, db `sandia_espejo`, user `postgres`, pass `123456`.

## Notas
- Los volúmenes `postgres_data` y `postgres_espejo_data` persisten los datos.
- El backend se monta con bind mount `./ProyectoWeb-Backend:/app` para desarrollo; cualquier cambio local se refleja en el contenedor.
- Si quieres servir frontend estático en lugar de Vite dev, se puede añadir una imagen Nginx con el build (`npm run build`) y cambiar el servicio `frontend` para servir `/dist` en puerto 80.
