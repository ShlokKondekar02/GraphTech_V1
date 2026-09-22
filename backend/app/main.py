from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.api.router import api_router
from app.schemas.health import HealthResponse


def create_app() -> FastAPI:
    setup_logging()
    logger.info("Initializing GraphTech Backend Application...")

    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="Backend API for GraphTech DiagramGPT Architecture Studio",
        debug=settings.DEBUG,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root health endpoint
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def root_health() -> HealthResponse:
        return HealthResponse(status="ok")

    # Include API Routers (/api/health, /api/auth, /api/diagrams, etc.)
    app.include_router(api_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
