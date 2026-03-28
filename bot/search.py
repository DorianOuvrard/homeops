"""Product documentation search via Tavily."""

import logging

from tavily import TavilyClient

logger = logging.getLogger(__name__)

_DOC_DOMAINS = [
    "manualslib.com",
    "ifixit.com",
    "leroymerlin.fr",
    "manomano.fr",
    "boulanger.com",
    "darty.com",
]


def search_product_docs(api_key: str, query: str) -> dict:
    """Search for product documentation using Tavily."""
    client = TavilyClient(api_key=api_key)
    response = client.search(
        query=f"{query} fiche technique manuel documentation",
        search_depth="advanced",
        include_domains=_DOC_DOMAINS,
        max_results=5,
    )
    results = [
        {"title": r["title"], "url": r["url"], "content": r["content"]}
        for r in response.get("results", [])
    ]
    if not results:
        # Retry without domain restriction
        response = client.search(
            query=f"{query} fiche technique manuel documentation",
            search_depth="advanced",
            max_results=5,
        )
        results = [
            {"title": r["title"], "url": r["url"], "content": r["content"]}
            for r in response.get("results", [])
        ]
    return {"results": results, "query": query}
