import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
import os

from elasticsearch import Elasticsearch
from fastapi import FastAPI
from redis import Redis
import rq
from starlette.staticfiles import StaticFiles

from config import Config
from app import db
from app.i18n import lazy_gettext as _l
from app.login import login
from app.middleware import RequestContextMiddleware
from app.session import SessionMiddleware
from app.state import state

basedir = os.path.abspath(os.path.dirname(__file__))

login.login_view = 'auth.login'
login.login_message = _l('Please log in to access this page.')


def create_app(config_class=Config):
    app = FastAPI(title='Microblog')
    state.app = app
    config = state.init_config(config_class)

    db.init_db(config['DATABASE_URI'])
    state.elasticsearch = Elasticsearch([config['ELASTICSEARCH_URL']]) \
        if config['ELASTICSEARCH_URL'] else None
    state.redis = Redis.from_url(config['REDIS_URL'])
    state.task_queue = rq.Queue('microblog-tasks', connection=state.redis)

    app.mount('/static', StaticFiles(directory=os.path.join(basedir,
                                                            'static')),
              name='static')

    from app.errors import register_error_handlers
    register_error_handlers(app)

    from app.auth import bp as auth_bp
    app.include_router(auth_bp, prefix='/auth')

    from app.main import bp as main_bp
    app.include_router(main_bp)

    from app.api import bp as api_bp
    app.include_router(api_bp, prefix='/api')

    from app.errors.handlers import internal_error
    from app.main.routes import before_request
    app.add_middleware(RequestContextMiddleware,
                       before_request=before_request,
                       error_handler=internal_error)
    app.add_middleware(SessionMiddleware, secret_key=config['SECRET_KEY'],
                       session_cookie='session')

    if not config['DEBUG'] and not config['TESTING']:
        if config['MAIL_SERVER']:
            auth = None
            if config['MAIL_USERNAME'] or config['MAIL_PASSWORD']:
                auth = (config['MAIL_USERNAME'], config['MAIL_PASSWORD'])
            secure = None
            if config['MAIL_USE_TLS']:
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(config['MAIL_SERVER'], config['MAIL_PORT']),
                fromaddr='no-reply@' + config['MAIL_SERVER'],
                toaddrs=config['ADMINS'], subject='Microblog Failure',
                credentials=auth, secure=secure)
            mail_handler.setLevel(logging.ERROR)
            state.logger.addHandler(mail_handler)

        if config['LOG_TO_STDOUT']:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)
            state.logger.addHandler(stream_handler)
        else:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            file_handler = RotatingFileHandler('logs/microblog.log',
                                               maxBytes=10240, backupCount=10)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s '
                '[in %(pathname)s:%(lineno)d]'))
            file_handler.setLevel(logging.INFO)
            state.logger.addHandler(file_handler)

        state.logger.setLevel(logging.INFO)
        state.logger.info('Microblog startup')

    return app


from app import models
