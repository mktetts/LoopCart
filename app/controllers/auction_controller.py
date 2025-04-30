import threading
import time
from datetime import datetime, timedelta
import uuid
from slack_sdk.errors import SlackApiError
from routes.slack import client, slack_app

from config.settings import settings


auctions = {}

def create_auction_message(channel_id, auction):
    remaining_time = (auction["end_time"] - datetime.now()).seconds // 60
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Auction Timer: {remaining_time} minutes remaining"
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
                "text": f"*Auction: {auction['item']}*\nCurrent Bid: ${auction['highest_bid']:.2f}" + 
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

@slack_app.event("member_joined_channel")
def handle_member_joined(ack, body, logger):
    ack()
    channel_id = body["event"]["channel"]
    user_id = body["event"]["user"]
    print("channel id" ,channel_id)
    if user_id == slack_app.client.auth_test()["user_id"]:
        return

    if channel_id in auctions:
        return

    item = "Vintage Painting"
    image_url = "https://example.com/painting.jpg"
    starting_bid = 100.0
    duration_minutes = 10
    auction_id = str(uuid.uuid4())

    auctions[channel_id] = {
        "item": item,
        "image_url": image_url,
        "highest_bid": starting_bid,
        "highest_bidder": None,
        "end_time": datetime.now() + timedelta(minutes=duration_minutes),
        "auction_id": auction_id
    }

    try:
        response = client.chat_postMessage(
            channel=channel_id,
            blocks=create_auction_message(channel_id, auctions[channel_id]),
            text=f"Auction started for {item}"
        )
        auctions[channel_id]["ts"] = response["ts"]
        threading.Thread(target=update_timer, args=(channel_id, duration_minutes)).start()
        threading.Thread(target=close_auction, args=(channel_id, duration_minutes)).start()
    except SlackApiError as e:
        logger.error(f"Error posting auction: {e}")

@slack_app.action("place_bid")
def handle_bid_button(ack, body, respond):
    ack()
    auction_id = body["actions"][0]["value"]
    user_id = body["user"]["id"]

    channel_id = None
    for cid, auction in auctions.items():
        if auction["auction_id"] == auction_id:
            channel_id = cid
            break

    if not channel_id or auctions[channel_id]["end_time"] < datetime.now():
        respond("This auction is no longer active.")
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
        client.views_open(
            trigger_id=body["trigger_id"],
            view=modal
        )
    except SlackApiError as e:
        respond(f"Error opening bid modal: {e}")

@slack_app.view("bid_submission")
def handle_bid_submission(ack, body, respond):
    ack()
    channel_id, auction_id = body["view"]["private_metadata"].split(":")
    user_id = body["user"]["id"]

    try:
        bid_amount = float(body["view"]["state"]["values"]["bid_amount"]["bid_value"]["value"])
    except ValueError:
        respond("Please enter a valid number for the bid amount.")
        return

    auction = auctions.get(channel_id)
    if not auction or auction["auction_id"] != auction_id or auction["end_time"] < datetime.now():
        respond("This auction is no longer active.")
        return

    if bid_amount <= auction["highest_bid"]:
        respond(f"Your bid of ${bid_amount:.2f} is not higher than the current highest bid of ${auction['highest_bid']:.2f}.")
        return

    auction["highest_bid"] = bid_amount
    auction["highest_bidder"] = user_id

    try:
        client.chat_update(
            channel=channel_id,
            ts=auction["ts"],
            blocks=create_auction_message(channel_id, auction),
            text=f"Updated bid for {auction['item']}"
        )
        respond(f"Bid of ${bid_amount:.2f} placed successfully!")
    except SlackApiError as e:
        respond(f"Error updating auction: {e}")

def update_timer(channel_id, duration_minutes):
    auction = auctions.get(channel_id)
    if not auction:
        return

    while datetime.now() < auction["end_time"]:
        time.sleep(60)
        if channel_id not in auctions:
            break
        try:
            client.chat_update(
                channel=channel_id,
                ts=auction["ts"],
                blocks=create_auction_message(channel_id, auction),
                text=f"Updated timer for {auction['item']}"
            )
        except SlackApiError as e:
            print(f"Error updating timer: {e}")

def close_auction(channel_id, duration_minutes):
    time.sleep(duration_minutes * 60)
    auction = auctions.get(channel_id)
    if not auction:
        return

    winner_text = f"<@{auction['highest_bidder']}>" if auction["highest_bidder"] else "No bidders"
    final_message = f"Auction for *{auction['item']}* has ended!\nWinner: {winner_text}\nFinal Bid: ${auction['highest_bid']:.2f}"
    try:
        client.chat_postMessage(
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
                    "text": f"*Auction Closed: {auction['item']}*\nWinner: {winner_text}\nFinal Bid: ${auction['highest_bid']:.2f}"
                }
            }
        ]
        client.chat_update(
            channel=channel_id,
            ts=auction["ts"],
            blocks=blocks,
            text=f"Auction closed for {auction['item']}"
        )
    except SlackApiError as e:
        print(f"Error closing auction: {e}")

    del auctions[channel_id]