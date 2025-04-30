import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from fastapi import APIRouter, HTTPException, Request, logger
from pydantic import BaseModel
from slack_bolt.adapter.fastapi import SlackRequestHandler
from slack_sdk import WebClient
from slack_sdk.web.async_client import AsyncWebClient
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from slack_sdk.errors import SlackApiError
from slack_bolt import App
from config.settings import settings
from db.mongodb_manager import mongodb_manager
import threading
import time
from datetime import datetime, timedelta, timezone
import uuid

router = APIRouter()

slack_app = AsyncApp(
    token=settings.AUCTION_BOT_OAUTH_TOKEN,
    signing_secret=settings.AUCTION_BOT_SIGNING_SECRET,
)
client = AsyncWebClient(token=settings.AUCTION_BOT_OAUTH_TOKEN)
logging.getLogger("slack_sdk").setLevel(logging.WARNING)
logging.getLogger("slack_bolt").setLevel(logging.WARNING)
logging.getLogger("slack_bolt.App").setLevel(logging.WARNING)

handler = AsyncSlackRequestHandler(slack_app)

auctions = {}


def create_auction_message(channel_id, auction):
    remaining_time = max(0, (auction["end_time"] - datetime.now(timezone.utc)).total_seconds() // 60)
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Auction Timer: {int(remaining_time)} minutes remaining"
            }
        },
        {
            "type": "image",
            "image_url": auction["image_url"],
            "alt_text": auction["item"]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Auction: {auction['item']}*\nCurrent Bid: {auction['currency']} {auction['highest_bid']:.2f}" + 
                        (f" by <@{auction['highest_bidder']}>" if auction["highest_bidder"] else "")
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Place Bid"},
                    "action_id": "place_bid",
                    "value": auction["auction_id"]
                }
            ]
        }
    ]
    return blocks

async def start_auction(channel_id, start_time, end_time, item, image_url, starting_bid, currency):
    # Parse start_time and end_time if strings
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    if isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

    # Ensure start_time and end_time are UTC-aware
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    # Wait until start_time
    now = datetime.now(timezone.utc)
    if now < start_time:
        delay = (start_time - now).total_seconds()
        time.sleep(delay)

    # Check if auction was already started
    if channel_id in auctions:
        return

    auction_id = str(uuid.uuid4())
    auctions[channel_id] = {
        "item": item,
        "image_url": image_url,
        "highest_bid": starting_bid,
        "highest_bidder": None,
        "start_time": start_time,
        "end_time": end_time,
        "auction_id": auction_id,
        "currency": currency
    }

    try:
        response = await client.chat_postMessage(
            channel=channel_id,
            blocks=create_auction_message(channel_id, auctions[channel_id]),
            text=f"Auction started for {item}"
        )
        auctions[channel_id]["ts"] = response["ts"]
        threading.Thread(target=lambda: asyncio.run(update_timer(channel_id))).start()
        threading.Thread(target=lambda: asyncio.run(close_auction(channel_id))).start()
    except SlackApiError:
        pass

async def handle_member_joined(ack, body):
    await ack()
    channel_id = body["event"]["channel"]
    user_id = body["event"]["user"]
    auth_test = await slack_app.client.auth_test()
    if user_id == auth_test["user_id"]:
        return

    auc = await mongodb_manager.find_by_id("auction", channel=channel_id)
    if auc is None:
        return

    item = auc["product_name"]
    image_url = auc["image"]
    starting_bid = float(auc["base_price"].replace(',', ''))
    start_time = auc["start_time"]
    end_time = auc["end_time"]
    currency = auc["currency"]

    # Start auction in a separate thread
    threading.Thread(target=lambda: asyncio.run(start_auction(channel_id, start_time, end_time, item, image_url, starting_bid, currency))).start()

