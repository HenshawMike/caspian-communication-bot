"""Tool executor responsible for validation, permission checks, execution, and auditing."""

import time
from typing import Any, Dict, Optional
from pydantic import ValidationError

from agent.schemas import ToolResultEnvelope, ToolError, ExecutionMetadata
from agent.permissions import PermissionContext, PermissionDeniedError
from agent.tool_registry import ToolRegistry, registry as default_registry
from agent.logging_config import logger
from database.models import record_audit_log


class ToolExecutor:
    """Executes tools safely with permission checks and validation."""

    def __init__(self, tool_registry: Optional[ToolRegistry] = None):
        self.registry = tool_registry or default_registry

    def execute(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        context: Optional[PermissionContext] = None,
    ) -> ToolResultEnvelope:
        """
        Execute a registered tool within a permission context.
        Returns a standardized ToolResultEnvelope.
        """
        start_time = time.perf_counter()
        raw_args = arguments or {}

        # 1. Check if tool exists
        tool = self.registry.get_tool(tool_name)
        if not tool:
            duration_ms = (time.perf_counter() - start_time) * 1000
            err = ToolError(
                code="TOOL_NOT_FOUND",
                message=f"Tool '{tool_name}' is not registered in the system.",
            )
            self._log_and_audit(
                tool_name=tool_name,
                success=False,
                duration_ms=duration_ms,
                context=context,
                inputs=raw_args,
                error=err,
            )
            return ToolResultEnvelope(
                success=False,
                data=None,
                error=err,
                execution_metadata=ExecutionMetadata(
                    tool_name=tool_name,
                    duration_ms=duration_ms,
                    executed_by=context.user_id if context else None,
                ),
            )

        # 2. Check required permission
        required_perm = tool["permission"]
        if context:
            try:
                context.verify_permission(required_perm)
            except PermissionDeniedError as pe:
                duration_ms = (time.perf_counter() - start_time) * 1000
                err = ToolError(
                    code="PERMISSION_DENIED",
                    message=str(pe),
                    details={"required_permission": required_perm},
                )
                self._log_and_audit(
                    tool_name=tool_name,
                    success=False,
                    duration_ms=duration_ms,
                    context=context,
                    inputs=raw_args,
                    error=err,
                )
                return ToolResultEnvelope(
                    success=False,
                    data=None,
                    error=err,
                    execution_metadata=ExecutionMetadata(
                        tool_name=tool_name,
                        duration_ms=duration_ms,
                        executed_by=context.user_id,
                    ),
                )

        # 3. Validate arguments against schema if defined
        validated_args = raw_args
        if tool["args_model"]:
            try:
                validated_model = tool["args_model"](**raw_args)
                validated_args = validated_model.model_dump()
            except ValidationError as ve:
                duration_ms = (time.perf_counter() - start_time) * 1000
                err = ToolError(
                    code="INVALID_ARGUMENTS",
                    message="Validation error in tool arguments.",
                    details={"validation_errors": ve.errors()},
                )
                self._log_and_audit(
                    tool_name=tool_name,
                    success=False,
                    duration_ms=duration_ms,
                    context=context,
                    inputs=raw_args,
                    error=err,
                )
                return ToolResultEnvelope(
                    success=False,
                    data=None,
                    error=err,
                    execution_metadata=ExecutionMetadata(
                        tool_name=tool_name,
                        duration_ms=duration_ms,
                        executed_by=context.user_id if context else None,
                    ),
                )

        # 4. Execute tool function
        try:
            func = tool["function"]
            result = func(**validated_args)

            # Optional output validation
            if tool["output_model"] and isinstance(result, dict):
                try:
                    result = tool["output_model"](**result).model_dump()
                except ValidationError as ve:
                    logger.warning(f"Output of tool '{tool_name}' did not match output schema: {ve}")

            duration_ms = (time.perf_counter() - start_time) * 1000
            envelope = ToolResultEnvelope(
                success=True,
                data=result,
                error=None,
                execution_metadata=ExecutionMetadata(
                    tool_name=tool_name,
                    duration_ms=duration_ms,
                    executed_by=context.user_id if context else None,
                ),
            )
            self._log_and_audit(
                tool_name=tool_name,
                success=True,
                duration_ms=duration_ms,
                context=context,
                inputs=raw_args,
                output=result,
            )
            return envelope

        except Exception as ex:
            duration_ms = (time.perf_counter() - start_time) * 1000
            err = ToolError(
                code="TOOL_EXECUTION_ERROR",
                message=f"Error executing tool '{tool_name}': {str(ex)}",
            )
            self._log_and_audit(
                tool_name=tool_name,
                success=False,
                duration_ms=duration_ms,
                context=context,
                inputs=raw_args,
                error=err,
            )
            return ToolResultEnvelope(
                success=False,
                data=None,
                error=err,
                execution_metadata=ExecutionMetadata(
                    tool_name=tool_name,
                    duration_ms=duration_ms,
                    executed_by=context.user_id if context else None,
                ),
            )

    def _log_and_audit(
        self,
        tool_name: str,
        success: bool,
        duration_ms: float,
        context: Optional[PermissionContext],
        inputs: Optional[Dict[str, Any]],
        output: Optional[Any] = None,
        error: Optional[ToolError] = None,
    ) -> None:
        """Write execution record to SQLite audit log and application logger."""
        caller = context.user_id if context else None
        active_skill = context.active_skill if context else None
        err_code = error.code if error else None
        err_msg = error.message if error else None

        if success:
            logger.info(f"Tool '{tool_name}' executed successfully in {duration_ms:.2f}ms.")
        else:
            logger.error(f"Tool '{tool_name}' failed: [{err_code}] {err_msg}")

        try:
            record_audit_log(
                tool_name=tool_name,
                success=success,
                duration_ms=duration_ms,
                caller_id=caller,
                active_skill=active_skill,
                input_params=inputs,
                output_data=output,
                error_code=err_code,
                error_message=err_msg,
            )
        except Exception as db_err:
            logger.error(f"Failed to record audit log for '{tool_name}': {db_err}")


# Global default tool executor
executor = ToolExecutor()
