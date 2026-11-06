from unittest.mock import patch

import llm


def test_letovo_uses_provider_specific_reasoning_settings():
    with (
        patch.object(llm, "LETOVO_LLM_API_KEY", "test-key"),
        patch.object(
            llm,
            "send_openai_compatible_request",
            return_value={"status": "correct", "is_passed": True},
        ) as send_request,
    ):
        llm.ask_letovo_llm(
            "problem",
            "solution",
            [],
            0,
            reference_answer="answer",
        )

    payload = send_request.call_args.args[1]
    assert payload["max_tokens"] == 2500
    assert payload["reasoning_effort"] == "low"
    assert payload["thinking"] == {"type": "enabled"}
    assert "temperature" not in payload
