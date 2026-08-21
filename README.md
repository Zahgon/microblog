# Welcome to Microblog!

This is an example application featured in my [Flask Mega-Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world). See the tutorial for instructions on how to work with it.

The version of the application featured in this repository corresponds to the 2024 edition of the Flask Mega-Tutorial. You can find the 2018 and 2021 versions of the code [here](https://github.com/miguelgrinberg/microblog-2018). And if for any strange reason you are interested in the original code, dating back to 2012, that is [here](https://github.com/miguelgrinberg/microblog-2012).

## Running the application

This version of the application has been ported from Flask to FastAPI, so it
is run with an ASGI server instead of the Flask development server:

```bash
uvicorn microblog:app --reload
```

The commands that were provided by the Flask CLI are now available through the
command line interface of the application, and the database migrations are
applied with Alembic:

```bash
alembic upgrade head            # was: flask db upgrade
python -m app.cli translate compile   # was: flask translate compile
python -m app.cli shell               # was: flask shell
```
