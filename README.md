# TamizAI Backend

Backend para un MVP educativo de apoyo al tamizaje temprano de dificultades de lectoescritura. No realiza diagnóstico clínico.

## Stack

- FastAPI
- SQLAlchemy 2.x + Alembic
- PostgreSQL
- JWT access token (8h) + refresh token rotation
- Azure Blob Storage, Azure OCR, Azure Speech
- Passlib (pbkdf2_sha256)

## Estructura (Hexagonal / DDD)

```
app/
  iam/              # Bounded Context: Identity & Access Management
    domain/         #   User, RefreshToken, PasswordResetToken
    application/    #   ports, use cases, services
    infrastructure/ #   models ORM, repositories, adapters
    presentation/   #   routes, schemas
  school/           # Bounded Context: School management
    domain/         #   HomeroomTeacher, Classroom, GradeLevel, Section
    application/    #   ports, use cases
    infrastructure/ #   models ORM, repositories
    presentation/   #   routes, schemas
    modules/        #   legacy Student module (to migrate)
  assessment/       # Bounded Context: Assessment sessions
    modules/        #   sessions, ai_processing, evidences, results
  core/             # settings, security, email
  db/               # session factory, base model imports
  models/           # legacy ORM stubs (to remove)
  dependencies/     # FastAPI dependencies (auth)
alembic/
tests/
```

## Requisitos

- Docker Desktop
- Git

## Setup rápido

```bash
# 1. Clonar y entrar
git clone <repo-url> tamizai
cd tamizai/backend

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con los valores necesarios (ver sección Variables)

# 3. Iniciar PostgreSQL y construir la API
docker compose up --build -d

# 4. Ejecutar migraciones de base de datos
docker compose run --rm api alembic upgrade head

# 5. Verificar que funciona
docker compose logs -f api
# Deberías ver: "Application startup complete."
```

## Endpoints

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| POST | `/api/v1/auth/signup` | Registrar docente + teacher profile | No |
| POST | `/api/v1/auth/signin` | Iniciar sesión | No |
| POST | `/api/v1/auth/refresh` | Renovar access token | No |
| POST | `/api/v1/auth/signout` | Cerrar sesión (revoca refresh token) | No |
| POST | `/api/v1/auth/forgot-password` | Solicitar reset de contraseña | No |
| PATCH | `/api/v1/auth/reset-password` | Resetear contraseña con token | No |
| GET | `/api/v1/teachers/me` | Obtener perfil del docente | JWT |
| PUT | `/api/v1/teachers/me` | Actualizar perfil del docente | JWT |
| POST | `/api/v1/classrooms` | Crear aula | JWT |
| GET | `/api/v1/classrooms` | Listar aulas del docente | JWT |
| GET | `/api/v1/classrooms/{id}` | Obtener aula por ID | JWT |
| PUT | `/api/v1/classrooms/{id}` | Actualizar aula | JWT |
| DELETE | `/api/v1/classrooms/{id}` | Eliminar aula | JWT |
| GET | `/health` | Health check | No |

## Variables de entorno clave

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/early_literacy
ACCESS_TOKEN_SECRET=change-this-access-secret
REFRESH_TOKEN_SECRET=change-this-refresh-secret

# SMTP para recuperación de contraseña (opcional en dev)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tu-correo@gmail.com
SMTP_PASSWORD=contraseña-de-aplicacion
SMTP_USE_TLS=True
EMAIL_FROM=tu-correo@gmail.com

# Azure (opcional para features de IA)
AZURE_BLOB_CONNECTION_STRING=
AZURE_VISION_ENDPOINT=
AZURE_VISION_KEY=
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=
```

## Password reset (desarrollo)

En modo dev (`SMTP_HOST=localhost` por defecto), el token de reset se imprime en los logs:

```bash
docker compose logs -f api
# Buscar: "DEV MODE: Email suppressed"
```

Copias el token y lo usas:

```bash
curl -X PATCH http://localhost:8000/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{"token": "<el-token>", "new_password": "mi-nueva-pass"}'
```

## Comandos útiles

```bash
# Ver logs
docker compose logs -f api

# Reconstruir imagen tras cambios
docker compose up --build -d

# Ejecutar migraciones
docker compose run --rm api alembic upgrade head

# Crear nueva migración (autogenerate)
docker compose run --rm api alembic revision --autogenerate -m "descripcion"

# Acceder a la DB
docker compose exec db psql -U postgres -d early_literacy

# Ver rutas registradas
docker compose run --rm api python -c "from app.main import app; [print(r.path, r.methods) for r in app.routes]"

# Detener todo
docker compose down

# Detener y borrar volúmenes (reinicio limpio)
docker compose down -v
```

## Notas de alcance

- No hay módulo para padres ni especialistas.
- No hay diagnóstico automatizado.
- No hay LLM ni modelo predictivo propio.
- Los scores y flags son métricas de apoyo prudentes, no conclusiones clínicas.
