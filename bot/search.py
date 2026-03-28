"""Web search tools for product documentation and common issues via Tavily."""

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

_ISSUES_DOMAINS = [
    "commentreparer.com",
    "spareka.fr",
    "sosav.fr",
    "quechoisir.org",
    "electromenager-compare.com",
    "forums.futura-sciences.com",
    "bricolage.linternaute.com",
]


def _tavily_search(api_key: str, query: str, domains: list[str], max_results: int = 5) -> list[dict]:
    """Run a Tavily search with domain fallback."""
    client = TavilyClient(api_key=api_key)
    response = client.search(
        query=query,
        search_depth="advanced",
        include_domains=domains,
        max_results=max_results,
    )
    results = [
        {"title": r["title"], "url": r["url"], "content": r["content"]}
        for r in response.get("results", [])
    ]
    if not results:
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
        )
        results = [
            {"title": r["title"], "url": r["url"], "content": r["content"]}
            for r in response.get("results", [])
        ]
    return results


def search_product_docs(api_key: str, query: str) -> dict:
    """Search for product documentation using Tavily."""
    results = _tavily_search(
        api_key,
        f"{query} fiche technique manuel documentation",
        _DOC_DOMAINS,
    )
    return {"results": results, "query": query}


def search_common_issues(api_key: str, query: str) -> dict:
    """Search for recurring problems and common issues for an appliance."""
    results = _tavily_search(
        api_key,
        f"{query} problèmes fréquents pannes récurrentes avis",
        _ISSUES_DOMAINS,
    )
    return {"results": results, "query": query}
