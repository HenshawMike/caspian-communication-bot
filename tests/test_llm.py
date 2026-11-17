"""Tests for LLM integration including OpenRouter, Hugging Face, and Mock clients."""

from unittest.mock import MagicMock, patch
import pytest
from agent.llm import (
    MockLLMClient,
    OpenRouterClient,
    HuggingFaceClient,
    GeminiClient,
    get_llm_client,
)
from agent.config import settings


def test_mock_llm_client_text():
    client = MockLLMClient(default_response="Default response")
    assert client.generate_text("Hello") == "Default response"

    client.queue_response("Queued answer")
    assert client.generate_text("Another prompt") == "Queued answer"
    assert client.generate_text("Prompt 3") == "Default response"


def test_mock_llm_client_json():
    client = MockLLMClient()
    client.queue_response({"key": "value", "count": 42})
    data = client.generate_json("Generate json")
    assert data == {"key": "value", "count": 42}


def test_mock_llm_client_json_codeblock():
    client = MockLLMClient()
    client.queue_response("```json\n{\"item\": \"apple\"}\n```")
    data = client.generate_json("Generate item")
    assert data == {"item": "apple"}


def test_get_llm_client_fallback_to_mock(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", None)
    monkeypatch.setattr(settings, "hf_token", None)
    monkeypatch.setattr(settings, "gemini_api_key", None)
    client = get_llm_client(use_mock_if_no_key=True)
    assert isinstance(client, MockLLMClient)


def test_get_llm_client_selects_openrouter(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "sk-or-v1-mock123")
    client = get_llm_client()
    assert isinstance(client, OpenRouterClient)
    assert client.api_key == "sk-or-v1-mock123"


def test_get_llm_client_selects_hf(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", None)
    monkeypatch.setattr(settings, "hf_token", "hf_test_token_12345")
    client = get_llm_client()
    assert isinstance(client, HuggingFaceClient)
    assert client.api_key == "hf_test_token_12345"


def test_openrouter_client_missing_key(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", None)
    client = OpenRouterClient(api_key=None)
    with pytest.raises(RuntimeError, match="requires a valid OPENROUTER_API_KEY"):
        client.generate_text("Hello")


def test_openrouter_client_generate_text_success():
    client = OpenRouterClient(
        api_key="sk-or-test-key",
        model="baidu/ernie-5.5-flash-preview",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "gen-12345",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Paris is the capital of France.",
                }
            }
        ],
    }

    with patch("requests.post", return_value=mock_resp) as mock_post:
        res = client.generate_text("What is the capital of France?", system_instruction="You are an expert.")
        assert res == "Paris is the capital of France."
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer sk-or-test-key"
        assert call_kwargs["json"]["model"] == "baidu/ernie-5.5-flash-preview"
        assert len(call_kwargs["json"]["messages"]) == 2


def test_openrouter_client_generate_json_success():
    client = OpenRouterClient(api_key="sk-or-test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "```json\n{\"status\": \"OK\", \"score\": 0.98}\n```",
                }
            }
        ]
    }

    with patch("requests.post", return_value=mock_resp):
        data = client.generate_json("Return status in JSON")
        assert data == {"status": "OK", "score": 0.98}


def test_openrouter_client_api_error():
    client = OpenRouterClient(api_key="sk-or-test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = '{"error": {"code": 401, "message": "User key is invalid"}}'

    with patch("requests.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="OpenRouter API failed \\[401\\]"):
            client.generate_text("Ping")


def test_huggingface_client_missing_key(monkeypatch):
    monkeypatch.setattr(settings, "hf_token", None)
    client = HuggingFaceClient(api_key=None)
    with pytest.raises(RuntimeError, match="requires a valid HF_TOKEN"):
        client.generate_text("Hello")


def test_huggingface_client_streaming_success():
    client = HuggingFaceClient(api_key="hf_mock_token", model="Qwen/Qwen3-4B:featherless-ai")

    stream_lines = [
        b'data: {"choices": [{"delta": {"content": "Paris"}}]}',
        b'data: {"choices": [{"delta": {"content": " is the capital."}}]}',
        b'data: [DONE]',
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_lines.return_value = stream_lines

    with patch("requests.post", return_value=mock_resp) as mock_post:
        res = client.generate_text("What is the capital of France?", system_instruction="You are a helpful assistant.")
        assert res == "Paris is the capital."
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer hf_mock_token"
        assert call_kwargs["json"]["model"] == "Qwen/Qwen3-4B:featherless-ai"
        assert len(call_kwargs["json"]["messages"]) == 2


def test_huggingface_client_json_generation():
    client = HuggingFaceClient(api_key="hf_mock_token")

    stream_lines = [
        b'data: {"choices": [{"delta": {"content": "```json\\n{\\"city\\": \\"Paris\\"}\\n```"}}]}',
        b'data: [DONE]',
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_lines.return_value = stream_lines

    with patch("requests.post", return_value=mock_resp):
        data = client.generate_json("Return city in json")
        assert data == {"city": "Paris"}
