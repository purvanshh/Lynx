from fastapi import FastAPI

from lynx.api.routes.health import router as health_router
from lynx.api.routes.participants import router as participants_router
from lynx.api.routes.sessions import router as sessions_router
from lynx.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.include_router(health_router)
app.include_router(sessions_router)
app.include_router(participants_router)
