"""Skill loader and Markdown specification parser."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from agent.schemas import SkillMetadata, SkillRegistryFile, ParsedSkill
from agent.config import settings
from agent.logging_config import logger


MANDATORY_SECTIONS = [
    "Identity",
    "Activation Conditions",
    "Required Inputs",
    "Available Tools",
    "Tool Routing Rules",
    "Execution Workflow",
    "Decision Rules",
    "Output Contract",
    "Failure Handling",
    "Restrictions",
    "Completion Criteria",
]


class SkillLoaderError(Exception):
    """Exception raised when skill loading or parsing fails."""
    pass


class SkillLoader:
    """Discovers, parses, and validates SKILL.md documents."""

    def __init__(self, registry_path: Optional[Path] = None):
        self.skills_dir = settings.skills_dir
        self.registry_path = registry_path or (self.skills_dir / "registry.json")
        self._skills_metadata: Dict[str, SkillMetadata] = {}
        self._parsed_skills_cache: Dict[str, ParsedSkill] = {}
        self.load_registry()

    def load_registry(self) -> None:
        """Load and parse skills/registry.json."""
        if not self.registry_path.is_file():
            logger.warning(f"Skill registry not found at {self.registry_path}")
            return

        with open(self.registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        reg = SkillRegistryFile(**data)
        self._skills_metadata = {s.id: s for s in reg.skills}
        logger.info(f"Loaded {len(self._skills_metadata)} skills from registry.")

    def get_all_skills_metadata(self) -> List[SkillMetadata]:
        """Return metadata for all registered skills."""
        return list(self._skills_metadata.values())

    def get_metadata(self, skill_id: str) -> Optional[SkillMetadata]:
        """Retrieve metadata for a specific skill."""
        return self._skills_metadata.get(skill_id)

    def load_skill(self, skill_id: str) -> ParsedSkill:
        """Load, parse, and validate a skill by its ID."""
        if skill_id in self._parsed_skills_cache:
            return self._parsed_skills_cache[skill_id]

        meta = self.get_metadata(skill_id)
        if not meta:
            raise SkillLoaderError(f"Skill ID '{skill_id}' not found in registry.")

        skill_file = settings.base_dir / meta.path
        if not skill_file.is_file():
            raise SkillLoaderError(f"Skill file not found at {skill_file}")

        with open(skill_file, "r", encoding="utf-8") as f:
            raw_text = f.read()

        parsed = self.parse_skill_markdown(raw_text, skill_id=skill_id)
        self._parsed_skills_cache[skill_id] = parsed
        return parsed

    @staticmethod
    def parse_skill_markdown(raw_markdown: str, skill_id: str = "") -> ParsedSkill:
        """
        Parse raw markdown ensuring the 11 mandatory sections are present.
        """
        lines = raw_markdown.splitlines()
        
        # 1. Extract title
        title = ""
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                break

        if not title:
            raise SkillLoaderError(f"Skill '{skill_id}' is missing a top-level '# Title' heading.")

        # 2. Extract sections by `## <number>. <Name>` or `## <Name>`
        section_pattern = re.compile(r"^##\s+(?:\d+\.\s*)?([^\n\r]+)", re.MULTILINE)
        matches = list(section_pattern.finditer(raw_markdown))

        if not matches:
            raise SkillLoaderError(f"Skill '{skill_id}' contains no '## Section' headings.")

        sections_dict: Dict[str, str] = {}
        for i, match in enumerate(matches):
            sec_name = match.group(1).strip()
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(raw_markdown)
            sec_content = raw_markdown[start_pos:end_pos].strip()
            sections_dict[sec_name.lower()] = sec_content

        # 3. Verify all mandatory sections
        missing = []
        normalized_map: Dict[str, str] = {}
        for req in MANDATORY_SECTIONS:
            content = sections_dict.get(req.lower())
            if content is None:
                missing.append(req)
            else:
                normalized_map[req] = content

        if missing:
            raise SkillLoaderError(
                f"Skill '{skill_id}' is missing mandatory sections: {', '.join(missing)}"
            )

        # 4. Extract tools from Section 4 "Available Tools"
        tools_text = normalized_map.get("Available Tools", "")
        # Find tools wrapped in backticks or bullet points e.g. - `tool_name`
        tool_names = re.findall(r"`([a-zA-Z0-9_-]+)`", tools_text)
        if not tool_names:
            # Fallback to lines starting with - or *
            for l in tools_text.splitlines():
                clean_l = l.strip().lstrip("-* ").strip()
                if clean_l and not clean_l.startswith("#"):
                    tool_names.append(clean_l.split()[0].replace("`", ""))

        return ParsedSkill(
            name=title,
            identity=normalized_map["Identity"],
            activation_conditions=normalized_map["Activation Conditions"],
            required_inputs=normalized_map["Required Inputs"],
            available_tools=tool_names,
            tool_routing_rules=normalized_map["Tool Routing Rules"],
            execution_workflow=normalized_map["Execution Workflow"],
            decision_rules=normalized_map["Decision Rules"],
            output_contract=normalized_map["Output Contract"],
            failure_handling=normalized_map["Failure Handling"],
            restrictions=normalized_map["Restrictions"],
            completion_criteria=normalized_map["Completion Criteria"],
            raw_markdown=raw_markdown,
        )


# Global default skill loader
skill_loader = SkillLoader()
