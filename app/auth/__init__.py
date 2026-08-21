from fastapi import APIRouter

bp = APIRouter()

from app.auth import routes
