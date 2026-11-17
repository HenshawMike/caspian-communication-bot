"""Execution orchestrator tying together routing, skills, tools, and permissions."""

from typing import Any, Dict, Optional
from agent.config import settings
from agent.router import SkillRouter, router as default_router
from agent.skill_loader import SkillLoader, skill_loader as default_loader
from agent.tool_registry import ToolRegistry, registry as default_registry
from agent.tool_executor import ToolExecutor, executor as default_executor
from agent.permissions import PermissionContext, create_default_context
from agent.llm import LLMClient, get_llm_client
from agent.logging_config import logger


class Orchestrator:
    """Coordinates skill routing, tool permissions, and LLM reasoning."""

    def __init__(
        self,
        router: Optional[SkillRouter] = None,
        loader: Optional[SkillLoader] = None,
        tool_registry: Optional[ToolRegistry] = None,
        tool_executor: Optional[ToolExecutor] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        self.router = router or default_router
        self.loader = loader or default_loader
        self.registry = tool_registry or default_registry
        self.executor = tool_executor or default_executor
        self.llm = llm_client or get_llm_client()

    def process_message(
        self,
        user_message: str,
        user_id: Optional[str] = None,
        context: Optional[PermissionContext] = None,
    ) -> Dict[str, Any]:
        """
        Process an incoming message: route, load skill, validate permissions, and execute.
        """
        logger.info(f"Processing message for user '{user_id}': {user_message[:60]}...")
        
        # 1. Route the request
        route_decision = self.router.route_request(user_message)
        
        if not route_decision.selected_skill_id:
            return {
                "success": False,
                "message": (
                    "I am not sure how to handle this request. "
                    "You can ask me to scan the Caspian repository, check AI research, "
                    "prepare a daily briefing, or publish content."
                ),
                "routing": route_decision.model_dump(),
            }

        # 2. Load the designated skill
        skill_id = route_decision.selected_skill_id
        try:
            parsed_skill = self.loader.load_skill(skill_id)
        except Exception as e:
            logger.error(f"Failed to load skill '{skill_id}': {e}")
            return {
                "success": False,
                "message": f"Error loading instructions for skill '{skill_id}'.",
                "routing": route_decision.model_dump(),
                "error": str(e),
            }

        # 3. Setup security & permission context
        perm_ctx = context or create_default_context(user_id=user_id, skill_id=skill_id)
        perm_ctx.active_skill = skill_id

        # 4. Synthesize prompt with skill instructions and permissible tools
        available_tools = parsed_skill.available_tools
        logger.info(
            f"Activated skill '{parsed_skill.name}'. Permissible tools: {available_tools}"
        )

        return {
            "success": True,
            "skill": {
                "id": skill_id,
                "name": parsed_skill.name,
                "available_tools": available_tools,
            },
            "routing": route_decision.model_dump(),
            "message": f"Skill '{parsed_skill.name}' activated for execution.",
        }


# Global default orchestrator
orchestrator = Orchestrator()
