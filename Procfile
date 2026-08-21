web: alembic upgrade head; python -m app.cli translate compile; gunicorn -k uvicorn.workers.UvicornWorker microblog:app
worker: rq worker microblog-tasks
