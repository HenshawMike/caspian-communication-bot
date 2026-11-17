"""Tool registry for Project Caspian."""

from typing import Any, Callable, Dict, List, Optional, Type
from pydantic import BaseModel
from agent.permissions import PermissionScope
from agent.logging_config import logger


class ToolDefinition(BaseModel):
    """Specification of a registered tool."""
    name: str
    description: str
    permission: str
    args_model: Optional[Type[BaseModel]] = None
    output_model: Optional[Type[BaseModel]] = None
    
    # Store function as arbitrary object in pydantic
    model_config = {"arbitrary_types_allowed": True}


class ToolRegistry:
    """Central authoritative registry of tools."""

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        description: str,
        permission: str | PermissionScope,
        args_model: Optional[Type[BaseModel]] = None,
        output_model: Optional[Type[BaseModel]] = None,
    ) -> Callable[[Callable], Callable]:
        """Decorator to register a tool function."""
        perm_str = permission.value if isinstance(permission, PermissionScope) else str(permission)

        def decorator(func: Callable) -> Callable:
            if name in self._tools:
                raise ValueError(f"Tool '{name}' is already registered.")

            self._tools[name] = {
                "name": name,
                "function": func,
                "description": description.strip(),
                "permission": perm_str,
                "args_model": args_model,
                "output_model": output_model,
            }
            logger.debug(f"Registered tool '{name}' with permission '{perm_str}'.")
            return func

        return decorator

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve tool entry by name."""
        return self._tools.get(name)

    def has_tool(self, name: str) -> bool:
        """Check if tool name is registered."""
        return name in self._tools

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools."""
        return list(self._tools.values())

    def get_tool_names(self) -> List[str]:
        """Return names of all registered tools."""
        return list(self._tools.keys())

    def to_gemini_declarations(self, tool_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Export tool declarations for Gemini Function Calling.
        If tool_names is provided, exports only those tools.
        """
        declarations = []
        target_names = tool_names if tool_names is not None else self.get_tool_names()

        for name in target_names:
            tool = self._tools.get(name)
            if not tool:
                continue

            decl: Dict[str, Any] = {
                "name": tool["name"],
                "description": tool["description"],
            }
            if tool["args_model"]:
                schema = tool["args_model"].model_json_schema()
                # Clean up schema for Gemini OpenAPI subset
                schema.pop("title", None)
                decl["parameters"] = schema
            else:
                decl["parameters"] = {
                    "type": "object",
                    "properties": {},
                }
            declarations.append(decl)

        return declarations


# Global default tool registry
registry = ToolRegistry()
register_tool = registry.register
