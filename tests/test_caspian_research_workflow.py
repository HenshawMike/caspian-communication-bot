"""End-to-end integration test for Caspian Research skill workflow."""

from pathlib import Path
from agent.orchestrator import Orchestrator
from agent.router import SkillRouter
from agent.permissions import create_default_context
from agent.llm import MockLLMClient


def test_caspian_research_workflow_execution(tmp_path):
    # 1. Setup mock research repository with public and restricted reports
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    public_report = reports_dir / "report_world_model.md"
    public_report.write_text(
        """# Sample World Model Report
<!-- DISCLOSURE: PUBLIC -->
experiment_id: EXP-PUBLIC-01

## Findings
Latent representations converged 30% faster with auxiliary prediction targets.

## Limitations
Requires high GPU memory during warm-up phase.
""",
        encoding="utf-8",
    )

    internal_report = reports_dir / "report_internal_architecture.md"
    internal_report.write_text(
        """# Proprietary Training Infrastructure
<!-- DISCLOSURE: INTERNAL -->
experiment_id: EXP-INTERNAL-02

## Findings
Internal cluster deployment configurations.
""",
        encoding="utf-8",
    )

    # 2. Run orchestrator on message
    mock_llm = MockLLMClient()
    router = SkillRouter(llm_client=mock_llm)
    orch = Orchestrator(router=router, llm_client=mock_llm)

    ctx = create_default_context(user_id="researcher_1", skill_id="caspian_research")

    # Pass the tmp_path as repo_path in workflow
    res = orch.execute_caspian_research_workflow(context=ctx, repository_path=None)

    assert "data" in res
    data = res["data"]
    assert "research_updates" in data
    assert "important_findings" in data
    assert "limitations" in data
    assert "public_opportunities" in data
    assert "restricted_items" in data
    assert "source_references" in data

    # Verify structured message summary
    assert "Project Caspian Research Scan" in res["message"]


def test_caspian_research_triggered_via_message():
    mock_llm = MockLLMClient()
    router = SkillRouter(llm_client=mock_llm)
    orch = Orchestrator(router=router, llm_client=mock_llm)

    result = orch.process_message("scan Caspian repository updates", user_id="researcher_1")
    assert result["success"] is True
    assert result["skill"]["id"] == "caspian_research"
    assert "Project Caspian Research Scan" in result["message"]
    assert "data" in result
    assert isinstance(result["data"]["public_opportunities"], list)
    assert isinstance(result["data"]["restricted_items"], list)
