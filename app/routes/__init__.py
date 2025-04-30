from fastapi import APIRouter

from routes.aws_s3 import s3_router
from routes.instagram import instagram_router
from routes.currency import router as currency_router
from routes.slack import router as slack_router


api_router = APIRouter()
api_router.include_router(instagram_router)
api_router.include_router(s3_router)
api_router.include_router(currency_router)
api_router.include_router(slack_router)
