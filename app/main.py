from __future__ import annotations

from app.factory import create_app


app = create_app()


if __name__ == "__main__":
    settings = app.ctx.settings
    app.run(
        host=settings.app_host,
        port=settings.app_port,
        debug=settings.debug,
        access_log=True,
        auto_reload=False,
    )
