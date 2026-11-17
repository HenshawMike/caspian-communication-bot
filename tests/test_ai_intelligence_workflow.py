"""Tests for AI Intelligence skill orchestration workflow."""

from agent.orchestrator import Orchestrator
from agent.router import SkillRouter
from agent.permissions import create_default_context
from agent.llm import MockLLMClient


def test_ai_intelligence_workflow_execution():
    mock_llm = MockLLMClient()
    router = SkillRouter(llm_client=mock_llm)
    orch = Orchestrator(router=router, llm_client=mock_llm)

    ctx = create_default_context(user_id="researcher_2", skill_id="ai_intelligence")
    res = orch.execute_ai_intelligence_workflow(context=ctx, query="world models")

    assert "data" in res
    data = res["data"]
    assert "sources_collected" in data
    assert "research_topics" in data
    assert "important_developments" in data
    assert "knowledge_saved" in data
    assert "collection_errors" in data

    assert len(data["sources_collected"]) >= 1
    assert "AI Intelligence Research Collection" in res["message"]


def test_ai_intelligence_triggered_via_message():
    mock_llm = MockLLMClient()
    router = SkillRouter(llm_client=mock_llm)
    orch = Orchestrator(router=router, llm_client=mock_llm)

    result = orch.process_message("find AI research on world models", user_id="researcher_2")
    assert result["success"] is True
    assert result["skill"]["id"] == "ai_intelligence"
    assert "AI Intelligence Research Collection" in result["message"]
    assert "data" in result
    assert isinstance(result["data"]["knowledge_saved"], list)
