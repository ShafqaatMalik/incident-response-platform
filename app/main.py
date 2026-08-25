from fastapi import Depends, FastAPI
from fastapi.responses import Response
from slowapi.middleware import SlowAPIMiddleware

from app.api.deps import require_api_key
from app.api.routes import documents, health
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.rate_limit import limiter
from app.observability.logging import RequestIdMiddleware, configure_logging
from app.observability.metrics import MetricsMiddleware, render_metrics


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Incident Response Platform — Document API", version="0.1.0")

    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestIdMiddleware)

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(documents.router)

    @app.get("/metrics", dependencies=[Depends(require_api_key)])
    async def metrics() -> Response:
        return render_metrics()

    return app


app = create_app()
