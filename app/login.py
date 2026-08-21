"""User sessions.

This module provides the parts of Flask-Login that the application used: the
``current_user`` proxy, the functions that log users in and out, and the
dependency that protects the views that require an authenticated user.
"""
from contextvars import ContextVar

from app.context import get_session, flash, get_request

USER_ID_KEY = '_user_id'
REMEMBER_KEY = '_remember'

_current_user_ctx = ContextVar('microblog_current_user', default=None)


class UserMixin:
    """Default implementations of the properties expected from a user."""

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


class AnonymousUser:
    """The user of a request that does not have anybody logged in."""

    @property
    def is_authenticated(self):
        return False

    @property
    def is_active(self):
        return False

    @property
    def is_anonymous(self):
        return True

    def get_id(self):
        return None

    def __repr__(self):
        return '<AnonymousUser>'


class AuthRedirect(Exception):
    """Raised when an anonymous user requests a page that needs a login."""

    def __init__(self, location):
        super().__init__(location)
        self.location = location


class LoginManager:
    """Keeps the user loader and the settings of the login redirect."""

    def __init__(self):
        self.login_view = None
        self.login_message = None
        self.anonymous_user = AnonymousUser
        self._user_callback = None

    def user_loader(self, callback):
        self._user_callback = callback
        return callback

    def load_user(self, user_id):
        if self._user_callback is None:
            raise RuntimeError('No user loader has been installed.')
        return self._user_callback(user_id)


login = LoginManager()


def set_current_user(user):
    """Bind a user to the current context, returning the reset token."""
    return _current_user_ctx.set(user)


def reset_current_user(token):
    _current_user_ctx.reset(token)


def get_current_user():
    user = _current_user_ctx.get()
    if user is None:
        user = login.anonymous_user()
        _current_user_ctx.set(user)
    return user


def load_user_from_session():
    """Restore the logged in user of the current request from its session."""
    user = None
    user_id = get_session().get(USER_ID_KEY)
    if user_id is not None:
        try:
            user = login.load_user(user_id)
        except (TypeError, ValueError):
            user = None
    if user is None:
        user = login.anonymous_user()
    return set_current_user(user)


class CurrentUserProxy:
    """Proxy that forwards everything to the user of the current request."""

    __slots__ = ()

    @property
    def __class__(self):
        return type(get_current_user())

    def _get_current_object(self):
        return get_current_user()

    def __getattr__(self, name):
        return getattr(get_current_user(), name)

    def __setattr__(self, name, value):
        setattr(get_current_user(), name, value)

    def __delattr__(self, name):
        delattr(get_current_user(), name)

    def __eq__(self, other):
        if isinstance(other, CurrentUserProxy):
            other = other._get_current_object()
        return get_current_user() == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(get_current_user())

    def __bool__(self):
        return bool(get_current_user())

    def __repr__(self):
        return repr(get_current_user())


current_user = CurrentUserProxy()


def login_user(user, remember=False):
    """Log a user in, storing its identity in the session."""
    session = get_session()
    session[USER_ID_KEY] = user.get_id()
    session[REMEMBER_KEY] = bool(remember)
    set_current_user(user)
    return True


def logout_user():
    """Log the current user out."""
    session = get_session()
    session.pop(USER_ID_KEY, None)
    session.pop(REMEMBER_KEY, None)
    set_current_user(login.anonymous_user())
    return True


def make_next_param():
    """Return the path of the current request, to return to it after login."""
    request = get_request()
    if request is None:
        return None
    next_param = request.url.path
    if request.url.query:
        next_param = f'{next_param}?{request.url.query}'
    return next_param


async def login_required():
    """Dependency that only lets authenticated users through."""
    from app.urls import url_for

    user = get_current_user()
    if not user.is_authenticated:
        if login.login_message:
            flash(login.login_message)
        next_param = make_next_param()
        values = {'next': next_param} if next_param else {}
        raise AuthRedirect(url_for(login.login_view, **values))
    return user
