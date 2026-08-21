# Task: Migrate this project from Flask to FastAPI

Migrate the Flask application in `microblog/` to FastAPI, preserving its behavior exactly.

## Requirements
- Read the Flask source and port it to idiomatic FastAPI.
- Keep any resource files the code relies on — templates, translations, static assets and
  database migrations — and use them unchanged.
- Preserve the same public interface and behavior as the original: the same URLs, the same
  responses, and the same database schema.
- Drop the Flask dependencies. The application must run on an ASGI server.
- Keep the existing tests. Do not delete, rename, skip or weaken any of them.
- Update the entry point, the container image and the deployment scripts to match.

## Interface the tests use

The project's tests are updated for you and must run unchanged against your port. Three of the
names they use do not exist in the source project, so provide them:

- `Config.DATABASE_URI` — the database URL setting, in place of `SQLALCHEMY_DATABASE_URI`.
- `db.new_session_scope()` — start a fresh database session scope; returns a token.
- `db.reset_session_scope(token)` — end the scope that token started.

Everything else the tests touch — `create_app`, `db.session`, `db.create_all`, `db.drop_all`,
`db.session.remove` — already exists in the source project and must keep working.

## Done when

All three of these pass:

- **Test cases** — `python -m unittest tests.py` passes.
- **Behaviour tests** — the migrated application's responses match the original Flask
  application's, request for request.
- **Coverage tests** — the code you write is reached by those checks. Code that nothing
  exercises does not count as migrated.
