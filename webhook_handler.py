"""Shopify webhook handler for sales notifications."""

import asyncio
import base64
import hashlib
import hmac
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request

from keymaster import get_key

router = APIRouter(tags=["webhooks"])

NOTION_PARENT_PAGE_ID = "329f46dbdd8d815aa79be904bde55141"
NOTION_VERSION = "2022-06-28"
TELEGRAM_CHAT_ID_ENV = "TELEGRAM_CHAT_ID"


def verify_shopify_signature(body: bytes, signature: str, secret: str) -> bool:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    encoded = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(encoded, signature)


def parse_order(payload: dict[str, Any]) -> dict[str, str]:
    line_items = payload.get("line_items") or []
    titles = [item.get("title", "作品名不明") for item in line_items]
    total_price = payload.get("total_price") or "0"
    currency = payload.get("currency") or "JPY"
    order_name = payload.get("name") or f"#{payload.get('order_number', 'unknown')}"
    created_at = payload.get("created_at") or datetime.now(timezone.utc).isoformat()
    customer = payload.get("customer") or {}
    customer_name = " ".join(
        part for part in [customer.get("last_name"), customer.get("first_name")] if part
    ).strip()
    if not customer_name:
        customer_name = customer.get("email") or "購入者情報なし"

    return {
        "order_id": str(payload.get("id", "")),
        "order_name": order_name,
        "titles": " / ".join(titles) if titles else "作品名不明",
        "total_price": str(total_price),
        "currency": currency,
        "created_at": created_at,
        "customer_name": customer_name,
    }


def build_telegram_message(order: dict[str, str]) -> str:
    return (
        "ビーズワークス売れました!\n"
        f"作品名: {order['titles']}\n"
        f"価格: {order['total_price']} {order['currency']}\n"
        f"注文: {order['order_name']}\n"
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
            json={
                "chat_id": chat_id,
                "text": build_telegram_message(order),
            },
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Telegram error: {resp.text}")


def notion_rich_text(content: str) -> dict[str, Any]:
    return {"type": "text", "text": {"content": content}}


async def create_notion_sales_log(order: dict[str, str]) -> None:
    notion_token = await get_key("notion", "api_key")
    created_label = order["created_at"]
    try:
        created_label = datetime.fromisoformat(
            order["created_at"].replace("Z", "+00:00")
        ).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        pass

    payload = {
        "parent": {"page_id": NOTION_PARENT_PAGE_ID},
        "properties": {
            "title": {
                "title": [
                    notion_rich_text(
                        f"売上ログ {order['order_name']} {order['titles']}"
                    )
                ]
            }
        },
        "children": [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [notion_rich_text("ビーズワークス売上通知")]
                },
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [notion_rich_text(f"作品名: {order['titles']}")]
                },
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        notion_rich_text(
                            f"価格: {order['total_price']} {order['currency']}"
                        )
                    ]
                },
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [notion_rich_text(f"注文: {order['order_name']}")]
                },
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [notion_rich_text(f"購入者: {order['customer_name']}")]
                },
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [notion_rich_text(f"受信日時: {created_label}")]
                },
            },
        ],
    }

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            "https://api.notion.com/v1/pages",
            headers={
                "Authorization": f"Bearer {notion_token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            json=payload,
        )
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"Notion error: {resp.text}")


@router.post("/webhooks/orders/create")
async def handle_orders_create(request: Request) -> dict[str, Any]:
    body = await request.body()
    signature = request.headers.get("X-Shopify-Hmac-Sha256", "")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing Shopify signature")

    webhook_secret = await get_key("shopify", "webhook_secret")
    if not verify_shopify_signature(body, signature, webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid Shopify signature")

    payload = await request.json()
    order = parse_order(payload)

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
        raise HTTPException(
            status_code=502,
            detail="; ".join(errors),
        )

    return {"ok": True, "order": order["order_name"]}
