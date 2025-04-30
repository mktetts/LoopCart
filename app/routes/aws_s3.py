from controllers import aws_s3
from fastapi import APIRouter

s3_router = APIRouter()


s3_router.post(path="/api/upload-to-s3/")(aws_s3.upload_multiple_images)
