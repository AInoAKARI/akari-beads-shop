"""Akari Beads Shop - Shopify product creation API."""

import base64
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

SHOPIFY_STORE = os.environ.get("SHOPIFY_STORE", "")
KEYMASTER_URL = os.environ.get("AKARI_KEYMASTER_URL", "")
KEYMASTER_TOKEN = os.environ.get("AKARI_KEYMASTER_TOKEN", "")

_http: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _http
    _http = httpx.AsyncClient(timeout=30)
    yield
    await _http.aclose()


app = FastAPI(title="Akari Beads Shop", lifespan=lifespan)


async def _get_shopify_key() -> str:
    resp = await _http.get(
        f"{KEYMASTER_URL}/vault/api-key",
        params={"api_name": "shopify", "key_name": "api_key"},
        headers={"Authorization": f"Bearer {KEYMASTER_TOKEN}"},
    )
    if resp.status_code != 200:
        raise HTTPException(502, "Failed to fetch Shopify API key from Keymaster")
    return resp.json()["value"]


def _body_html(title: str, description: str) -> str:
    return (
        '<div style="font-family: sans-serif;">'
        f"<h2>{title}</h2>"
        f"<p>{description}</p>"
        "<hr>"
        "<p><strong>きらきらあかりん食堂</strong>へようこそ！</p>"
        "<p>ひとつひとつ心を込めて手作りしたビーズアクセサリーをお届けします。</p>"
        "<p>あかりんの世界観をまとった、きらきら輝くアイテムたち。</p>"
        "</div>"
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/products")
async def list_products():
    api_key = await _get_shopify_key()
    resp = await _http.get(
        f"https://{SHOPIFY_STORE}/admin/api/2024-01/products.json",
        headers={"X-Shopify-Access-Token": api_key},
    )
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, resp.text)
    return resp.json()


@app.post("/products/create")
async def create_product(
    title: str = Form(...),
    description: str = Form(""),
    price: str = Form("0"),
    image: UploadFile = File(None),
):
    api_key = await _get_shopify_key()

    payload = {
        "product": {
            "title": title,
            "body_html": _body_html(title, description),
            "variants": [
                {
                    "price": price,
                    "inventory_management": None,
                    "inventory_quantity": 1,
                }
            ],
        }
    }

    if image:
        image_b64 = base64.b64encode(await image.read()).decode()
        payload["product"]["images"] = [
            {"attachment": image_b64, "filename": image.filename or "product.jpg"}
        ]

    resp = await _http.post(
        f"https://{SHOPIFY_STORE}/admin/api/2024-01/products.json",
        headers={
            "X-Shopify-Access-Token": api_key,
            "Content-Type": "application/json",
        },
        json=payload,
    )
    if resp.status_code not in (200, 201):
        raise HTTPException(resp.status_code, resp.text)
    return JSONResponse(status_code=201, content=resp.json())
