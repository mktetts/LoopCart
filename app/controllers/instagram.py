import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import logging
from typing import Any, List, Optional

import requests
from db.mongodb_manager import mongodb_manager
from config.settings import settings
from fastapi import HTTPException, Request
from services.agent_connection import create_session_id, send_message
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=2)


def send_customer_message(
    page_id: str, response: str, page_token: str, recipient_id: str
) -> dict:
    """Send a DM to an Instagram user."""
    url = f"https://graph.instagram.com/v22.0/{page_id}/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": response},
        "messaging_type": "RESPONSE",
        "access_token": page_token,
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        logger.info(f"DM sent to {recipient_id}: {response.json()}")
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to send DM: {str(e)}")
        return {"error": str(e)}


async def check_connection(mode, token, challenge):
    print(f"Verification request: mode={mode}, token={token}")
    if mode == "subscribe" and token == settings.INSTAGRAM_VERIFY_TOKEN:
        print("Webhook verified successfully")
        return challenge
    return PlainTextResponse("Verification token mismatch", status_code=403)
async def run_in_executor(func, *args):
    """Run a synchronous function in a thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, lambda: func(*args))

async def receive_webhook(request: Request):
    data = await request.json()
    # print(f"Received data: {json.dumps(data, indent=4)}")
    if "entry" in data:
        for entry in data.get("entry", []):
            if "changes" in entry:
                for change in entry.get("changes", []):
                    if change.get("field") == "comments":
                        comment_data = change.get("value", {})
                        comment_text = comment_data.get("text", "")
                        commenter_id = comment_data.get("from", {}).get("id", "")
                        media_id = comment_data.get("media", {}).get("id", "")
                        if comment_text == "buy" or comment_text == "Buy" or comment_text == "BUY":
                            comment_text = "Hi, I want to purchase(buy) this product, post id is " + media_id + " Can u please look up this product"
                        if commenter_id and comment_text:
                            logger.info(
                                f"Comment received from {commenter_id}: {comment_text}"
                            )
                            # dm_response = "Thanks for commenting on my post!"
                            # send_customer_message(
                            #     settings.INSTAGRAM_USER_ID,
                            #     dm_response,
                            #     settings.INSTAGRAM_ACCESS_TOKEN,
                            #     commenter_id,
                            # )
                            user = await mongodb_manager.find_by_id("insta_users", **{"user_id": commenter_id})
                            if user is not None:
                                session_id = user.get("session_id", "")
                            if user is None:
                                session_id = create_session_id()
                                if session_id:
                                    await mongodb_manager.create("insta_users", **{"user_id" : commenter_id, "session_id" : session_id})
                            reply = await run_in_executor(send_message, session_id, comment_text)
                            await run_in_executor(
                                    send_customer_message,
                                    settings.INSTAGRAM_USER_ID,
                                    reply,
                                    settings.INSTAGRAM_ACCESS_TOKEN,
                                    commenter_id,
                                )

            for messaging in entry.get("messaging", []):
                if messaging.get("sender", {}).get("id") == settings.INSTAGRAM_USER_ID:
                    continue
                sender_id = messaging.get("sender", {}).get("id")
                
                # Check for Story reply
                reply_to = messaging.get("message", {}).get("reply_to", {})
                story = reply_to.get("story", {})
                if story.get("id"):
                    story_id = story.get("id")
                    reply_text = messaging.get("message", {}).get("text", "")
                    logger.info(f"Story reply received from {sender_id}: {reply_text} for Story {story_id}")
                                       
                    dm_response = "Thanks for replying to my Story!"
                    user = await mongodb_manager.find_by_id("insta_users", **{"user_id": sender_id})
                    if user is not None:
                        session_id = user.get("session_id", "")
                    if user is None:
                        session_id = create_session_id()
                        if session_id:
                            await mongodb_manager.create("insta_users", **{"user_id" : sender_id, "session_id" : session_id})
                    reply = await run_in_executor(send_message, session_id, reply_text)
                    await run_in_executor(
                            send_customer_message,
                            settings.INSTAGRAM_USER_ID,
                            reply,
                            settings.INSTAGRAM_ACCESS_TOKEN,
                            sender_id,
                        )
                    # send_customer_message(
                    #     settings.INSTAGRAM_USER_ID,
                    #     dm_response,
                    #     settings.INSTAGRAM_ACCESS_TOKEN,
                    #     sender_id,
                    # )
                    continue
                if messaging.get("sender").get("id") == settings.INSTAGRAM_USER_ID:
                    return None
                sender_id = messaging.get("sender").get("id")
                user = await mongodb_manager.find_by_id("insta_users", **{"user_id": sender_id})
                if user is not None:
                    session_id = user.get("session_id", "")
                if user is None:
                    session_id = create_session_id()
                    if session_id:
                        await mongodb_manager.create("insta_users", **{"user_id" : sender_id, "session_id" : session_id})
                message_text = messaging.get("message", {}).get("text", "")
                reply = await run_in_executor(send_message, session_id, message_text)
                await run_in_executor(
                        send_customer_message,
                        settings.INSTAGRAM_USER_ID,
                        reply,
                        settings.INSTAGRAM_ACCESS_TOKEN,
                        sender_id,
                    )
                print(message_text)
    return PlainTextResponse("", status_code=200)


class PostRequest(BaseModel):
    image_urls: List[str]
    main_caption: str


class PostResponse(BaseModel):
    post_id: str
    permalink: str
    status: str


async def upload_single_image(image_url: str) -> str:
    """Upload a single image to Instagram and return the container ID."""
    url = f"https://graph.instagram.com/v22.0/{settings.INSTAGRAM_USER_ID}/media"
    params = {"image_url": image_url, "access_token": settings.INSTAGRAM_ACCESS_TOKEN}
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        container_id = response.json().get("id")
        if not container_id:
            raise ValueError("No container ID returned")
        logger.info(f"Uploaded image container: {container_id}")
        return container_id
    except requests.RequestException as e:
        logger.error(f"Failed to upload image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


async def create_carousel(children: List[str], caption: str) -> str:
    """Create a carousel container with multiple media items."""
    url = f"https://graph.instagram.com/v22.0/{settings.INSTAGRAM_USER_ID}/media"
    params = {
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": caption,
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN,
    }
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        container_id = response.json().get("id")
        if not container_id:
            raise ValueError("No carousel container ID returned")
        logger.info(f"Created carousel container: {container_id}")
        return container_id
    except requests.RequestException as e:
        logger.error(f"Failed to create carousel: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create carousel: {str(e)}"
        )


async def publish_container(container_id: str) -> str:
    """Publish a container to Instagram and return the post ID."""
    url = (
        f"https://graph.instagram.com/v22.0/{settings.INSTAGRAM_USER_ID}/media_publish"
    )
    params = {
        "creation_id": container_id,
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN,
    }
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        post_id = response.json().get("id")
        if not post_id:
            raise ValueError("No post ID returned")
        logger.info(f"Published post: {post_id}")
        return post_id
    except requests.RequestException as e:
        logger.error(f"Failed to publish post: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to publish post: {str(e)}")


async def post_images(request: PostRequest):
    """Post multiple images to Instagram as a carousel using image URLs."""
    if len(request.image_urls) < 2:
        raise HTTPException(
            status_code=400, detail="At least two images are required for a carousel"
        )
    if len(request.image_urls) > 10:
        raise HTTPException(
            status_code=400, detail="Maximum 10 images allowed for a carousel"
        )

    try:
        # Step 1: Upload each image and get container IDs
        container_ids = []
        for image_url in request.image_urls:
            container_id = await upload_single_image(image_url)
            container_ids.append(container_id)

        # Step 2: Create carousel container
        carousel_container_id = await create_carousel(
            container_ids, request.main_caption
        )

        # Step 3: Publish the carousel
        post_id = await publish_container(carousel_container_id)
        permalink = await get_post_permalink(post_id=post_id)
        return PostResponse(post_id=post_id, permalink=permalink, status="success")
    except Exception as e:
        logger.error(f"Error posting images: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error posting images: {str(e)}")


class PostLinkResponse(BaseModel):
    post_id: str
    permalink: str


async def get_post_permalink(post_id: str) -> str:
    """Fetch the permalink for a given post_id."""
    url = f"https://graph.instagram.com/v22.0/{post_id}?fields=permalink&access_token={settings.INSTAGRAM_ACCESS_TOKEN}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        permalink = response.json().get("permalink")
        if not permalink:
            raise ValueError("No permalink returned")
        logger.info(f"Fetched permalink for post {post_id}: {permalink}")
        return permalink
    except requests.RequestException as e:
        logger.error(f"Failed to fetch permalink: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch permalink: {str(e)}"
        )


async def get_post_link(post_id: str):
    try:
        permalink = await get_post_permalink(post_id)
        return PostLinkResponse(post_id=post_id, permalink=permalink)
    except Exception as e:
        logger.error(f"Error retrieving post link: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving post link: {str(e)}"
        )


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


async def create_story_container(
    post_id: str, external_url: str, image_url: Optional[str]
) -> str:
    """Create a Story container, either sharing a post or using an image."""
    url = f"https://graph.instagram.com/v22.0/{settings.INSTAGRAM_USER_ID}/media"
    params = {
        "media_type": "STORIES",
        "caption": f"Check out this post! {external_url}",
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN,
    }
    if image_url:
        params["image_url"] = image_url

    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        container_id = response.json().get("id")
        if not container_id:
            raise ValueError("No container ID returned")
        logger.info(f"Created Story container: {container_id}")
        return container_id
    except requests.RequestException as e:
        logger.error(f"Failed to create Story container: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create Story: {str(e)}")


async def publish_container(container_id: str) -> str:
    """Publish a container to Instagram."""
    url = (
        f"https://graph.instagram.com/v22.0/{settings.INSTAGRAM_USER_ID}/media_publish"
    )
    params = {
        "creation_id": container_id,
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN,
    }
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        post_id = response.json().get("id")
        if not post_id:
            raise ValueError("No post ID returned")
        logger.info(f"Published Story: {post_id}")
        return post_id
    except requests.RequestException as e:
        logger.error(f"Failed to publish Story: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to publish Story: {str(e)}"
        )


async def post_story(request: StoryRequest):
    """Post a Story referencing a carousel post or using an image with an external link."""
    try:
        container_id = await create_story_container(
            "", "", request.image_url
        )

        # Publish Story
        story_post_id = await publish_container(container_id)

        # Fetch permalink
        permalink = await get_post_permalink(story_post_id)
        result = await mongodb_manager.create(
            "auction",
            channel=request.channel_id,
            record=request.record_id,
            currency = request.currency,
            start_time = request.start_time,
            end_time = request.end_time,
            image = request.image_url,
            timezone = request.timezone,
            post_id = story_post_id,
            product_name = request.product_name,
            base_price = request.price
        )

        return StoryResponse(post_id="permalink", status="success")
    except Exception as e:
        print(e)
        logger.error(f"Error posting Story: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error posting Story: {str(e)}")
