"""Database access layer.

This replaces Flask-SQLAlchemy with plain SQLAlchemy. The scoped session is
tied to a context variable that the request context middleware refreshes on
every request, so each request works with its own session, exactly like the
session that Flask-SQLAlchemy attached to the application context.
"""
from contextvars import ContextVar
from math import ceil

import sqlalchemy as sa
import sqlalchemy.orm as so
from starlette.exceptions import HTTPException

_session_scope = ContextVar('microblog_db_session', default=None)


class Model(so.DeclarativeBase):
    """Base class for all the models of the application."""


engine = None
session_factory = so.sessionmaker()
session = so.scoped_session(session_factory, scopefunc=_session_scope.get)

metadata = Model.metadata


def init_db(uri, engine_options=None):
    """Create the engine and bind the session factory to it."""
    global engine
    options = dict(engine_options or {})
    url = sa.engine.make_url(uri)
    if url.get_backend_name() == 'sqlite':
        if url.database in (None, '', ':memory:'):
            # keep a single connection alive, or every session would get its
            # own, empty, in-memory database
            options.setdefault('poolclass', sa.pool.StaticPool)
            options.setdefault('connect_args', {'check_same_thread': False})
    engine = sa.create_engine(url, **options)
    session_factory.configure(bind=engine)
    return engine


def new_session_scope():
    """Start a new session scope, returning its reset token."""
    return _session_scope.set(object())


def reset_session_scope(token):
    _session_scope.reset(token)


def create_all():
    Model.metadata.create_all(engine)


def drop_all():
    Model.metadata.drop_all(engine)


class Pagination:
    """The subset of the Flask-SQLAlchemy pagination object that is used."""

    def __init__(self, select, page, per_page, error_out=True,
                 max_per_page=None):
        if page is None or (page < 1 and not error_out):
            page = 1
        if per_page is None or (per_page < 1 and not error_out):
            per_page = 20
        if error_out and (page < 1 or per_page < 1):
            raise HTTPException(status_code=404)
        if max_per_page is not None:
            per_page = min(per_page, max_per_page)

        self.page = page
        self.per_page = per_page
        self.max_per_page = max_per_page

        items = session.execute(
            select.limit(per_page).offset((page - 1) * per_page)
        ).unique().scalars().all()
        if not items and page != 1 and error_out:
            raise HTTPException(status_code=404)
        self.items = list(items)

        sub = select.options(so.lazyload('*')).order_by(None).subquery()
        self.total = session.execute(
            sa.select(sa.func.count()).select_from(sub)).scalar()

    @property
    def pages(self):
        if self.total == 0 or self.total is None:
            return 0
        return int(ceil(self.total / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def prev_num(self):
        if not self.has_prev:
            return None
        return self.page - 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def next_num(self):
        if not self.has_next:
            return None
        return self.page + 1


def paginate(select, page=None, per_page=None, max_per_page=None,
             error_out=True):
    return Pagination(select, page=page, per_page=per_page,
                      max_per_page=max_per_page, error_out=error_out)


def first_or_404(select, description=None):
    """Return the first result of the query, or raise a 404 error."""
    value = session.scalars(select).first()
    if value is None:
        raise HTTPException(status_code=404, detail=description)
    return value


def get_or_404(model, ident, description=None):
    """Return the model instance with the given primary key, or raise a 404."""
    value = session.get(model, ident)
    if value is None:
        raise HTTPException(status_code=404, detail=description)
    return value
