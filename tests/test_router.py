"""Tests for request router and orchestrator."""

from agent.router import SkillRouter
from agent.orchestrator import Orchestrator
from agent.llm import MockLLMClient
from agent.skill_loader import SkillLoader


def test_deterministic_trigger_routing():
    router = SkillRouter()
    
    # "check Caspian" trigger should map to caspian_research
    decision = router.route_request("Please check Caspian repo")
    assert decision.selected_skill_id == "caspian_research"
    assert decision.is_direct_match is True
    assert decision.confidence == 1.0

    # "daily ai updates" trigger should map to daily_briefing
    decision2 = router.route_request("Give me the daily AI updates")
    assert decision2.selected_skill_id == "daily_briefing"
    assert decision2.is_direct_match is True


def test_llm_fallback_routing():
    mock_llm = MockLLMClient()
    mock_llm.queue_response({
        "selected_skill_id": "ai_intelligence",
        "confidence": 0.88,
        "reasoning": "User is asking to survey external arXiv papers.",
    })

    router = SkillRouter(llm_client=mock_llm)
    # Ambiguous phrase that doesn't match raw trigger
    decision = router.route_request("What did DeepMind publish about agents yesterday?")
    assert decision.selected_skill_id == "ai_intelligence"
    assert decision.is_direct_match is False
    assert decision.confidence == 0.88


def test_orchestrator_flow():
    mock_llm = MockLLMClient()
    router = SkillRouter(llm_client=mock_llm)
    orch = Orchestrator(router=router, llm_client=mock_llm)

    res = orch.process_message("check Caspian updates", user_id="henshawmike")
    assert res["success"] is True
    assert res["skill"]["id"] == "caspian_research"
    assert "scan_repository" in res["skill"]["available_tools"]


def test_orchestrator_unknown_request():
    mock_llm = MockLLMClient()
    mock_llm.queue_response({
        "selected_skill_id": None,
        "confidence": 0.0,
        "reasoning": "Unrelated topic.",
    })

    router = SkillRouter(llm_client=mock_llm)
    orch = Orchestrator(router=router, llm_client=mock_llm)

    res = orch.process_message("Tell me a recipe for pizza dough", user_id="henshawmike")
    assert res["success"] is False
    assert "not sure how to handle" in res["message"]
