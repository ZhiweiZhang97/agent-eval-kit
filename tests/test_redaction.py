from agent_eval_kit.redaction import redact_text, redact_value


def test_redact_common_secret_shapes():
    text = "token=sk-abcdefghijklmnop Bearer abcdefghijklmnop"
    redacted = redact_text(text)
    assert "sk-abcdefghijklmnop" not in redacted
    assert "Bearer abcdefghijklmnop" not in redacted
    assert "[REDACTED_TOKEN]" in redacted


def test_redact_nested_values():
    value = {
        "response": "api_key=abcdefghijklmnop",
        "tool": {"arguments": ["secret=abcdefghijklmnop"]},
    }
    redacted = redact_value(value)
    assert "abcdefghijklmnop" not in str(redacted)
