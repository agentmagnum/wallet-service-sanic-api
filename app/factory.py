from __future__ import annotations

from sqlalchemy import text
from sanic import Sanic, json

from app.api import admin_blueprint, auth_blueprint, user_blueprint, webhook_blueprint
from app.config import get_settings
from app.db import create_engine_and_session_factory
from app.errors import register_error_handlers
from app.rate_limit import InMemoryRateLimiter


def create_app() -> Sanic:
    settings = get_settings()
    app = Sanic(settings.app_name)
    app.ctx.settings = settings
    app.ctx.rate_limiter = InMemoryRateLimiter()

    @app.before_server_start
    async def setup_database(app: Sanic):
        engine, session_factory = create_engine_and_session_factory(settings)
        app.ctx.engine = engine
        app.ctx.session_factory = session_factory

    @app.after_server_stop
    async def close_database(app: Sanic):
        await app.ctx.engine.dispose()

    @app.get("/healthz")
    async def healthcheck(request):
        async with request.app.ctx.session_factory() as session:
            await session.execute(text("SELECT 1"))
        return json({"status": "ok"})

    app.blueprint(auth_blueprint)
    app.blueprint(user_blueprint)
    app.blueprint(admin_blueprint)
    app.blueprint(webhook_blueprint)

    register_error_handlers(app)
    return app
