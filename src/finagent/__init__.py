"""finagent — ticker impact-analysis tool library powered by Exa."""
from .agent import analyze_ticker
from .models import (
    Citation,
    Entities,
    Entity,
    Impact,
    ImpactDriver,
    NewsItem,
    TickerAnalysis,
)
from .tool import (
    TOOL_DESCRIPTION,
    TOOL_NAME,
    TOOL_PARAMETERS,
    build_tool_spec,
    run_tool,
)

__all__ = [
    "analyze_ticker",
    "TickerAnalysis",
    "Entity",
    "Entities",
    "NewsItem",
    "Impact",
    "ImpactDriver",
    "Citation",
    "build_tool_spec",
    "run_tool",
    "TOOL_NAME",
    "TOOL_DESCRIPTION",
    "TOOL_PARAMETERS",
]
