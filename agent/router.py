"""Request router matching user intent to appropriate skills."""

import re
from typing import Optional
from agent.schemas import RouteDecision
from agent.skill_loader import SkillLoader, skill_loader as default_loader
from agent.llm import LLMClient, get_llm_client
from agent.logging_config import logger


class SkillRouter:
    """Routes natural language user requests to the appropriate skill."""

    def __init__(
        self,
        loader: Optional[SkillLoader] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        self.loader = loader or default_loader
        self.llm = llm_client or get_llm_client()

    def route_request(self, message: str) -> RouteDecision:
        """Determine which skill should handle the user's request."""
        clean_text = self._normalize_text(message)
        if not clean_text:
            return RouteDecision(
                selected_skill_id=None,
                confidence=0.0,
                reasoning="Empty request text provided.",
                is_direct_match=False,
            )

        # 1. Deterministic trigger matching
        direct_match = self._match_triggers(clean_text)
        if direct_match:
            logger.info(f"Deterministic trigger matched skill: '{direct_match}'")
            return RouteDecision(
                selected_skill_id=direct_match,
                confidence=1.0,
                reasoning=f"Matched trigger keyword in request.",
                is_direct_match=True,
            )

        # 2. LLM-assisted routing for ambiguous natural language
        return self._route_with_llm(message)

    def _normalize_text(self, text: str) -> str:
        """Clean and normalize message string for matching."""
        return re.sub(r"\s+", " ", text).strip().lower()

    def _match_triggers(self, text: str) -> Optional[str]:
        """Check text against known triggers from the skill registry."""
        skills = self.loader.get_all_skills_metadata()
        text_words = set(re.findall(r"\b[a-zA-Z0-9_-]+\b", text))

        # 1. First pass: exact contiguous phrase match
        for skill in skills:
            for trigger in skill.triggers:
                trigger_clean = trigger.strip().lower()
                pattern = r"\b" + re.escape(trigger_clean) + r"\b"
                if re.search(pattern, text):
                    return skill.id

        # 2. Second pass: all trigger words present in user message
        for skill in skills:
            for trigger in skill.triggers:
                trigger_words = set(re.findall(r"\b[a-zA-Z0-9_-]+\b", trigger.strip().lower()))
                if trigger_words and trigger_words.issubset(text_words):
                    return skill.id

        return None

    def _route_with_llm(self, message: str) -> RouteDecision:
        """Use LLM to select the most appropriate skill."""
        skills = self.loader.get_all_skills_metadata()
        skills_summary = [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
            }
            for s in skills
        ]

        system_prompt = (
            "You are the Caspian Agent Router. Your job is to select the most relevant skill "
            "for a user's request from the available skills list. "
            "If no skill is relevant, return null for selected_skill_id. "
            "Respond ONLY with a JSON object containing: "
            "'selected_skill_id' (string or null), 'confidence' (float 0.0-1.0), and 'reasoning' (string)."
        )

        user_prompt = f"""Available skills:
{skills_summary}

User request: "{message}"

Determine the best skill ID. Return JSON:
{{"selected_skill_id": "<id or null>", "confidence": <float>, "reasoning": "<explanation>"}}
"""

        try:
            result = self.llm.generate_json(
                prompt=user_prompt,
                system_instruction=system_prompt,
            )
            selected_id = result.get("selected_skill_id")
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "LLM routing decision")

            # Validate that selected_id is actually in registry
            if selected_id and not self.loader.get_metadata(selected_id):
                logger.warning(f"LLM suggested unknown skill ID '{selected_id}'. Falling back to null.")
                selected_id = None
                confidence = 0.0

            return RouteDecision(
                selected_skill_id=selected_id,
                confidence=confidence,
                reasoning=reasoning,
                is_direct_match=False,
            )
        except Exception as e:
            logger.error(f"LLM routing failed: {e}")
            return RouteDecision(
                selected_skill_id=None,
                confidence=0.0,
                reasoning=f"Routing failure: {str(e)}",
                is_direct_match=False,
            )


# Global default router
router = SkillRouter()
