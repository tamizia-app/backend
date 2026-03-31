# Early Literacy MVP Backend

Backend para un MVP educativo de apoyo al tamizaje temprano de dificultades de lectoescritura. Este sistema **no realiza diagnóstico clínico** y solo entrega indicadores de apoyo para docentes.

## Stack

- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- JWT access token + refresh token
- Azure Blob Storage
- Azure OCR y Azure Speech encapsulados en adapters

## Estructura

```text
app/
  api/            # routers HTTP
  core/           # settings y seguridad
  db/             # session factory
  domain/         # enums de dominio
  models/         # modelos ORM
  schemas/        # DTOs Pydantic
  services/       # lógica de negocio e integraciones
  dependencies/   # dependencias FastAPI
  scripts/        # utilidades operativas
alembic/
tests/
```

## Arranque local

1. Copia `.env.example` a `.env`.
2. Levanta PostgreSQL y la app:

```bash
docker compose up --build
```

3. Ejecuta migraciones:

```bash
alembic upgrade head
```

4. Crea un docente inicial:

```bash
python -m app.scripts.bootstrap_user --email docente@example.com --password secret123 --full-name "Docente Demo" --institution-name "Colegio Demo"
```

5. Abre la documentación:

- Swagger UI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## Variables clave

- `DATABASE_URL`
- `ACCESS_TOKEN_SECRET`
- `REFRESH_TOKEN_SECRET`
- `AZURE_BLOB_CONNECTION_STRING`
- `AZURE_VISION_ENDPOINT`
- `AZURE_VISION_KEY`
- `AZURE_SPEECH_KEY`
- `AZURE_SPEECH_REGION`

## Notas de alcance

- No hay módulo para padres ni especialistas.
- No hay diagnóstico automatizado.
- No hay LLM ni modelo predictivo propio.
- Los scores y flags son métricas de apoyo prudentes, no conclusiones clínicas.

