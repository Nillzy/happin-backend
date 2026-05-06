"""Unsplash image search proxy endpoint."""

import time
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()

UNSPLASH_SEARCH_URL = "https://api.unsplash.com/search/photos"
CACHE_TTL_SECONDS = 3600  # 1 hour

_cache: dict[str, tuple[float, list]] = {}


class StockImage(BaseModel):
    url: str
    thumbnail: str
    photographer: str
    unsplash_link: str


@router.get("/search", response_model=list[StockImage])
async def search_images(
    q: str = Query(..., min_length=1, description="Search query for stock images"),
    per_page: int = Query(8, ge=1, le=30),
) -> list[StockImage]:
    """Proxy endpoint for Unsplash image search.

    Keeps the API key server-side and caches results for 1 hour.
    """
    if not settings.UNSPLASH_ACCESS_KEY:
        raise HTTPException(
            status_code=503,
            detail="Unsplash API key not configured",
        )

    cache_key = f"{q.lower().strip()}:{per_page}"
    now = time.time()

    if cache_key in _cache:
        cached_time, cached_results = _cache[cache_key]
        if now - cached_time < CACHE_TTL_SECONDS:
            return cached_results

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            UNSPLASH_SEARCH_URL,
            params={
                "query": q,
                "per_page": per_page,
                "orientation": "landscape",
            },
            headers={
                "Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}",
                "Accept-Version": "v1",
            },
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Unsplash API error: {response.text}",
        )

    data = response.json()
    results: list[StockImage] = []

    for photo in data.get("results", []):
        results.append(
            StockImage(
                url=photo["urls"]["regular"],
                thumbnail=photo["urls"]["small"],
                photographer=photo["user"]["name"],
                unsplash_link=photo["user"]["links"]["html"],
            )
        )

    _cache[cache_key] = (now, results)
    return results
