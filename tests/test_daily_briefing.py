"""Tests for Daily AI Briefing skill and workflow."""

from agent.orchestrator import Orchestrator
from agent.router import SkillRouter
from agent.permissions import create_default_context
from agent.llm import MockLLMClient
from database.models import (
    save_daily_briefing,
    get_latest_daily_briefing,
    save_caspian_research,
    save_external_knowledge,
)


def test_save_and_get_daily_briefing(temp_db):
    devs = [{
        "title": "New State Space Architecture",
        "what_happened": "Linear time sequence model introduced.",
        "simple_explanation": "Processes sequences faster without quadratic memory cost.",
        "why_it_matters": "Enables ultra-long context windows.",
        "technical_insight": "Selective state space mechanism.",
        "relevance_to_caspian": "Aligns with Caspian representation goals.",
        "source_url": "https://arxiv.org/abs/2611.55555",
    }]
    takeaways = ["State space models reduce sequence processing overhead."]
    caspian_rel = [{"development": "New State Space Architecture", "connection": "Shares SSM principles."}]
    sources = ["https://arxiv.org/abs/2611.55555"]
    text = "DAILY AI INTELLIGENCE\n1. New State Space Architecture"

    row_id = save_daily_briefing(
        briefing_date="2026-11-17",
        developments=devs,
        key_takeaways=takeaways,
        caspian_relevance=caspian_rel,
        sources=sources,
        formatted_text=text,
        manager=temp_db,
    )
    assert row_id is not None
    assert row_id > 0

    latest = get_latest_daily_briefing(manager=temp_db)
    assert latest is not None
    assert latest["briefing_date"] == "2026-11-17"
    assert len(latest["developments"]) == 1
    assert latest["developments"][0]["title"] == "New State Space Architecture"
    assert latest["sources"] == sources


def test_daily_briefing_workflow_execution(temp_db):
    # Pre-populate stored knowledge and Caspian context
    save_caspian_research(
        title="Latent Dynamics Navigation",
        experiment_id="EXP-101",
        findings="Compression improved navigation memory by 40%.",
        disclosure_status="PUBLIC",
        manager=temp_db,
    )
    save_external_knowledge(
        title="Scalable World Models for Autonomous Agents",
        source_url="https://arxiv.org/abs/2611.66666",
        source_name="arXiv",
        publication_date="2026-11-17",
        research_type="preprint",
        topic="world_models",
        summary="A study of latent world models for continuous navigation.",
        central_contribution="Combines diffusion decoders with latent dynamics.",
        relevance_score=0.9,
        importance_score=0.9,
        manager=temp_db,
    )

    mock_llm = MockLLMClient()
    router = SkillRouter(llm_client=mock_llm)
    orch = Orchestrator(router=router, llm_client=mock_llm)

    ctx = create_default_context(user_id="briefing_user", skill_id="daily_briefing")
    result = orch.execute_daily_briefing_workflow(context=ctx, briefing_date="2026-11-17")

    assert "data" in result
    data = result["data"]
    assert data["briefing_date"] == "2026-11-17"
    assert len(data["developments"]) >= 1
    assert len(data["sources"]) >= 1

    # Verify structured message contains all required format sections
    msg = result["message"]
    assert "DAILY AI INTELLIGENCE" in msg
    assert "What happened:" in msg
    assert "Simple explanation:" in msg
    assert "Why it matters:" in msg
    assert "Technical insight:" in msg
    assert "Relevance to Caspian:" in msg
    assert "Original source:" in msg


def test_daily_briefing_triggered_via_message():
    mock_llm = MockLLMClient()
    router = SkillRouter(llm_client=mock_llm)
    orch = Orchestrator(router=router, llm_client=mock_llm)

    result = orch.process_message("Give me the daily AI updates", user_id="briefing_user")
    assert result["success"] is True
    assert result["skill"]["id"] == "daily_briefing"
    assert "DAILY AI INTELLIGENCE" in result["message"]
    assert "data" in result
    assert "developments" in result["data"]
