"""Application wide state.

FastAPI has no equivalent of Flask's application context, so the objects that
used to be reachable through ``current_app`` (the configuration, the
Elasticsearch client, the Redis connection, the task queue and the logger) are
kept in this single container, which is populated by ``create_app()``.
"""
import logging


class AppState:
    def __init__(self):
        self.app = None
        self.config = {}
        self.elasticsearch = None
        self.redis = None
        self.task_queue = None
        self.logger = logging.getLogger('microblog')

    def init_config(self, config_class):
        self.config.clear()
        self.config.update({key: getattr(config_class, key)
                            for key in dir(config_class) if key.isupper()})
        return self.config


state = AppState()
