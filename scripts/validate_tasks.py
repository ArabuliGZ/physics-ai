"""Validate the task database.

The script is intentionally read-only: it never rewrites JSON files or media.
Run from the project root:

    python scripts/validate_tasks.py
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
TASKS_DIR = ROOT_DIR / "tasks"
IMAGES_DIR = TASKS_DIR / "images"

TASK_FILES = (
    TASKS_DIR / "7class.json",
    TASKS_DIR / "8class.json",
    TASKS_DIR / "9class.json",
)

REQUIRED_TASK_KEYS = {
    "class_id",
    "chapter",
    "topic",
    "number",
    "image",
    "problem",
    "answer",
}

OLD_TASK_KEYS = {
    "group",
    "id",
    "hint",
}

MEDIA_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".pdf",
)


def main() -> int:
    errors: list[str] = []
    seen_task_ids: set[tuple[str, str, str, str]] = set()
    total_tasks = 0
    total_media = 0

    for task_file in TASK_FILES:
        class_id_from_file = task_file.stem
        tasks = load_json_list(task_file, errors)

        if tasks is None:
            continue

        print(f"{task_file.relative_to(ROOT_DIR)}: {len(tasks)} tasks")
        total_tasks += len(tasks)

        for index, task in enumerate(tasks, start=1):
            context = f"{task_file.relative_to(ROOT_DIR)} item #{index}"

            if not isinstance(task, dict):
                errors.append(f"{context}: task must be an object")
                continue

            validate_schema(task, context, errors)

            if task.get("class_id") != class_id_from_file:
                errors.append(
                    f"{context}: class_id must be {class_id_from_file!r}, "
                    f"got {task.get('class_id')!r}"
                )

            task_identity = (
                str(task.get("class_id")),
                str(task.get("chapter")),
                str(task.get("topic")),
                str(task.get("number")),
            )
            context = (
                f"{task_file.relative_to(ROOT_DIR)} "
                f"{'.'.join(task_identity)} item #{index}"
            )

            if task_identity in seen_task_ids:
                errors.append(
                    f"{context}: duplicate task identity "
                    f"{'.'.join(task_identity)}"
                )
            else:
                seen_task_ids.add(task_identity)

            validate_number_field(task, "chapter", context, errors)
            validate_number_field(task, "topic", context, errors)
            validate_number_field(task, "number", context, errors)
            validate_non_empty_text(task, "problem", context, errors)
            validate_non_empty_text(task, "answer", context, errors)

            image_name = task.get("image")

            if image_name:
                total_media += 1
                validate_media_file(
                    str(task.get("class_id")),
                    str(image_name),
                    context,
                    errors
                )

    print(f"total tasks: {total_tasks}")
    print(f"tasks with media: {total_media}")

    if errors:
        print()
        print("Validation failed:")

        for error in errors:
            print(f"- {error}")

        return 1

    print("schema: ok")
    print("duplicates: ok")
    print("media: ok")
    return 0


def load_json_list(path: Path, errors: list[str]) -> list[dict] | None:
    if not path.exists():
        errors.append(f"{path.relative_to(ROOT_DIR)}: file does not exist")
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(
            f"{path.relative_to(ROOT_DIR)}: invalid JSON at "
            f"line {exc.lineno}, column {exc.colno}: {exc.msg}"
        )
        return None

    if not isinstance(data, list):
        errors.append(f"{path.relative_to(ROOT_DIR)}: root must be a list")
        return None

    return data


def validate_schema(task: dict, context: str, errors: list[str]) -> None:
    keys = set(task)
    missing_keys = REQUIRED_TASK_KEYS - keys
    extra_keys = keys - REQUIRED_TASK_KEYS
    old_keys = keys & OLD_TASK_KEYS

    if missing_keys:
        errors.append(
            f"{context}: missing keys {sorted(missing_keys)}"
        )

    if extra_keys:
        errors.append(
            f"{context}: unexpected keys {sorted(extra_keys)}"
        )

    if old_keys:
        errors.append(
            f"{context}: old keys are not allowed {sorted(old_keys)}"
        )


def validate_number_field(
    task: dict,
    field_name: str,
    context: str,
    errors: list[str]
) -> None:
    value = task.get(field_name)

    if not isinstance(value, str) or not value.isdigit():
        errors.append(
            f"{context}: {field_name} must be a numeric string, "
            f"got {value!r}"
        )


def validate_non_empty_text(
    task: dict,
    field_name: str,
    context: str,
    errors: list[str]
) -> None:
    value = task.get(field_name)

    if not isinstance(value, str) or not value.strip():
        errors.append(
            f"{context}: {field_name} must be a non-empty string"
        )


def validate_media_file(
    class_id: str,
    image_name: str,
    context: str,
    errors: list[str]
) -> None:
    media_dir = IMAGES_DIR / class_id
    suffix = Path(image_name).suffix.lower()

    if suffix in MEDIA_EXTENSIONS:
        candidates = [media_dir / image_name]
    else:
        candidates = [
            media_dir / f"{image_name}{extension}"
            for extension in MEDIA_EXTENSIONS
        ]

    if any(candidate.exists() for candidate in candidates):
        return

    lower_candidate_names = {
        candidate.name.lower()
        for candidate in candidates
    }

    if media_dir.exists():
        for child in media_dir.iterdir():
            if child.name.lower() in lower_candidate_names:
                return

    expected = ", ".join(
        str(candidate.relative_to(ROOT_DIR))
        for candidate in candidates
    )

    errors.append(
        f"{context}: media file not found for image={image_name!r}; "
        f"tried {expected}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
