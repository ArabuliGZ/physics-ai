import os
import re
import json


SOURCE_FOLDER = "tasks_source"

OUTPUT_FILE = "tasks.json"


all_tasks = []


def extract_image(task_text):

    match = re.search(
        r'\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}',
        task_text
    )

    if match:
        return match.group(1)

    return None


def clean_text(text):

    text = text.strip()

    text = text.replace("\n", " ")

    text = re.sub(r"\s+", " ", text)

    return text


def extract_braces(text, start_index):

    while text[start_index] != "{":
        start_index += 1

    level = 0

    result = ""

    i = start_index

    while i < len(text):

        char = text[i]

        if char == "{":

            level += 1

            if level > 1:
                result += char

        elif char == "}":

            level -= 1

            if level == 0:
                return result, i

            result += char

        else:
            result += char

        i += 1

    return result, i


def extract_brackets(text, start_index):

    while text[start_index] != "[":
        start_index += 1

    level = 0

    result = ""

    i = start_index

    while i < len(text):

        char = text[i]

        if char == "[":

            level += 1

            if level > 1:
                result += char

        elif char == "]":

            level -= 1

            if level == 0:
                return result, i

            result += char

        else:
            result += char

        i += 1

    return result, i


def parse_tasks(tex_text):

    tasks = []

    pos = 0

    while True:

        z_pos = tex_text.find(r"\z", pos)

        if z_pos == -1:
            break

        next_char = tex_text[z_pos + 2]

        image_block = ""

        # =========================
        # ВАРИАНТ С КАРТИНКОЙ
        # =========================

        if next_char == "[":

            image_block, end0 = extract_brackets(
                tex_text,
                z_pos + 2
            )

            percent_pos = tex_text.find("%", end0)

            problem, end1 = extract_braces(
                tex_text,
                percent_pos
            )

        # =========================
        # ВАРИАНТ БЕЗ КАРТИНКИ
        # =========================

        elif next_char == "{":

            problem, end1 = extract_braces(
                tex_text,
                z_pos + 2
            )

        else:

            pos = z_pos + 2

            continue

        next_percent = tex_text.find("%", end1)

        answer, end2 = extract_braces(
            tex_text,
            next_percent
        )

        tasks.append((
            image_block,
            problem,
            answer
        ))

        pos = end2

    return tasks


for filename in os.listdir(SOURCE_FOLDER):

    if not filename.endswith(".tex"):
        continue

    filepath = os.path.join(
        SOURCE_FOLDER,
        filename
    )

    with open(filepath, "r", encoding="utf-8") as f:

        tex_text = f.read()

    filename_without_ext = os.path.splitext(filename)[0]

    tasks = parse_tasks(tex_text)

    for index, task in enumerate(tasks, start=1):

        image_block = task[0]

        problem = clean_text(task[1])

        answer = clean_text(task[2])

        image = extract_image(image_block)

        clean_name = filename_without_ext.replace("Ch", "")

        task_id = f"{clean_name}.{index}"

        task_data = {

            "group": "8class",

            "id": task_id,

            "image": image,

            "problem": problem,

            "answer": answer,

            "hint": ""
        }

        all_tasks.append(task_data)


with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

    json.dump(
        all_tasks,
        f,
        ensure_ascii=False,
        indent=2
    )


print(f"Готово. Сохранено задач: {len(all_tasks)}")