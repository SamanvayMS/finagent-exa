"""Discover a ticker's subsidiaries and competitors via Exa structured search."""
from __future__ import annotations

from .client import ExaClient
from .models import Entities, Entity

DISCOVERY_SCHEMA: dict = {
    "type": "object",
    "description": "The company behind a stock ticker, its subsidiaries and competitors",
    "required": ["company_name"],
    "properties": {
        "company_name": {
            "type": "string",
            "description": "Full legal name of the company for the ticker",
        },
        "subsidiaries": {
            "type": "array",
            "description": "Notable subsidiaries / owned brands of the company",
            "items": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string", "description": "Subsidiary name"},
                    "description": {"type": "string", "description": "What it does"},
                },
            },
        },
        "competitors": {
            "type": "array",
            "description": "Primary publicly-known competitors of the company",
            "items": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string", "description": "Competitor name"},
                    "description": {"type": "string", "description": "What it does"},
                },
            },
        },
    },
}


def _to_entities(raw_list, relation: str) -> list[Entity]:
    out: list[Entity] = []
    for item in raw_list or []:
        if isinstance(item, dict) and item.get("name"):
            out.append(
                Entity(
                    name=item["name"],
                    relation=relation,
                    description=item.get("description"),
                )
            )
    return out


def discover_entities(client: ExaClient, ticker: str) -> tuple[str | None, Entities]:
    query = (
        f"Identify the company for stock ticker {ticker}, listing its major "
        f"subsidiaries and its primary competitors."
    )
    result = client.search(
        query,
        stage="discovery",
        type="auto",
        output_schema=DISCOVERY_SCHEMA,
    )
    content = getattr(getattr(result, "output", None), "content", None)
    if not isinstance(content, dict):
        return None, Entities()
    return (
        content.get("company_name"),
        Entities(
            subsidiaries=_to_entities(content.get("subsidiaries"), "subsidiary"),
            competitors=_to_entities(content.get("competitors"), "competitor"),
        ),
    )
