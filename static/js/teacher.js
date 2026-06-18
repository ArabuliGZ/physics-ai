const TEACHER_STATE = {
    students: [],
    tasks: [],
    groupsById: {},
};


document.addEventListener("DOMContentLoaded", () => {
    loadTeacherDashboard();
});


async function loadTeacherDashboard() {
    const table = document.getElementById("teacher_journal_table");
    const summary = document.getElementById("teacher_journal_summary");

    table.innerHTML = "<div class=\"progress-empty\">Загружаю...</div>";
    summary.textContent = "";

    try {
        const [studentsResponse, tasksResponse, groupsResponse] = await Promise.all([
            fetch("/teacher/students"),
            fetch("/tasks"),
            fetch("/groups"),
        ]);

        if (!studentsResponse.ok || !tasksResponse.ok || !groupsResponse.ok) {
            throw new Error("teacher dashboard request failed");
        }

        const groups = await groupsResponse.json();

        TEACHER_STATE.students = await studentsResponse.json();
        TEACHER_STATE.tasks = await tasksResponse.json();
        TEACHER_STATE.groupsById = Object.fromEntries(
            groups.map(group => [group.id, group.name])
        );

        fillTeacherFilters();
        await renderTeacherJournal();
    } catch (error) {
        console.error("Teacher dashboard failed:", error);
        table.innerHTML = "<div class=\"progress-empty\">Не получилось загрузить журнал.</div>";
    }
}


function fillTeacherFilters() {
    fillSelect(
        document.getElementById("teacher_school_select"),
        uniqueValues(TEACHER_STATE.students, "school")
    );

    fillTeacherStudentClasses();
    fillTeacherTaskBases();
}


function handleTeacherSchoolChange() {
    fillTeacherStudentClasses();
    fillTeacherTaskBases();
    renderTeacherJournal();
}


function handleTeacherClassChange() {
    fillTeacherTaskBases();
    renderTeacherJournal();
}


function fillTeacherStudentClasses() {
    const school = document.getElementById("teacher_school_select").value;
    const classes = TEACHER_STATE.students
        .filter(student => student.school === school)
        .map(student => ({
            grade: student.grade,
            class_group: student.class_group || "",
            title: student.class_name,
            key: `${student.grade}|${student.class_group || ""}`,
        }))
        .filter((item, index, items) => (
            items.findIndex(candidate => candidate.key === item.key) === index
        ))
        .sort((left, right) => (
            compareClassNames(left.grade, right.grade) ||
            String(left.class_group).localeCompare(String(right.class_group), "ru")
        ));

    const select = document.getElementById("teacher_student_class_select");

    select.innerHTML = classes.map(item => `
        <option value="${escapeHtml(item.key)}">${escapeHtml(item.title)}</option>
    `).join("");
}


function fillTeacherTaskBases() {
    const classKey = document.getElementById("teacher_student_class_select").value;
    const [grade] = classKey.split("|");
    const allowedClassId = `${grade}class`;
    const bases = [
        ...new Set(
            TEACHER_STATE.tasks
                .map(task => task.class_id)
                .filter(classId => classId === allowedClassId)
        )
    ].sort(compareClassNames);

    const select = document.getElementById("teacher_task_base_select");

    select.innerHTML = bases.map(classId => `
        <option value="${escapeHtml(classId)}">
            ${escapeHtml(TEACHER_STATE.groupsById[classId] || classId)}
        </option>
    `).join("");
}


async function renderTeacherJournal() {
    const school = document.getElementById("teacher_school_select").value;
    const classKey = document.getElementById("teacher_student_class_select").value;
    const classId = document.getElementById("teacher_task_base_select").value;
    const table = document.getElementById("teacher_journal_table");
    const summary = document.getElementById("teacher_journal_summary");

    if (classKey && !classId) {
        table.innerHTML = "<div class=\"progress-empty\">Для этой параллели пока нет базы заданий.</div>";
        summary.textContent = "";
        return;
    }

    if (!school || !classKey || !classId) {
        table.innerHTML = "<div class=\"progress-empty\">Выбери школу, класс и базу заданий.</div>";
        summary.textContent = "";
        return;
    }

    const [grade, classGroup] = classKey.split("|");

    table.innerHTML = "<div class=\"progress-empty\">Загружаю...</div>";
    summary.textContent = "";

    try {
        const params = new URLSearchParams({
            school,
            grade,
            class_group: classGroup,
            class_id: classId,
        });

        const response = await fetch(`/teacher/journal?${params.toString()}`);

        if (!response.ok) {
            throw new Error("teacher journal request failed");
        }

        const journal = await response.json();

        summary.textContent = [
            `${journal.students.length} учеников`,
            `${journal.tasks.length} задач`
        ].join(" · ");

        table.innerHTML = renderJournalTable(journal);
    } catch (error) {
        console.error("Teacher journal failed:", error);
        table.innerHTML = "<div class=\"progress-empty\">Не получилось загрузить журнал.</div>";
    }
}


