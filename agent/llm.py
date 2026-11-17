"""Gemini LLM integration and mock client interface."""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from agent.config import settings
from agent.logging_config import logger, redact_secrets


class LLMClient(ABC):
    """Abstract interface for LLM operations."""

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Generate a simple text response."""
        pass

    @abstractmethod
    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate structured JSON conforming to expected output."""
        pass


class MockLLMClient(LLMClient):
    """Deterministic mock client for offline testing."""

    def __init__(self, default_response: Optional[str] = None):
        self.default_response = default_response or "Mock LLM response"
        self._responses_queue: List[str] = []
        self._last_prompt: Optional[str] = None
        self._last_system: Optional[str] = None

    def queue_response(self, response: str | Dict[str, Any]) -> None:
        """Queue a specific response for subsequent generate calls."""
        if isinstance(response, dict):
            self._responses_queue.append(json.dumps(response))
        else:
            self._responses_queue.append(str(response))

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        self._last_prompt = prompt
        self._last_system = system_instruction
        if self._responses_queue:
            return self._responses_queue.pop(0)
        return self.default_response

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        text = self.generate_text(prompt, system_instruction)
        try:
            # Strip markdown json blocks if present
            cleaned = text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
        except json.JSONDecodeError:
            logger.warning(f"Mock response was not valid JSON: {text}")
            return {"raw_response": text}


class GeminiClient(LLMClient):
    """Production Gemini client using Google GenAI SDK."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        self._client = None
        
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Google GenAI client: {e}")

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        if not self._client:
            raise RuntimeError("GeminiClient requires a valid GEMINI_API_KEY.")

        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                temperature=temperature,
                system_instruction=system_instruction if system_instruction else None,
            )
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"Gemini API call failed: {redact_secrets(str(e))}")
            raise

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self._client:
            raise RuntimeError("GeminiClient requires a valid GEMINI_API_KEY.")

        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                temperature=0.1,
                system_instruction=system_instruction if system_instruction else None,
                response_mime_type="application/json",
            )
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Gemini JSON generation failed: {redact_secrets(str(e))}")
            raise


def get_llm_client(use_mock_if_no_key: bool = True) -> LLMClient:
    """Factory providing GeminiClient if key is configured, or MockLLMClient for testing."""
    if settings.gemini_api_key:
        return GeminiClient()
    if use_mock_if_no_key:
        logger.info("GEMINI_API_KEY not set. Using MockLLMClient.")
        return MockLLMClient()
    return GeminiClient()
