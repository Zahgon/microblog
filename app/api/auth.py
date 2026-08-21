import sqlalchemy as sa
from fastapi import Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPBearer, \
    HTTPAuthorizationCredentials
from starlette.exceptions import HTTPException

from app import db
from app.models import User

basic_auth_scheme = HTTPBasic(auto_error=False)
token_auth_scheme = HTTPBearer(auto_error=False)


def verify_password(username, password):
    user = db.session.scalar(sa.select(User).where(User.username == username))
    if user and user.check_password(password):
        return user


def verify_token(token):
    return User.check_token(token) if token else None


def basic_auth_error(status=401):
    raise HTTPException(status_code=status, headers={
        'WWW-Authenticate': 'Basic realm="Authentication Required"'})


def token_auth_error(status=401):
    raise HTTPException(status_code=status, headers={
        'WWW-Authenticate': 'Bearer realm="Authentication Required"'})


async def basic_auth(
        credentials: HTTPBasicCredentials = Depends(basic_auth_scheme)):
    """Dependency that authenticates a user with its username and password."""
    user = None
    if credentials is not None:
        user = verify_password(credentials.username, credentials.password)
    if user is None:
        basic_auth_error(401)
    return user


async def token_auth(
        credentials: HTTPAuthorizationCredentials = Depends(
            token_auth_scheme)):
    """Dependency that authenticates a user with its API token."""
    user = None
    if credentials is not None:
        user = verify_token(credentials.credentials)
    if user is None:
        token_auth_error(401)
    return user
