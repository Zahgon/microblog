#!/bin/bash
# this script is used to boot a Docker container
while true; do
    alembic upgrade head
    if [[ "$?" == "0" ]]; then
        break
    fi
    echo Deploy command failed, retrying in 5 secs...
    sleep 5
done
exec gunicorn -b :5000 -k uvicorn.workers.UvicornWorker --access-logfile - --error-logfile - microblog:app
