from unittest.mock import patch

import llm
from app.services.llm_settings import LLM_PROVIDER_OPTIONS


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


def test_valid_incorrect_result_does_not_trigger_fallback():
    incorrect = {
        "status": "error",
        "is_passed": False,
        "message": "Попробуй ещё раз.",
    }

    with (
        patch.object(llm, "get_active_llm_provider", return_value="timeweb"),
        patch.object(llm, "ask_timeweb", return_value=incorrect),
        patch.object(llm, "ask_qwencloud") as ask_qwen,
        patch.object(llm, "ask_letovo_llm") as ask_letovo,
    ):
        result = llm.ask_llm("problem", "solution", [], 0)

    assert result == incorrect
    ask_qwen.assert_not_called()
    ask_letovo.assert_not_called()


def test_technical_errors_fallback_to_qwen_then_letovo():
    qwen_error = llm.technical_llm_error("qwen unavailable")
    letovo_result = {
        "status": "correct",
        "is_passed": True,
        "message": "Верно.",
    }

    with (
        patch.object(llm, "get_active_llm_provider", return_value="timeweb"),
        patch.object(
            llm,
            "ask_timeweb",
            return_value=llm.technical_llm_error("timeweb unavailable"),
        ) as ask_timeweb,
        patch.object(llm, "ask_qwencloud", return_value=qwen_error) as ask_qwen,
        patch.object(
            llm,
            "ask_letovo_llm",
            return_value=letovo_result,
        ) as ask_letovo,
    ):
        result = llm.ask_llm("problem", "solution", [], 0)

    assert result == letovo_result
    ask_timeweb.assert_called_once()
    ask_qwen.assert_called_once()
    ask_letovo.assert_called_once()
    assert "_retryable" not in result


def test_letovo_primary_retries_after_qwen_fallback():
    technical_error = llm.technical_llm_error("provider unavailable")
    success = {
        "status": "correct",
        "is_passed": True,
        "message": "Верно.",
    }

    with (
        patch.object(llm, "get_active_llm_provider", return_value="letovo"),
        patch.object(llm, "ask_qwencloud", return_value=technical_error),
        patch.object(
            llm,
            "ask_letovo_llm",
            side_effect=[technical_error, success],
        ) as ask_letovo,
    ):
        result = llm.ask_llm("problem", "solution", [], 0)

    assert result == success
    assert ask_letovo.call_count == 2


def test_empty_model_response_is_retryable():
    result = llm.parse_json_response("")

    assert result["_retryable"] is True
    assert result["is_passed"] is False


def test_removed_provider_is_not_available_to_admin():
    providers = [option["provider"] for option in LLM_PROVIDER_OPTIONS]

    assert providers == ["letovo", "qwencloud", "timeweb"]
