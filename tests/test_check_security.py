import asyncio
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.api.check import check
from app.schemas import CheckRequest


SESSION_STUDENT = {
    "id": 7,
    "task_class_id": "10class",
}
CANONICAL_TASK = {
    "class_id": "10class",
    "chapter": "2",
    "topic": "2",
    "number": "2",
    "problem": "Canonical physics problem",
    "answer": "Canonical answer",
    "image": None,
}


def make_request(**overrides):
    values = {
        "problem": "Сколько будет 2 + 2?",
        "solution": "4",
        "history": [],
        "hint_level": 0,
        "student_id": 7,
        "class_id": "10class",
        "chapter": "2",
        "topic": "2",
        "number": "2",
    }
    values.update(overrides)
    return CheckRequest(**values)


class CheckSecurityTests(unittest.TestCase):
    def run_check(self, request, authorization="Bearer valid-token"):
        return asyncio.run(check(request, authorization))

    def test_requires_valid_student_session(self):
        with patch(
            "app.api.check.find_student_by_session_token",
            return_value=None,
        ):
            with self.assertRaises(HTTPException) as context:
                self.run_check(make_request(), authorization=None)

        self.assertEqual(context.exception.status_code, 401)

    def test_rejects_student_id_mismatch(self):
        with patch(
            "app.api.check.find_student_by_session_token",
            return_value=SESSION_STUDENT,
        ):
            with self.assertRaises(HTTPException) as context:
                self.run_check(make_request(student_id=8))

        self.assertEqual(context.exception.status_code, 403)

    def test_requires_complete_task_identifiers(self):
        with patch(
            "app.api.check.find_student_by_session_token",
            return_value=SESSION_STUDENT,
        ):
            with self.assertRaises(HTTPException) as context:
                self.run_check(make_request(number=None))

        self.assertEqual(context.exception.status_code, 400)

    def test_rejects_task_base_from_another_class(self):
        with (
            patch(
                "app.api.check.find_student_by_session_token",
                return_value=SESSION_STUDENT,
            ),
            patch("app.api.check.find_task") as find_task,
        ):
            with self.assertRaises(HTTPException) as context:
                self.run_check(make_request(class_id="11class"))

        self.assertEqual(context.exception.status_code, 403)
        find_task.assert_not_called()

    def test_rejects_unknown_task_before_llm_call(self):
        with (
            patch(
                "app.api.check.find_student_by_session_token",
                return_value=SESSION_STUDENT,
            ),
            patch("app.api.check.find_task", return_value=None),
            patch("app.api.check.ask_llm") as ask_llm,
        ):
            with self.assertRaises(HTTPException) as context:
                self.run_check(make_request())

        self.assertEqual(context.exception.status_code, 404)
        ask_llm.assert_not_called()

    def test_uses_canonical_task_and_session_student(self):
        llm_result = {
            "status": "correct",
            "is_passed": True,
            "message": "Correct",
        }
        attempt = {"id": 99}

        with (
            patch(
                "app.api.check.find_student_by_session_token",
                return_value=SESSION_STUDENT,
            ),
            patch("app.api.check.find_task", return_value=CANONICAL_TASK),
            patch("app.api.check.ask_llm", return_value=llm_result) as ask_llm,
            patch(
                "app.api.check.record_task_attempt",
                return_value=attempt,
            ) as record_attempt,
            patch(
                "app.api.check.get_task_progress",
                return_value={"is_passed": 1},
            ),
        ):
            result = self.run_check(make_request())

        self.assertEqual(ask_llm.call_args.args[0], CANONICAL_TASK["problem"])
        self.assertEqual(
            ask_llm.call_args.args[6],
            CANONICAL_TASK["answer"],
        )
        self.assertEqual(record_attempt.call_args.kwargs["student_id"], 7)
        self.assertTrue(result["attempt_saved"])
        self.assertEqual(result["attempt_id"], 99)


if __name__ == "__main__":
    unittest.main()