async def handle_bid_button(ack, body, respond):
    await ack()
    auction_id = body["actions"][0]["value"]
    user_id = body["user"]["id"]

    channel_id = None
    for cid, auction in auctions.items():
        if auction["auction_id"] == auction_id:
            channel_id = cid
            break

    if not channel_id:
        await respond("This auction does not exist.")
        return

    auction = auctions[channel_id]
    now = datetime.now(timezone.utc)
    if now < auction["start_time"]:
        await respond("The auction has not started yet.")
        return
    if now >= auction["end_time"]:
        await respond("This auction is no longer active.")
        return

    modal = {
        "type": "modal",
        "callback_id": "bid_submission",
        "private_metadata": f"{channel_id}:{auction_id}",
        "title": {"type": "plain_text", "text": "Place Your Bid"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "bid_amount",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "bid_value",
                    "placeholder": {"type": "plain_text", "text": "Enter your bid amount"}
                },
                "label": {"type": "plain_text", "text": "Bid Amount ($)"}
            }
        ]
    }

    try:
        await client.views_open(
            trigger_id=body["trigger_id"],
            view=modal
        )
    except SlackApiError:
        await respond("Error opening bid modal.")

async def handle_bid_submission(ack, body):
    try:
        channel_id, auction_id = body["view"]["private_metadata"].split(":")
        user_id = body["user"]["id"]
        auction = auctions.get(channel_id)

        if not auction or auction["auction_id"] != auction_id:
            await ack({"response_action": "errors", "errors": {"bid_amount": "This auction does not exist."}})
            return

        now = datetime.now(timezone.utc)
        if now < auction["start_time"]:
            await ack({"response_action": "errors", "errors": {"bid_amount": "The auction has not started yet."}})
            return
        if now >= auction["end_time"]:
            await ack({"response_action": "errors", "errors": {"bid_amount": "This auction is no longer active."}})
            return

        try:
            bid_amount = float(body["view"]["state"]["values"]["bid_amount"]["bid_value"]["value"])
        except ValueError:
            await ack({"response_action": "errors", "errors": {"bid_amount": "Please enter a valid number for the bid amount."}})
            return

        if bid_amount <= auction["highest_bid"]:
            await ack({"response_action": "errors", "errors": {"bid_amount": f"Your bid of ${bid_amount:.2f} is not higher than the current highest bid of ${auction['highest_bid']:.2f}."}})
            return

        auction["highest_bid"] = bid_amount
        auction["highest_bidder"] = user_id

        try:
            await client.chat_update(
                channel=channel_id,
                ts=auction["ts"],
                blocks=create_auction_message(channel_id, auction),
                text=f"Updated bid for {auction['item']}"
            )
            await client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=f"Bid of ${bid_amount:.2f} placed successfully!"
            )
            await ack()
        except SlackApiError:
            await ack({"response_action": "errors", "errors": {"bid_amount": "Error updating auction."}})
    except Exception:
        await ack({"response_action": "errors", "errors": {"bid_amount": "An unexpected error occurred."}})

async def update_timer(channel_id):
    auction = auctions.get(channel_id)
    if not auction:
        return

    while datetime.now(timezone.utc) < auction["end_time"]:
        time.sleep(60)
        if channel_id not in auctions or datetime.now(timezone.utc) >= auction["end_time"]:
            break
        try:
            await client.chat_update(
                channel=channel_id,
                ts=auction["ts"],
                blocks=create_auction_message(channel_id, auction),
                text=f"Updated timer for {auction['item']}"
            )
        except SlackApiError:
            pass

