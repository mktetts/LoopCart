import logging
import os
from typing import List
import uuid

import boto3
from config.settings import settings
from fastapi import File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_ACCESS_SECRET_ID,
    region_name=settings.AWS_REGION,
)


async def upload_multiple_images(files: List[UploadFile] = File(...)):
    image_urls = []
    try:
        if len(files) < 2 or len(files) > 9:
            raise HTTPException(status_code=400, detail="Please upload between 2 and 9 images.")
        for file in files:
            if not file.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=400, detail=f"File {file.filename} is not an image."
                )
        for file in files:
            file_extension = file.filename.split(".")[-1]
            unique_filename = f"{uuid.uuid4()}.{file_extension}"

            # Upload to S3
            s3_client.upload_fileobj(
                file.file,
                settings.BUCKET_NAME,
                unique_filename,
                ExtraArgs={"ContentType": file.content_type}
            )
            # image_url = s3_client.generate_presigned_url(
            #     "get_object",
            #     Params={"Bucket": settings.BUCKET_NAME, "Key": file_key},
            #     ExpiresIn=3600,  # URL expires in 1 hour
            # )
            image_url = f"https://{settings.BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{unique_filename}"
            image_urls.append(image_url)
        print(image_urls)

        return JSONResponse(content={"urls": image_urls}, status_code=200)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    finally:
        for file in files:
            await file.close()
