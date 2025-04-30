from typing import Any, List, Optional

from controllers import instagram
from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

instagram_router = APIRouter()


@instagram_router.get(path="/api/webhook", response_class=PlainTextResponse)
async def connection_check(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
) -> PlainTextResponse:
    return await instagram.check_connection(hub_mode, hub_token, hub_challenge)


@instagram_router.post(path="/api/webhook")
async def receive_message(request: Request):
    return await instagram.receive_webhook(request)


class PostRequest(BaseModel):
    image_urls: List[str]
    main_caption: str


class PostResponse(BaseModel):
    post_id: str
    status: str
    permalink: str

@instagram_router.post(path="/api/post-to-instagram", response_model=PostResponse)
async def receive_message(request: PostRequest):
    return await instagram.post_images(request)


class PostLinkResponse(BaseModel):
    post_id: str
    permalink: str


@instagram_router.get(path="/api/get-post-link/{post_id}", response_model=PostLinkResponse)
async def get_post_link(post_id: str):
    return await instagram.get_post_link(post_id=post_id)

class StoryRequest(BaseModel):
    record_id: str
    channel_id : str
    start_time: str
    end_time: str
    currency: str
    timezone: str
    price: Any
    product_name: str
    image_url: str = None

class StoryResponse(BaseModel):
    post_id: str
    status: str
    
@instagram_router.post(path="/api/post-story/", response_model=StoryResponse)
async def post_story(request: StoryRequest):
    return await instagram.post_story(request=request)

