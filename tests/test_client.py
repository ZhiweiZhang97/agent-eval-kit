from agent_eval_kit.client import normalize_tool_calls


def test_normalize_modern_tool_calls():
    message = {
        "tool_calls": [
            {
                "id": "call-1",
                "type": "function",
                "function": {
                    "name": "search",
                    "arguments": '{"query": "agent eval"}',
                },
            }
        ]
    }
    calls = normalize_tool_calls(message)
    assert len(calls) == 1
    assert calls[0].name == "search"
    assert calls[0].arguments == {"query": "agent eval"}
    assert calls[0].id == "call-1"


def test_normalize_legacy_function_call():
    calls = normalize_tool_calls(
        {
            "function_call": {
                "name": "lookup",
                "arguments": '{"id": 3}',
            }
        }
    )
    assert calls[0].name == "lookup"
    assert calls[0].arguments == {"id": 3}
