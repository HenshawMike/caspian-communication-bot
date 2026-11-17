"""End-to-end integration tests for Publishing and Scheduling workflows."""

from agent.orchestrator import Orchestrator
from agent.router import SkillRouter
from agent.llm import MockLLMClient
from database.models import get_content_draft


def test_full_publish_flow(temp_db):
    mock_llm = MockLLMClient()
    router = SkillRouter(llm_client=mock_llm)
    orch = Orchestrator(router=router, llm_client=mock_llm)

    # 1. Draft post with unique run ID
    draft_res = orch.process_message("write a post about quantum latent planning", user_id="user_admin")
    draft_id = draft_res["data"]["draft_id"]

    # 2. Attempt publish before approval (should fail)
    early_pub = orch.process_message(f"publish draft {draft_id}", user_id="user_admin")
    assert "rejected" in early_pub["message"].lower()

    # 3. Approve draft
    appr_res = orch.process_message(f"approve draft {draft_id}", user_id="user_admin")
    assert appr_res["data"]["approval_status"] == "APPROVED"

    # 4. Publish draft after approval
    pub_res = orch.process_message(f"publish draft {draft_id}", user_id="user_admin")
    assert "Published to X Successfully" in pub_res["message"]

    # 5. Attempt second publication (must be prevented by duplicate check)
    dup_res = orch.process_message(f"publish draft {draft_id}", user_id="user_admin")
    assert "already published" in dup_res["message"].lower() or "rejected" in dup_res["message"].lower()


def test_schedule_management_flow(temp_db):
    mock_llm = MockLLMClient()
    router = SkillRouter(llm_client=mock_llm)
    orch = Orchestrator(router=router, llm_client=mock_llm)

    # Pause schedule
    pause_res = orch.process_message("pause schedule", user_id="user_admin")
    assert "paused" in pause_res["message"].lower()

    # Resume schedule
    resume_res = orch.process_message("resume schedule", user_id="user_admin")
    assert "resumed" in resume_res["message"].lower()
