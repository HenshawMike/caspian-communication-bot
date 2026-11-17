"""LLM client abstraction interface supporting OpenRouter, Hugging Face, Gemini, and Mock clients."""

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import requests

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


class OpenRouterClient(LLMClient):
    """Production OpenRouter client supporting Baidu ERNIE-5.5-Flash-Preview and other models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        api_url: Optional[str] = None,
    ):
        if api_key is not None:
            self.api_key = api_key if api_key else None
        else:
            self.api_key = settings.openrouter_api_key

        self.model = model or settings.openrouter_model
        self.api_url = api_url or settings.openrouter_api_url

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Call OpenRouter Chat Completions endpoint."""
        if not self.api_key:
            raise RuntimeError("OpenRouterClient requires a valid OPENROUTER_API_KEY.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/HenshawMike/caspian",
            "X-Title": "Project Caspian Research Agent",
        }

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=90,
            )

            if response.status_code != 200:
                err_text = response.text
                logger.error(
                    f"OpenRouter API returned status {response.status_code}: {redact_secrets(err_text)}"
                )
                raise RuntimeError(
                    f"OpenRouter API failed [{response.status_code}]: {err_text}"
                )

            data = response.json()
            choices = data.get("choices", [])
            if choices and "message" in choices[0]:
                return choices[0]["message"].get("content", "").strip()

            return ""
        except Exception as e:
            logger.error(f"OpenRouter API request failed: {redact_secrets(str(e))}")
            raise

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate structured JSON via OpenRouter."""
        json_instruction = (
            (system_instruction + "\n\n" if system_instruction else "")
            + "IMPORTANT: Respond ONLY with a valid JSON object. Do not include markdown code blocks, explanations, or conversational filler."
        )
        text = self.generate_text(
            prompt=prompt,
            system_instruction=json_instruction,
            temperature=0.1,
        )

        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            logger.error(f"Failed to decode JSON from OpenRouter response: {redact_secrets(text)}")
            raise ValueError(f"OpenRouter response could not be parsed as JSON: {text[:200]}")


class HuggingFaceClient(LLMClient):
    """Production Hugging Face Router client supporting streaming and JSON output."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        api_url: Optional[str] = None,
    ):
        if api_key is not None:
            self.api_key = api_key if api_key else None
        else:
            self.api_key = settings.hf_token

        self.model = model or settings.hf_model
        self.api_url = api_url or settings.hf_api_url

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Query Hugging Face Router endpoint with streaming chunk collection."""
        if not self.api_key:
            raise RuntimeError("HuggingFaceClient requires a valid HF_TOKEN.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "messages": messages,
            "model": self.model,
            "temperature": temperature,
            "stream": True,
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=90,
            )

            if response.status_code != 200:
                err_text = response.text
                logger.error(
                    f"Hugging Face API call returned status {response.status_code}: {redact_secrets(err_text)}"
                )
                raise RuntimeError(
                    f"Hugging Face API failed [{response.status_code}]: {err_text}"
                )

            collected = []
            for line in response.iter_lines():
                if not line.startswith(b"data:"):
                    continue
                if line.strip() == b"data: [DONE]":
                    break
                decoded = line.decode("utf-8").lstrip("data:").rstrip("\n").strip()
                if not decoded:
                    continue
                try:
                    chunk = json.loads(decoded)
                    choices = chunk.get("choices", [])
                    if choices and "delta" in choices[0]:
                        delta = choices[0]["delta"]
                        if "content" in delta and delta["content"]:
                            collected.append(delta["content"])
                except Exception:
                    continue

            return "".join(collected).strip()
        except Exception as e:
            logger.error(f"Hugging Face API request failed: {redact_secrets(str(e))}")
            raise

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate structured JSON via Hugging Face Router."""
        json_instruction = (
            (system_instruction + "\n\n" if system_instruction else "")
            + "IMPORTANT: Respond ONLY with a valid JSON object. Do not include markdown code blocks, explanations, or conversational filler."
        )
        text = self.generate_text(
            prompt=prompt,
            system_instruction=json_instruction,
            temperature=0.1,
        )

        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            logger.error(f"Failed to decode JSON from Hugging Face response: {redact_secrets(text)}")
            raise ValueError(f"Hugging Face response could not be parsed as JSON: {text[:200]}")


class GeminiClient(LLMClient):
    """Fallback Gemini client using Google GenAI SDK."""

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
    """Factory providing OpenRouterClient (primary), HuggingFaceClient, GeminiClient, or MockLLMClient."""
    if settings.openrouter_api_key:
        return OpenRouterClient()
    if settings.hf_token:
        return HuggingFaceClient()
    if settings.gemini_api_key:
        return GeminiClient()
    if use_mock_if_no_key:
        logger.info("No LLM API key configured. Using MockLLMClient.")
        return MockLLMClient()
    return OpenRouterClient()
