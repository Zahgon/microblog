from starlette.exceptions import HTTPException

from app.login import AuthRedirect


def register_error_handlers(app):
    """Install the error handlers of the application."""
    from app.errors import handlers

    app.add_exception_handler(HTTPException, handlers.http_exception)
    app.add_exception_handler(AuthRedirect, handlers.auth_redirect)
    return app
