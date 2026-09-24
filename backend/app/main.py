from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.errors import register_error_handlers
from app.routers.activity import router as activity_router
from app.routers.auth import router as auth_router
from app.routers.comments import router as comments_router
from app.routers.dashboard import router as dashboard_router
from app.routers.tickets import router as tickets_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Support Ticketing Portal",
        version="1.0.0",
        description="Customer support ticketing with advisory AI triage.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    app.include_router(auth_router)
    app.include_router(tickets_router)
    app.include_router(comments_router)
    app.include_router(activity_router)
    app.include_router(dashboard_router)

    @app.get("/api/health", tags=["meta"], summary="Liveness probe")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
