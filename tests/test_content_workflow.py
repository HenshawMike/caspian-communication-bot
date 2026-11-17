"""Tests for Content Publishing generation and approval workflows."""

from agent.orchestrator import Orchestrator
from agent.router import SkillRouter
from agent.permissions import create_default_context
from agent.llm import MockLLMClient
from database.models import get_content_draft


def test_content_generation_single_post():
    mock_llm = MockLLMClient()
    router = SkillRouter(llm_client=mock_llm)
    orch = Orchestrator(router=router, llm_client=mock_llm)

    res = orch.process_message("write a post about world models", user_id="author_1")
    assert res["success"] is True
    assert res["skill"]["id"] == "content_publishing"
    data = res["data"]
    assert "draft_id" in data
    assert data["content_type"] == "single_post"
    assert data["approval_status"] == "PENDING"
    assert "Proposed Draft" in res["message"]
    assert "approve draft" in res["message"]

    # Verify persisted in DB
    draft = get_content_draft(data["draft_id"])
    assert draft is not None
    assert draft["approval_status"] == "PENDING"


def test_content_generation_thread():
    mock_llm = MockLLMClient()
    router = SkillRouter(llm_client=mock_llm)
    orch = Orchestrator(router=router, llm_client=mock_llm)

    res = orch.process_message("generate a thread about autonomous reasoning agents", user_id="author_1")
    assert res["success"] is True
    data = res["data"]
    assert data["content_type"] == "thread"
    assert "1/" in data["content"]
    assert "2/" in data["content"]


def test_user_approval_flow():
    mock_llm = MockLLMClient()
    router = SkillRouter(llm_client=mock_llm)
    orch = Orchestrator(router=router, llm_client=mock_llm)

    # 1. Generate draft
    gen_res = orch.process_message("write a post on reinforcement learning", user_id="author_1")
    draft_id = gen_res["data"]["draft_id"]

    # 2. Approve draft
    appr_res = orch.process_message(f"approve draft {draft_id}", user_id="author_1")
    assert appr_res["success"] is True
    assert appr_res["data"]["approval_status"] == "APPROVED"
    assert "Draft APPROVED" in appr_res["message"]

    # Verify DB status
    draft = get_content_draft(draft_id)
    assert draft["approval_status"] == "APPROVED"
