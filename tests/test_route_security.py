import unittest
from unittest.mock import patch
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.task_store import TASKS
from app.services.task_store import build_task_response


class RouteSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_source_task_json_is_not_public(self):
        response = self.client.get("/tasks/10class.json")

        self.assertEqual(response.status_code, 404)

    def test_safe_task_api_does_not_expose_answers(self):
        response = self.client.get("/tasks")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json())
        self.assertNotIn("answer", response.json()[0])

    def test_task_images_remain_public(self):
        image_url = next(
            response["image_url"]
            for response in (build_task_response(task) for task in TASKS)
            if response.get("image_url")
        )

        response = self.client.get(image_url)

        self.assertEqual(response.status_code, 200)

    def test_student_list_requires_admin_session(self):
        response = self.client.get("/students")

        self.assertEqual(response.status_code, 401)

    def test_student_progress_requires_matching_session(self):
        response = self.client.get("/students/1/progress")

        self.assertEqual(response.status_code, 401)

    def test_teacher_email_header_cannot_replace_session(self):
        with patch(
            "app.api.students.find_user_by_session_token",
            return_value=None,
        ):
            response = self.client.get(
                "/teacher/students",
                headers={"X-User-Email": "teacher@example.com"},
            )

        self.assertEqual(response.status_code, 401)

    def test_chat_does_not_render_messages_as_html(self):
        chat_source = Path("static/js/chat.js").read_text(encoding="utf-8")

        self.assertNotIn("innerHTML = text", chat_source)
        self.assertIn("div.textContent", chat_source)
        self.assertIn("textDiv.textContent", chat_source)

    def test_expired_student_session_returns_to_login(self):
        students_source = Path("static/js/students.js").read_text(
            encoding="utf-8"
        )
        main_source = Path("static/js/main.js").read_text(encoding="utf-8")

        self.assertIn("response.status === 401", students_source)
        self.assertIn("handleExpiredStudentSession", students_source)
        self.assertIn("initStudentSession()", main_source)
        self.assertIn("Promise.all", main_source)


if __name__ == "__main__":
    unittest.main()
