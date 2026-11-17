"""Tests for LLM integration."""

from agent.llm import MockLLMClient, get_llm_client


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


def test_get_llm_client_fallback_to_mock():
    # When no API key is provided, should return MockLLMClient
    client = get_llm_client(use_mock_if_no_key=True)
    assert isinstance(client, MockLLMClient)