function renderJournalTable(journal) {
    if (journal.students.length === 0) {
        return "<div class=\"progress-empty\">В выбранном классе пока нет учеников.</div>";
    }

    const progressByCell = new Map();
    const taskColumns = journal.tasks.map((task, index) => ({
        ...task,
        key: getTaskKey(task),
        block: `${task.chapter}.${task.topic}`,
        isMajorStart: index > 0 && (
            task.chapter !== journal.tasks[index - 1].chapter ||
            task.topic !== journal.tasks[index - 1].topic
        ),
    }));
    const taskBlocks = buildTaskBlocks(taskColumns);

    for (const progress of journal.progress) {
        progressByCell.set(
            `${progress.student_id}|${getTaskKey(progress)}`,
            progress
        );
    }

    return `
        <table class="teacher-journal">
            <thead>
                <tr>
                    <th class="teacher-student-column" rowspan="2">Ученик</th>
                    ${taskBlocks.map(block => `
                        <th
                            class="teacher-block-heading ${block.isMajorStart ? "teacher-major-start" : ""}"
                            colspan="${block.count}"
                        >
                            ${block.title}
                        </th>
                    `).join("")}
                    <th class="teacher-total-column" rowspan="2">Сдано</th>
                </tr>
                <tr>
                    ${taskColumns.map(task => `
                        <th class="teacher-task-heading ${task.isMajorStart ? "teacher-major-start" : ""}">
                            ${task.number}
                        </th>
                    `).join("")}
                </tr>
            </thead>
            <tbody>
                ${journal.students.map(student => {
                    const passedCount = taskColumns.filter(task => {
                        const progress = progressByCell.get(`${student.id}|${task.key}`);
                        return progress && progress.is_passed === 1;
                    }).length;

                    return `
                        <tr>
                            <td class="teacher-student-column">
                                <strong>${escapeHtml(student.full_name)}</strong>
                            </td>
                            ${taskColumns.map(task => {
                                const progress = progressByCell.get(`${student.id}|${task.key}`);
                                return renderJournalCell(progress, task);
                            }).join("")}
                            <td class="teacher-total-column">${passedCount}/${taskColumns.length}</td>
                        </tr>
                    `;
                }).join("")}
            </tbody>
        </table>
    `;
}


function buildTaskBlocks(taskColumns) {
    const blocks = [];

    for (const task of taskColumns) {
        const lastBlock = blocks[blocks.length - 1];

        if (lastBlock && lastBlock.title === task.block) {
            lastBlock.count += 1;
            continue;
        }

        blocks.push({
            title: task.block,
            count: 1,
            isMajorStart: blocks.length > 0,
        });
    }

    return blocks;
}


function renderJournalCell(progress, task) {
    const attempts = progress ? progress.attempts_count : 0;
    let statusClass = "empty";

    if (progress && progress.is_passed === 1) {
        statusClass = "passed";
    } else if (attempts > 0) {
        statusClass = "tried";
    }

    return `
        <td
            class="teacher-journal-cell ${statusClass} ${task.isMajorStart ? "teacher-major-start" : ""}"
            title="${task.chapter}.${task.topic}.${task.number}: ${attempts} попыток"
        >
            ${attempts}
        </td>
    `;
}


function fillSelect(select, values) {
    select.innerHTML = values.map(value => `
        <option value="${escapeHtml(value)}">${escapeHtml(value)}</option>
    `).join("");
}


function uniqueValues(items, key) {
    return [
        ...new Set(items.map(item => item[key]).filter(Boolean))
    ].sort((left, right) => String(left).localeCompare(String(right), "ru"));
}


function getTaskKey(task) {
    return `${task.chapter}.${task.topic}.${task.number}`;
}


function compareClassNames(left, right) {
    const leftNumber = parseInt(left, 10);
    const rightNumber = parseInt(right, 10);

    if (!Number.isNaN(leftNumber) && !Number.isNaN(rightNumber)) {
        return leftNumber - rightNumber;
    }

    return String(left).localeCompare(String(right), "ru");
}


function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll("\"", "&quot;")
        .replaceAll("'", "&#039;");
}

