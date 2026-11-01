import os

import requests
from dotenv import load_dotenv

load_dotenv()

WATCHMODE_BASE_URL = "https://api.watchmode.com/v1/title/{title_id}/sources/"
AVAILABILITY_LABELS = {
    "sub": "Subscription",
    "rent": "Rent",
    "buy": "Buy",
    "free": "Free",
    # Don't assume "tve" always means free with ads.
    "tve": "TV Everywhere",
}


def get_streaming_sources(title_id, region="IN"):
    """Fetch and normalize streaming sources from Watchmode."""
    api_key = os.getenv("WATCHMODE_API_KEY")
    if not api_key:
        raise RuntimeError("Watchmode API key configure nahi hai.")

    if isinstance(title_id, bool) or not str(title_id).strip():
        raise ValueError("Valid Watchmode title ID dena zaroori hai.")
    if not isinstance(region, str) or not region.strip():
        raise ValueError("Valid region code dena zaroori hai.")

    url = WATCHMODE_BASE_URL.format(title_id=str(title_id).strip())
    response = requests.get(
        url,
        params={"apiKey": api_key, "regions": region.strip().upper()},
        timeout=15,
    )
    response.raise_for_status()

    try:
        sources = response.json()
    except ValueError as exc:
        raise ValueError("Watchmode ne valid JSON response nahi diya.") from exc

    if not isinstance(sources, list):
        raise ValueError("Watchmode API ka response expected format mein nahi hai.")

    clean_sources = []
    seen = set()

    for source in sources:
        if not isinstance(source, dict):
            continue

        name = str(source.get("name") or "Unknown").strip()
        availability = str(source.get("type") or "").strip().lower()
        web_url = str(source.get("web_url") or "").strip()
        unique_key = (name.casefold(), availability, web_url.rstrip("/").casefold())

        if unique_key in seen:
            continue
        seen.add(unique_key)

        clean_sources.append({
            "platform": name,
            "availability": availability,
            "availability_label": AVAILABILITY_LABELS.get(availability, "Other"),
            "url": web_url or None,
        })

    return clean_sources
