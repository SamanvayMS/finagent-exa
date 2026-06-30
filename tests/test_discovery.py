from types import SimpleNamespace

from finagent.discovery import discover_entities, DISCOVERY_SCHEMA
from finagent.models import Entities


class StubClient:
    def __init__(self, output):
        self._output = output
        self.last_kwargs = None

    def search(self, query, *, stage, **kwargs):
        self.last_kwargs = kwargs
        return SimpleNamespace(output=SimpleNamespace(content=self._output))


def test_schema_has_no_citation_fields():
    props = DISCOVERY_SCHEMA["properties"]
    assert "subsidiaries" in props and "competitors" in props
    assert "citations" not in props and "confidence" not in props


def test_discover_parses_entities():
    client = StubClient({
        "company_name": "Apple Inc.",
        "subsidiaries": [{"name": "Beats", "description": "audio"}],
        "competitors": [{"name": "Samsung"}],
    })
    name, entities = discover_entities(client, "AAPL")
    assert name == "Apple Inc."
    assert isinstance(entities, Entities)
    assert entities.subsidiaries[0].name == "Beats"
    assert entities.subsidiaries[0].relation == "subsidiary"
    assert entities.competitors[0].relation == "competitor"
    assert client.last_kwargs["type"] == "auto"
    assert client.last_kwargs["output_schema"] is DISCOVERY_SCHEMA


def test_discover_degrades_gracefully():
    client = StubClient(None)
    name, entities = discover_entities(client, "AAPL")
    assert name is None
    assert entities.subsidiaries == [] and entities.competitors == []
