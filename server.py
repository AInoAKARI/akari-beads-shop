"""Akari Beads Shop - Shopify商品自動登録API.

ビーズワークスの写真を撮ってShopifyに即登録するサービス。
Keymaster経由でShopify Admin APIトークンを取得。
"""

import base64
import os
from typing import Any

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from keymaster import get_key

app = FastAPI(title="Akari Beads Shop")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SHOPIFY_STORE_DOMAIN = os.environ.get("SHOPIFY_STORE_DOMAIN", "")
SHOPIFY_API_VERSION = "2024-01"


def _shopify_base_url() -> str:
    if not SHOPIFY_STORE_DOMAIN:
        raise HTTPException(status_code=500, detail="SHOPIFY_STORE_DOMAIN not configured")
    return f"https://{SHOPIFY_STORE_DOMAIN}/admin/api/{SHOPIFY_API_VERSION}"


async def _shopify_headers() -> dict[str, str]:
    token = await get_key("shopify", "api_key")
    return {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json",
    }


@app.get("/")
async def root():
    return {"service": "Akari Beads Shop", "status": "ok"}


@app.get("/health")
async def health():
    """ヘルスチェック（Keymaster接続確認含む）."""
    checks: dict[str, str] = {"service": "ok"}

    # Keymaster connectivity
    try:
        await get_key("shopify", "api_key")
        checks["keymaster"] = "ok"
    except Exception as e:
        checks["keymaster"] = f"error: {e}"

    # Shopify domain
    checks["shopify_domain"] = SHOPIFY_STORE_DOMAIN or "not configured"

    status_code = 200 if checks.get("keymaster") == "ok" and SHOPIFY_STORE_DOMAIN else 503
    return JSONResponse(status_code=status_code, content=checks)


@app.get("/products")
async def list_products():
    """登録済みビーズワークス一覧."""
    base = _shopify_base_url()
    headers = await _shopify_headers()

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{base}/products.json",
            headers=headers,
            params={"limit": 50, "status": "active"},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    data = resp.json()
    products = []
    for p in data.get("products", []):
        image = p.get("images", [{}])[0] if p.get("images") else {}
        products.append({
            "product_id": p["id"],
            "title": p["title"],
            "description": p.get("body_html", ""),
            "price": p.get("variants", [{}])[0].get("price", "0") if p.get("variants") else "0",
            "url": f"https://{SHOPIFY_STORE_DOMAIN}/products/{p.get('handle', '')}",
            "image_url": image.get("src", ""),
        })

    return {"products": products, "count": len(products)}


@app.post("/products/create")
async def create_product(
    title: str = Form(...),
    description: str = Form(""),
    price: str = Form("0"),
    creator_name: str = Form(""),
    event_name: str = Form(""),
    event_date: str = Form(""),
    photo: UploadFile | None = File(None),
):
    """写真+商品情報を受け取り、Shopify商品を作成する."""
    base = _shopify_base_url()
    headers = await _shopify_headers()

    # Build body_html with metadata
    body_parts = []
    if description:
        body_parts.append(f"<p>{description}</p>")
    if creator_name:
        body_parts.append(f"<p>つくった人: {creator_name}</p>")
    if event_name:
        body_parts.append(f"<p>イベント: {event_name}</p>")
    if event_date:
        body_parts.append(f"<p>イベント日: {event_date}</p>")
    body_html = "\n".join(body_parts) if body_parts else ""

    # Build product payload
    product_payload: dict[str, Any] = {
        "product": {
            "title": title,
            "body_html": body_html,
            "vendor": "Akari Beads Workshop",
            "product_type": "ビーズワークス",
            "status": "active",
            "variants": [
                {
                    "price": price,
                    "inventory_management": None,
                    "requires_shipping": True,
                }
            ],
            "tags": ", ".join(
                t for t in [
                    "beadworks",
                    creator_name,
                    event_name,
                ] if t
            ),
        }
    }

    # If photo provided, encode as base64 for Shopify image upload
    image_b64 = None
    if photo:
        photo_bytes = await photo.read()
        if photo_bytes:
            image_b64 = base64.b64encode(photo_bytes).decode("utf-8")
            product_payload["product"]["images"] = [
                {
                    "attachment": image_b64,
                    "filename": photo.filename or "beadwork.jpg",
                    "alt": title,
                }
            ]

    # Create product
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{base}/products.json",
            headers=headers,
            json=product_payload,
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    product = resp.json().get("product", {})
    product_id = product.get("id")
    handle = product.get("handle", "")
    product_url = f"https://{SHOPIFY_STORE_DOMAIN}/products/{handle}"
    image_url = ""
    if product.get("images"):
        image_url = product["images"][0].get("src", "")

    return JSONResponse(
        status_code=201,
        content={
            "status": "created",
            "product_id": product_id,
            "title": title,
            "url": product_url,
            "image_url": image_url,
            "message": f"✨ 「{title}」がショップに並びました！",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8788)
