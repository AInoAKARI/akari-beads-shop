"""Stripe webhook handler for payment notifications."""

import asyncio
import hashlib
import hmac
import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request

from keymaster import get_key

router = APIRouter(tags=["webhooks"])

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
NOTION_DB_ID = "a8306831-049b-4bd4-a40e-791e00906228"
TELEGRAM_CHAT_ID_ENV = "TELEGRAM_CHAT_ID"

STRIPE_SIGNATURE_TOLERANCE = 300


def verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    """Verify Stripe webhook signature (v1)."""
    try:
        elements = dict(
            pair.split("=", 1) for pair in sig_header.split(",") if "=" in pair
        )
        timestamp = elements.get("t", "")
        signature = elements.get("v1", "")
        if not timestamp or not signature:
            return False

        if abs(time.time() - int(timestamp)) > STRIPE_SIGNATURE_TOLERANCE:
            return False

        signed_payload = f"{timestamp}.".encode() + payload
        expected = hmac.new(
            secret.encode("utf-8"), signed_payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    except (ValueError, KeyError):
        return False


def parse_checkout_session(session: dict[str, Any]) -> dict[str, str]:
    """Extract order details from a Stripe checkout.session.completed event."""
    amount_total = session.get("amount_total") or 0
    currency = (session.get("currency") or "jpy").upper()
    customer_email = session.get("customer_details", {}).get("email", "")
    customer_name = session.get("customer_details", {}).get("name", "")
    payment_intent = session.get("payment_intent") or ""
    session_id = session.get("id", "")

    return {
        "session_id": session_id,
        "payment_intent": payment_intent,
        "amount": str(amount_total),
        "currency": currency,
        "customer_name": customer_name or customer_email or "購入者情報なし",
        "customer_email": customer_email,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def build_telegram_message(order: dict[str, str]) -> str:
    return (
        "ビーズワークス売れました!\n"
        f"金額: {order['amount']} {order['currency']}\n"
        f"購入者: {order['customer_name']}\n"
        f"Payment: {order['payment_intent']}\n"
        "次回イベントの制作費に還元して、さらにかわいい作品を届けます。"
    )


async def send_telegram_notification(order: dict[str, str]) -> None:
    telegram_token = await get_key("telegram", "api_key")
    try:
        chat_id = await get_key("telegram", "chat_id")
    except HTTPException:
        chat_id = os.environ.get(TELEGRAM_CHAT_ID_ENV, "")

    if not chat_id:
        raise HTTPException(status_code=500, detail="Telegram chat_id not configured")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{telegram_token}/sendMessage",
            json={"chat_id": chat_id, "text": build_telegram_message(order)},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Telegram error: {resp.text}")


async def create_notion_sales_log(order: dict[str, str]) -> None:
    """Log the sale in the Notion DB."""
    headers = {
        "Authorization": f"Bearer {await get_key('notion', 'api_key')}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    payload: dict[str, Any] = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": f"売上 {order['customer_name']} {order['amount']} {order['currency']}"
                        }
                    }
                ]
            },
            "Description": {
                "rich_text": [
                    {
                        "text": {
                            "content": (
                                f"Payment: {order['payment_intent']}\n"
                                f"Session: {order['session_id']}\n"
                                f"購入者: {order['customer_name']}\n"
                                f"Email: {order['customer_email']}\n"
                                f"日時: {order['created_at']}"
                            )
                        }
                    }
                ]
            },
            "Price": {"number": int(order["amount"])},
            "Status": {"select": {"name": "Sold"}},
        },
    }

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{NOTION_API_BASE}/pages",
            headers=headers,
            json=payload,
        )
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"Notion error: {resp.text}")


@router.post("/webhooks/stripe")
async def handle_stripe_webhook(request: Request) -> dict[str, Any]:
    """Handle Stripe webhook events (checkout.session.completed)."""
    body = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")
    if not sig_header:
        raise HTTPException(status_code=401, detail="Missing Stripe-Signature header")

    webhook_secret = await get_key("stripe", "webhook_secret")
    if not verify_stripe_signature(body, sig_header, webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid Stripe signature")

    event = await request.json()
    event_type = event.get("type", "")

    if event_type != "checkout.session.completed":
        return {"ok": True, "skipped": event_type}

    session = event.get("data", {}).get("object", {})
    order = parse_checkout_session(session)

    results = await asyncio.gather(
        send_telegram_notification(order),
        create_notion_sales_log(order),
        return_exceptions=True,
    )

    errors: list[str] = []
    for target, result in zip(("telegram", "notion"), results):
        if isinstance(result, Exception):
            if isinstance(result, HTTPException):
                errors.append(f"{target}: {result.detail}")
            else:
                errors.append(f"{target}: {str(result)}")

    if errors:
        raise HTTPException(status_code=502, detail="; ".join(errors))

    return {"ok": True, "session_id": order["session_id"]}
