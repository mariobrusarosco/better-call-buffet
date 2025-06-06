Request Flow:
HTTP Request → FastAPI Router → Service Layer → Database
   ↑              ↑               ↑              ↑
   │              │               │              │
Client        API Layer     Business Logic    Data Layer

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
)
