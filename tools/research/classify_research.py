"""Research classification and relevance assessment tool."""

import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from agent.logging_config import logger


TOPIC_KEYWORDS = {
    "world_models": ["world model", "latent dynamic", "recurrent state space", "rssm", "dreamer", "environmental model"],
    "reasoning_agents": ["reasoning", "chain of thought", "planning", "agentic", "tool use", "reflection", "tree of thoughts"],
    "reinforcement_learning": ["reinforcement learning", "policy gradient", "q-learning", "reward", "actor-critic", "ppo"],
    "multimodal": ["multimodal", "vision-language", "vlm", "audio", "video model", "cross-modal"],
    "evaluation_benchmarks": ["benchmark", "evaluation", "leaderboard", "metric", "empirical comparison"],
}


class ClassifyResearchInput(BaseModel):
    """Input parameters for classify_research."""
    title: str = Field(description="Title of the research publication.")
    text: str = Field(description="Cleaned text or abstract.")
    source_url: str = Field(description="Source URL.")


class ClassifyResearchOutput(BaseModel):
    """Output schema for classify_research."""
    success: bool
    title: str
    research_type: str
    topic: str
    central_contribution: str
    relevance_score: float
    importance_score: float
    keywords: List[str] = Field(default_factory=list)


def _detect_research_type(url: str, text: str) -> str:
    """Classify the nature of the publication."""
    low_url = url.lower()
    low_text = text.lower()

    if "arxiv.org" in low_url or "biorxiv" in low_url or "medrxiv" in low_url:
        return "preprint"
    if any(k in low_text for k in ["we announce", "announcing", "today we are releasing", "introducing"]):
        return "announcement"
    if any(k in low_text for k in ["in my opinion", "we argue that", "commentary", "perspective", "editorial"]):
        return "opinion"
    if any(k in low_text for k in ["state-of-the-art", "sota", "outperforms baseline by", "empirical results", "we evaluate on"]):
        return "experimental_result"
    if any(k in low_url for k in ["acm.org", "ieee.org", "nature.com", "openreview.net"]):
        return "peer_reviewed_paper"
    return "article"


def _detect_topic(text: str) -> tuple[str, List[str]]:
    """Determine dominant topic and matched keywords."""
    low_text = text.lower()
    best_topic = "general_ai"
    best_score = 0
    matched_keywords: List[str] = []

    for topic, keywords in TOPIC_KEYWORDS.items():
        found = [k for k in keywords if k in low_text]
        if len(found) > best_score:
            best_score = len(found)
            best_topic = topic
            matched_keywords = found

    return best_topic, matched_keywords


@register_tool(
    name="classify_research",
    description="Classify AI research type (preprint, paper, announcement), topic, and importance scores.",
    permission=PermissionScope.EXTERNAL_READ,
    args_model=ClassifyResearchInput,
    output_model=ClassifyResearchOutput,
)
def classify_research(
    title: str,
    text: str,
    source_url: str,
) -> Dict[str, Any]:
    """Classify research publication."""
    research_type = _detect_research_type(source_url, text)
    topic, keywords = _detect_topic(f"{title} {text}")

    # Compute heuristic relevance (high for world models and reasoning agents)
    relevance = 0.5
    if topic in ("world_models", "reasoning_agents"):
        relevance = 0.9
    elif topic in ("reinforcement_learning", "evaluation_benchmarks"):
        relevance = 0.75

    # Compute heuristic importance (boosted for preprints with strong keywords)
    importance = 0.6
    if len(keywords) >= 2:
        importance += 0.2
    if research_type in ("peer_reviewed_paper", "experimental_result"):
        importance += 0.1
    importance = min(1.0, importance)

    # Extract central contribution
    first_sentence = text.split(".")[0].strip() if text else title
    contribution = f"{title}: {first_sentence}"[:300]

    return {
        "success": True,
        "title": title,
        "research_type": research_type,
        "topic": topic,
        "central_contribution": contribution,
        "relevance_score": round(relevance, 2),
        "importance_score": round(importance, 2),
        "keywords": keywords,
    }
