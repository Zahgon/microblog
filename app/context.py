"""Per-request context.

Flask kept the current request, the ``g`` namespace and the session in thread
local proxies. The same job is done here with context variables, which are set
by the request context middleware installed in ``create_app()``.
"""
from contextvars import ContextVar
from types import SimpleNamespace

_request_ctx = ContextVar('microblog_request', default=None)
_g_ctx = ContextVar('microblog_g', default=None)


def set_request(request):
    """Bind a request to the current context, returning the reset tokens."""
    return _request_ctx.set(request), _g_ctx.set(SimpleNamespace())


def reset_request(tokens):
    request_token, g_token = tokens
    _request_ctx.reset(request_token)
    _g_ctx.reset(g_token)


def get_request():
    return _request_ctx.get()


def get_g():
    g = _g_ctx.get()
    if g is None:
        g = SimpleNamespace()
        _g_ctx.set(g)
    return g


def get_session():
    """Return the session of the current request, or an empty dict."""
    request = get_request()
    if request is None:
        return {}
    return request.session


class GProxy:
    """Proxy that forwards attribute access to the current ``g`` namespace."""

    def __getattr__(self, name):
        return getattr(get_g(), name)

    def __setattr__(self, name, value):
        setattr(get_g(), name, value)

    def __delattr__(self, name):
        delattr(get_g(), name)

    def __contains__(self, name):
        return hasattr(get_g(), name)


g = GProxy()


def flash(message):
    """Store a message to be shown on the next rendered page."""
    session = get_session()
    session.setdefault('_flashes', []).append(str(message))


def get_flashed_messages():
    """Return and clear the messages stored by ``flash()``."""
    return get_session().pop('_flashes', [])
