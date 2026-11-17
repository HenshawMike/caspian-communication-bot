"""Tests for skill loading and Markdown parsing."""

import pytest
from agent.skill_loader import SkillLoader, SkillLoaderError


VALID_SKILL_MD = """# Test Skill

## 1. Identity
Responsible for testing skill parsing.

## 2. Activation Conditions
When test runs.

## 3. Required Inputs
Test parameters.

## 4. Available Tools
- `test_tool_a`
- `test_tool_b`

## 5. Tool Routing Rules
Call tool a then tool b.

## 6. Execution Workflow
1. Execute tool a.
2. Execute tool b.

## 7. Decision Rules
Proceed on success.

## 8. Output Contract
```json
{"status": "ok"}
```

## 9. Failure Handling
Log and fail gracefully.

## 10. Restrictions
Never modify external state.

## 11. Completion Criteria
When tests pass.
"""


def test_parse_valid_skill():
    parsed = SkillLoader.parse_skill_markdown(VALID_SKILL_MD, skill_id="test_skill")
    assert parsed.name == "Test Skill"
    assert "test_tool_a" in parsed.available_tools
    assert "test_tool_b" in parsed.available_tools
    assert parsed.identity == "Responsible for testing skill parsing."
    assert parsed.completion_criteria == "When tests pass."


def test_parse_skill_missing_mandatory_section():
    # Remove Section 10 Restrictions
    invalid_md = VALID_SKILL_MD.replace("## 10. Restrictions\nNever modify external state.", "")
    with pytest.raises(SkillLoaderError) as exc_info:
        SkillLoader.parse_skill_markdown(invalid_md, skill_id="invalid_skill")
    assert "missing mandatory sections" in str(exc_info.value)
    assert "Restrictions" in str(exc_info.value)


def test_load_caspian_research_skill():
    loader = SkillLoader()
    skill = loader.load_skill("caspian_research")
    assert skill.name == "Caspian Research"
    assert "scan_repository" in skill.available_tools
    assert "check_disclosure" in skill.available_tools
