"""Akari Beads Shop - Shopify product creation API."""

import base64
import os

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from keymaster import get_key
from webhook_handler import router as webhook_router

app = FastAPI(title="Akari Beads Shop")

SHOPIFY_STORE = os.environ.get("SHOPIFY_STORE", "")
app.include_router(webhook_router)


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
    api_key = await get_key("shopify", "api_key")
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
    api_key = await get_key("shopify", "api_key")
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
