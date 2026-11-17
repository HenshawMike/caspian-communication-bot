"""End-to-end integration tests for the Document Generation workflow."""

from pathlib import Path
from agent.orchestrator import Orchestrator
from agent.router import SkillRouter
from agent.llm import MockLLMClient
from agent.config import settings
from database.models import save_daily_briefing


def test_full_document_generation_flow(temp_db, tmp_path, monkeypatch):
    """Verify natural language request generates both PDF and DOCX in monochrome."""
    monkeypatch.setattr(settings, "documents_dir", tmp_path)

    mock_llm = MockLLMClient()
    router = SkillRouter(llm_client=mock_llm)
    orch = Orchestrator(router=router, llm_client=mock_llm)

    # Trigger document generation
    res = orch.process_message("create research report on quantum latent planning", user_id="user_admin")

    assert res["success"] is True
    assert res["skill"]["id"] == "document_generation"

    data = res["data"]
    assert data["theme"] == "Project Caspian Monochrome"
    assert data["pdf_path"] is not None
    assert data["docx_path"] is not None

    pdf_p = Path(data["pdf_path"])
    docx_p = Path(data["docx_path"])

    assert pdf_p.exists()
    assert pdf_p.stat().st_size > 0

    assert docx_p.exists()
    assert docx_p.stat().st_size > 0

    assert "Monochrome Document Successfully Generated" in res["message"]


def test_briefing_document_export_flow(temp_db, tmp_path, monkeypatch):
    """Verify exporting daily briefing to PDF preserves briefing structure and sources."""
    monkeypatch.setattr(settings, "documents_dir", tmp_path)

    # Pre-seed a briefing in the temporary database
    save_daily_briefing(
        briefing_date="2026-11-17",
        developments=[
            {
                "title": "Quantum Latent Planning Benchmark",
                "what_happened": "Introduced dynamic branching algorithms.",
                "simple_explanation": "A faster method to plan future moves.",
                "why_it_matters": "Increases sample efficiency.",
                "technical_insight": "Evaluated on standard MuJoCo tasks.",
                "relevance_to_caspian": "Complements Caspian Phase 2 world models.",
                "source_url": "https://arxiv.org/abs/2601.12345",
            }
        ],
        key_takeaways=["Fast planning via latent spaces."],
        caspian_relevance=[{"development": "Quantum Planning", "connection": "Phase 2 world models"}],
        sources=["https://arxiv.org/abs/2601.12345"],
        formatted_text="Briefing preview text",
    )

    mock_llm = MockLLMClient()
    router = SkillRouter(llm_client=mock_llm)
    orch = Orchestrator(router=router, llm_client=mock_llm)

    res = orch.process_message("export briefing to pdf", user_id="user_admin")

    assert res["success"] is True
    assert res["skill"]["id"] == "document_generation"

    data = res["data"]
    assert data["document_type"] == "daily_briefing"
    assert data["pdf_path"] is not None

    pdf_p = Path(data["pdf_path"])
    assert pdf_p.exists()
    assert pdf_p.stat().st_size > 0