async def close_auction(channel_id):
    auction = auctions.get(channel_id)
    if not auction:
        return

    # Wait until end_time
    now = datetime.now(timezone.utc)
    if now < auction["end_time"]:
        delay = (auction["end_time"] - now).total_seconds()
        time.sleep(delay)

    winner_text = f"<@{auction['highest_bidder']}>" if auction["highest_bidder"] else "No bidders"
    final_message = f"Auction for *{auction['item']}* has ended!\nWinner: {winner_text}\nFinal Bid: ${auction['highest_bid']:.2f}"
    try:
        await client.chat_postMessage(
            channel=channel_id,
            text=final_message
        )
        blocks = [
            {
                "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Auction Closed"
            }
        },
        {
            "type": "image",
            "image_url": auction["image_url"],
            "alt_text": auction["item"]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Auction Closed: {auction['item']}*\nWinner: {winner_text}\nFinal Bid: ${auction['highest_bid']:.2f}\n\n Winner will receive Payment Mail soon."
            }
        }
    ]
        await client.chat_update(
            channel=channel_id,
            ts=auction["ts"],
            blocks=blocks,
            text=f"Auction closed for {auction['item']}"
        )
    except SlackApiError:
        pass

    del auctions[channel_id]

# Register async event handlers
slack_app.event("member_joined_channel")(handle_member_joined)
slack_app.action("place_bid")(handle_bid_button)
slack_app.view("bid_submission")(handle_bid_submission)


@router.post("/slack/events")
async def slack_events(request: Request):
    return await handler.handle(request)


class InviteRequest(BaseModel):
    channel_id: str
    email: str


admin_client = AsyncWebClient(token=settings.SLACK_ADMIN_TOKEN)


@router.post("/slack/invite")
async def generate_invite_link(request: InviteRequest):
    try:
        channel_url = f"{settings.SLACK_WORKSPACE}/archives/{request.channel_id}"

        # Check if bot is in the channel
        try:
            members_response = await client.conversations_members(channel=request.channel_id)
            bot_user_id = (await client.auth_test())["user_id"]
            if bot_user_id not in members_response["members"]:
                # Try to join the channel (works for public channels)
                try:
                    await client.conversations_join(channel=request.channel_id)
                except SlackApiError as join_error:
                    if join_error.response["error"] == "method_not_supported_for_channel":
                        raise HTTPException(
                            status_code=400,
                            detail="Bot cannot join private channel. Invite the bot to the channel first."
                        )
                    raise
        except SlackApiError as e:
            raise HTTPException(status_code=400, detail=f"Error checking channel membership: {e.response['error']}")

        # Try to find user by email
        try:
            response = await client.users_lookupByEmail(email=request.email)
            if response["ok"]:
                user_id = response["user"]["id"]
            else:
                raise SlackApiError("lookup_failed", response["error"])
        except SlackApiError as e:
            if e.response["error"] == "users_not_found":
                # User not in workspace, attempt to invite to workspace
                try:
                    invite_response = await admin_client.admin_users_invite(
                        email=request.email,
                        channel_ids=request.channel_id,
                        team_id=settings.SLACK_TEAM_ID
                    )
                    if not invite_response["ok"]:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Failed to invite user to workspace: {invite_response['error']}"
                        )
                    return {
                        "channel_url": channel_url,
                        "message": f"Invitation sent to {request.email}. They must accept the workspace invite before joining the channel."
                    }
                except SlackApiError as invite_error:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Error inviting user to workspace: {invite_error.response['error']}"
                    )
            else:
                raise HTTPException(status_code=400, detail=f"Error looking up user: {e.response['error']}")

        # User exists, invite to channel
        try:
            response = await client.conversations_invite(
                channel=request.channel_id,
                users=user_id,
                force=True
            )
            if response["ok"]:
                return {"channel_url": channel_url, "message": f"User {request.email} invited to channel."}
            else:
                raise SlackApiError("invite_failed", response["error"])
        except SlackApiError as e:
            if e.response["error"] == "already_in_channel":
                return {
                    "channel_url": channel_url,
                    "message": f"User {request.email} is already a member of the channel."
                }
            raise HTTPException(status_code=400, detail=f"Error inviting user to channel: {e.response['error']}")

    except SlackApiError as e:
        raise HTTPException(status_code=500, detail=f"Error processing invite: {e.response['error']}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")