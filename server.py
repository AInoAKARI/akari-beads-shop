"""Akari Beads Shop - Shopify product creation API."""

import base64
import os

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

app = FastAPI(title="Akari Beads Shop")

KEYMASTER_URL = os.environ.get("AKARI_KEYMASTER_URL", "")
KEYMASTER_TOKEN = os.environ.get("AKARI_KEYMASTER_TOKEN", "")
SHOPIFY_STORE = os.environ.get("SHOPIFY_STORE", "")


async def get_shopify_api_key() -> str:
    """Fetch Shopify API key from Keymaster at runtime."""
    if not KEYMASTER_URL or not KEYMASTER_TOKEN:
        raise HTTPException(status_code=500, detail="Keymaster not configured")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{KEYMASTER_URL}/vault/api-key",
            params={"api_name": "shopify", "key_name": "api_key"},
            headers={"Authorization": f"Bearer {KEYMASTER_TOKEN}"},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch Shopify API key")
    data = resp.json()
    return data.get("key") or data.get("value") or ""


def build_body_html(title: str, description: str) -> str:
    return f"""<div style="font-family: sans-serif;">
<h2>{title}</h2>
<p>{description}</p>
<hr>
<p><strong>きらきらあかりん食堂</strong>へようこそ！</p>
<p>ひとつひとつ心を込めて手作りしたビーズアクセサリーをお届けします。</p>
<p>あかりんの世界観をまとった、きらきら輝くアイテムたち。</p>
</div>"""


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/products")
async def list_products():
    api_key = await get_shopify_api_key()
    if not SHOPIFY_STORE:
        raise HTTPException(status_code=500, detail="SHOPIFY_STORE not configured")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"https://{SHOPIFY_STORE}/admin/api/2024-01/products.json",
            headers={
                "X-Shopify-Access-Token": api_key,
                "Content-Type": "application/json",
            },
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@app.post("/products/create")
async def create_product(
    title: str = Form(...),
    description: str = Form(""),
    price: str = Form("0"),
    image: UploadFile = File(...),
):
    api_key = await get_shopify_api_key()
    if not SHOPIFY_STORE:
        raise HTTPException(status_code=500, detail="SHOPIFY_STORE not configured")

    image_data = await image.read()
    image_b64 = base64.b64encode(image_data).decode()

    body_html = build_body_html(title, description)

    payload = {
        "product": {
            "title": title,
            "body_html": body_html,
            "variants": [
                {
                    "price": price,
                    "inventory_management": None,
                    "inventory_quantity": 1,
                }
            ],
            "images": [
                {
                    "attachment": image_b64,
                    "filename": image.filename or "product.jpg",
                }
            ],
        }
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"https://{SHOPIFY_STORE}/admin/api/2024-01/products.json",
            headers={
                "X-Shopify-Access-Token": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return JSONResponse(status_code=201, content=resp.json())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8787)
