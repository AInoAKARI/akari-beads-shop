"""Akari Beads Shop - Stripe + Notion DB product management API."""

from typing import Any

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from keymaster import get_key
from webhook_handler import router as webhook_router

app = FastAPI(title="Akari Beads Shop")

STRIPE_API_BASE = "https://api.stripe.com/v1"
NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
NOTION_DB_ID = "a8306831-049b-4bd4-a40e-791e00906228"

app.include_router(webhook_router)


async def _stripe_headers() -> dict[str, str]:
    api_key = await get_key("stripe", "api_key")
    return {"Authorization": f"Bearer {api_key}"}


async def _notion_headers() -> dict[str, str]:
    token = await get_key("notion", "api_key")
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/products")
async def list_products():
    """List products from Notion DB."""
    headers = await _notion_headers()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{NOTION_API_BASE}/databases/{NOTION_DB_ID}/query",
            headers=headers,
            json={},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


async def _create_stripe_product(title: str, description: str) -> dict[str, Any]:
    """Create a Stripe Product."""
    headers = await _stripe_headers()
    data = {"name": title, "description": description}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{STRIPE_API_BASE}/products",
            headers=headers,
            data=data,
        )
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


async def _create_stripe_price(product_id: str, price_yen: int) -> dict[str, Any]:
    """Create a Stripe Price for a product (JPY)."""
    headers = await _stripe_headers()
    data = {
        "product": product_id,
        "unit_amount": str(price_yen),
        "currency": "jpy",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{STRIPE_API_BASE}/prices",
            headers=headers,
            data=data,
        )
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


async def _create_payment_link(price_id: str) -> dict[str, Any]:
    """Create a Stripe Payment Link."""
    headers = await _stripe_headers()
    data = {
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{STRIPE_API_BASE}/payment_links",
            headers=headers,
            data=data,
        )
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


async def _register_notion_product(
    title: str,
    description: str,
    price_yen: int,
    stripe_product_id: str,
    payment_link_url: str,
) -> dict[str, Any]:
    """Register a product in the Notion DB."""
    headers = await _notion_headers()
    payload: dict[str, Any] = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            "Description": {"rich_text": [{"text": {"content": description}}]},
            "Price": {"number": price_yen},
            "Stripe Product ID": {
                "rich_text": [{"text": {"content": stripe_product_id}}]
            },
            "Payment Link": {"url": payment_link_url},
            "Status": {"select": {"name": "Active"}},
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
    return resp.json()


@app.post("/products/create")
async def create_product(
    title: str = Form(...),
    description: str = Form(""),
    price: str = Form("0"),
    image: UploadFile | None = File(None),
):
    """Create a Stripe product + price + payment link, register in Notion DB."""
    price_yen = int(price)

    # 1. Create Stripe Product
    product = await _create_stripe_product(title, description)
    product_id = product["id"]

    # 2. Create Stripe Price
    stripe_price = await _create_stripe_price(product_id, price_yen)
    price_id = stripe_price["id"]

    # 3. Create Payment Link
    payment_link = await _create_payment_link(price_id)
    payment_url = payment_link["url"]

    # 4. Register in Notion DB
    notion_page = await _register_notion_product(
        title=title,
        description=description,
        price_yen=price_yen,
        stripe_product_id=product_id,
        payment_link_url=payment_url,
    )

    return JSONResponse(
        status_code=201,
        content={
            "stripe_product_id": product_id,
            "stripe_price_id": price_id,
            "payment_link": payment_url,
            "notion_page_id": notion_page.get("id", ""),
            "title": title,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8787)
