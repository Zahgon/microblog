from fastapi import Depends

from app import db
from app.api import bp
from app.api.auth import basic_auth, token_auth
from app.models import User


@bp.post('/tokens', name='api.get_token')
async def get_token(user: User = Depends(basic_auth)):
    token = user.get_token()
    db.session.commit()
    return {'token': token}


@bp.delete('/tokens', name='api.revoke_token', status_code=204)
async def revoke_token(user: User = Depends(token_auth)):
    user.revoke_token()
    db.session.commit()
    return None
