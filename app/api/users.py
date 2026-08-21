import sqlalchemy as sa
from fastapi import Depends, Request
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from app import db
from app.api import bp
from app.api.auth import token_auth
from app.api.errors import bad_request
from app.models import User
from app.params import Page, PerPage
from app.urls import url_for


@bp.get('/users/{id}', name='api.get_user',
        dependencies=[Depends(token_auth)])
async def get_user(id: int):
    return db.get_or_404(User, id).to_dict()


@bp.get('/users', name='api.get_users', dependencies=[Depends(token_auth)])
async def get_users(page: Page = 1, per_page: PerPage = 10):
    per_page = min(per_page, 100)
    return User.to_collection_dict(sa.select(User), page, per_page,
                                   'api.get_users')


@bp.get('/users/{id}/followers', name='api.get_followers',
        dependencies=[Depends(token_auth)])
async def get_followers(id: int, page: Page = 1, per_page: PerPage = 10):
    user = db.get_or_404(User, id)
    per_page = min(per_page, 100)
    return User.to_collection_dict(user.followers.select(), page, per_page,
                                   'api.get_followers', id=id)


@bp.get('/users/{id}/following', name='api.get_following',
        dependencies=[Depends(token_auth)])
async def get_following(id: int, page: Page = 1, per_page: PerPage = 10):
    user = db.get_or_404(User, id)
    per_page = min(per_page, 100)
    return User.to_collection_dict(user.following.select(), page, per_page,
                                   'api.get_following', id=id)


@bp.post('/users', name='api.create_user')
async def create_user(request: Request):
    data = await request.json()
    if 'username' not in data or 'email' not in data or 'password' not in data:
        return bad_request('must include username, email and password fields')
    if db.session.scalar(sa.select(User).where(
            User.username == data['username'])):
        return bad_request('please use a different username')
    if db.session.scalar(sa.select(User).where(
            User.email == data['email'])):
        return bad_request('please use a different email address')
    user = User()
    user.from_dict(data, new_user=True)
    db.session.add(user)
    db.session.commit()
    return JSONResponse(user.to_dict(), status_code=201, headers={
        'Location': url_for('api.get_user', id=user.id)})


@bp.put('/users/{id}', name='api.update_user')
async def update_user(id: int, request: Request,
                      token_user: User = Depends(token_auth)):
    if token_user.id != id:
        raise HTTPException(status_code=403)
    user = db.get_or_404(User, id)
    data = await request.json()
    if 'username' in data and data['username'] != user.username and \
        db.session.scalar(sa.select(User).where(
            User.username == data['username'])):
        return bad_request('please use a different username')
    if 'email' in data and data['email'] != user.email and \
        db.session.scalar(sa.select(User).where(
            User.email == data['email'])):
        return bad_request('please use a different email address')
    user.from_dict(data, new_user=False)
    db.session.commit()
    return user.to_dict()
