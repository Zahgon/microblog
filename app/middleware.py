"""Request context middleware.

Everything that Flask used to set up in the request context is prepared here:
the request itself, the ``g`` namespace, the database session, the locale and
the logged in user. It also takes the role of Flask's ``before_request`` hook
and of its handler for unexpected errors.
"""
from starlette.requests import Request

from app import db
from app.context import set_request, reset_request
from app.i18n import set_locale, reset_locale, select_locale
from app.login import reset_current_user, load_user_from_session
from app.state import state


class RequestContextMiddleware:
    def __init__(self, app, before_request=None, error_handler=None):
        self.app = app
        self.before_request = before_request
        self.error_handler = error_handler

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        request_tokens = set_request(request)
        session_token = db.new_session_scope()
        locale_token = set_locale(select_locale())
        user_token = load_user_from_session()

        response_started = False

        async def send_wrapper(message):
            nonlocal response_started
            if message['type'] == 'http.response.start':
                response_started = True
            await send(message)

        try:
            if self.before_request is not None:
                self.before_request()
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            state.logger.error('Exception on %s [%s]', request.url.path,
                               request.method, exc_info=exc)
            if self.error_handler is None or response_started:
                raise
            response = await self.error_handler(request, exc)
            await response(scope, receive, send)
        finally:
            db.session.remove()
            reset_current_user(user_token)
            reset_locale(locale_token)
            db.reset_session_scope(session_token)
            reset_request(request_tokens)
