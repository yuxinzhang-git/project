from fastapi import APIRouter

from app.api import chat, daily, learning, money, smart, web, xianyu_tasks

api_router = APIRouter()
api_router.include_router(chat.router)
api_router.include_router(daily.router)
api_router.include_router(learning.router)
api_router.include_router(money.router)
api_router.include_router(web.router)
api_router.include_router(smart.router)
api_router.include_router(xianyu_tasks.router)
