const TEACHER_STATE = {
    user: null,
    schools: [],
    adminTeachers: [],
    adminSchools: [],
    adminClasses: [],
    classes: [],
    students: [],
    tasks: [],
    groupsById: {},
    selectedFilters: null,
    adminClassSchoolFilter: "",
    manualProgressTarget: null,
    currentJournal: null,
    activeView: "classes",
};


document.addEventListener("DOMContentLoaded", () => {
    initTeacherSession();
});


function initTeacherSession() {
    const params = new URLSearchParams(window.location.search);

    if (params.get("logout") === "1") {
        localStorage.removeItem("physics_ai_teacher");
        window.history.replaceState(null, "", window.location.pathname);
    }

    const savedUser = localStorage.getItem("physics_ai_teacher");

    if (savedUser) {
        try {
            TEACHER_STATE.user = JSON.parse(savedUser);

            if (!TEACHER_STATE.user?.email || !TEACHER_STATE.user?.role) {
                throw new Error("invalid saved teacher");
            }
        } catch {
            TEACHER_STATE.user = null;
            localStorage.removeItem("physics_ai_teacher");
        }
    }

    renderTeacherSession();

    if (TEACHER_STATE.user) {
        loadTeacherDashboard();
    }
}


function renderTeacherSession() {
    const loginModal = document.getElementById("teacher_login_modal");
    const app = document.getElementById("teacher_app");
    const userName = document.getElementById("teacher_user_name");

    if (TEACHER_STATE.user) {
        loginModal.hidden = true;
        app.hidden = false;
        userName.textContent = [
            TEACHER_STATE.user.full_name,
            formatTeacherRole(TEACHER_STATE.user.role),
        ].join(" · ");
        renderAdminAccess();

        return;
    }

    loginModal.hidden = false;
    app.hidden = true;
    userName.textContent = "";
    renderAdminAccess();
}


function resetTeacherWorkspaceUi() {
    TEACHER_STATE.activeView = "classes";

    const createClassPanel = document.getElementById("teacher_create_class_panel");

    if (createClassPanel) {
        createClassPanel.hidden = true;
    }

    [
        "teacher_import_result",
        "teacher_single_result",
        "admin_teacher_result",
    ].forEach(elementId => {
        const element = document.getElementById(elementId);

        if (element) {
            element.textContent = "";
        }
    });

    if (document.getElementById("teacher_app")) {
        switchTeacherView("classes");
    }
}


function switchTeacherView(viewName) {
    if (viewName === "admin" && TEACHER_STATE.user?.role !== "admin") {
        viewName = "classes";
    }

    TEACHER_STATE.activeView = viewName;

    document
        .querySelectorAll("[data-teacher-tab]")
        .forEach(button => {
            button.classList.toggle(
                "is-active",
                button.dataset.teacherTab === viewName
            );
        });

    document
        .querySelectorAll("[data-teacher-view]")
        .forEach(section => {
            section.hidden = section.dataset.teacherView !== viewName;
        });
}


function renderAdminAccess() {
    const isAdmin = TEACHER_STATE.user?.role === "admin";

    document
        .querySelectorAll("[data-admin-only]")
        .forEach(element => {
            element.hidden = !isAdmin;
        });

    if (!isAdmin && TEACHER_STATE.activeView === "admin") {
        switchTeacherView("classes");
    }
}


function toggleTeacherCreateClassForm() {
    const panel = document.getElementById("teacher_create_class_panel");

    if (!panel) {
        return;
    }

    panel.hidden = !panel.hidden;
}


function formatTeacherRole(role) {
    if (role === "admin") {
        return "администратор";
    }

    return "учитель";
}


async function handleTeacherLogin(event) {
    event.preventDefault();

    const button = document.getElementById("teacher_login_button");
    const errorBox = document.getElementById("teacher_login_error");
    const email = document.getElementById("teacher_email").value.trim().toLowerCase();

    if (!email) {
        errorBox.textContent = "Введи email.";
        return;
    }

    button.disabled = true;
    errorBox.textContent = "";

    try {
        const response = await fetch(
            "/auth/login",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ email }),
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "teacher login failed");
        }

        if (data.role !== "teacher" && data.role !== "admin") {
            throw new Error("not a teacher");
        }

        TEACHER_STATE.user = data;
        localStorage.setItem("physics_ai_teacher", JSON.stringify(data));
        resetTeacherWorkspaceUi();
        renderTeacherSession();
        await loadTeacherDashboard();
    } catch (error) {
        console.error("Teacher login failed:", error);
        errorBox.textContent = `Не получилось войти: ${error.message}`;
    } finally {
        button.disabled = false;
    }
}


function logoutTeacher() {
    TEACHER_STATE.user = null;
    TEACHER_STATE.schools = [];
    TEACHER_STATE.adminTeachers = [];
    TEACHER_STATE.adminSchools = [];
    TEACHER_STATE.adminClasses = [];
    TEACHER_STATE.classes = [];
    TEACHER_STATE.students = [];
    TEACHER_STATE.selectedFilters = null;
    TEACHER_STATE.currentJournal = null;
    resetTeacherWorkspaceUi();
    localStorage.removeItem("physics_ai_teacher");
    renderTeacherSession();
}


function teacherFetch(url, options = {}) {
    const headers = new Headers(options.headers || {});

    if (TEACHER_STATE.user?.email) {
        headers.set("X-User-Email", TEACHER_STATE.user.email);
    }

    return fetch(url, {
        ...options,
        headers,
    });
}


async function loadTeacherDashboard() {
    const table = document.getElementById("teacher_journal_table");
    const summary = document.getElementById("teacher_journal_summary");
    const currentFilters = readTeacherFilters();

    if (!TEACHER_STATE.user) {
        return;
    }

    table.innerHTML = "<div class=\"progress-empty\">Загружаю...</div>";
    summary.textContent = "";

    try {
        const [schoolsResponse, classesResponse, studentsResponse, tasksResponse, groupsResponse] = await Promise.all([
            teacherFetch("/teacher/schools"),
            teacherFetch("/teacher/classes"),
            teacherFetch("/teacher/students"),
            fetch("/tasks"),
            fetch("/groups"),
        ]);

        if (!schoolsResponse.ok || !classesResponse.ok || !studentsResponse.ok || !tasksResponse.ok || !groupsResponse.ok) {
            throw new Error("teacher dashboard request failed");
        }

        const groups = await groupsResponse.json();

        TEACHER_STATE.schools = await schoolsResponse.json();
        TEACHER_STATE.classes = await classesResponse.json();
        TEACHER_STATE.students = await studentsResponse.json();
        TEACHER_STATE.tasks = await tasksResponse.json();
        TEACHER_STATE.groupsById = Object.fromEntries(
            groups.map(group => [group.id, group.name])
        );

        fillTeacherImportTaskBases();
        fillTeacherImportSchools();
        fillTeacherFilters(currentFilters || TEACHER_STATE.selectedFilters);
        renderTeacherClassesList();
        await loadAdminDashboardIfNeeded();
        fillTeacherImportTeachers();
        await renderTeacherJournal();
    } catch (error) {
        console.error("Teacher dashboard failed:", error);
        table.innerHTML = "<div class=\"progress-empty\">Не получилось загрузить журнал.</div>";
    }
}


async function loadAdminDashboardIfNeeded() {
    if (TEACHER_STATE.user?.role !== "admin") {
        return;
    }

    const [teachersResponse, schoolsResponse, classesResponse] = await Promise.all([
        teacherFetch("/admin/teachers"),
        teacherFetch("/admin/schools"),
        teacherFetch("/admin/classes"),
    ]);

    if (!teachersResponse.ok || !schoolsResponse.ok || !classesResponse.ok) {
        throw new Error("admin dashboard request failed");
    }

    TEACHER_STATE.adminTeachers = await teachersResponse.json();
    TEACHER_STATE.adminSchools = await schoolsResponse.json();
    TEACHER_STATE.adminClasses = await classesResponse.json();
    renderAdminDashboard();
}


function renderAdminDashboard() {
    renderAdminTeachers();
    renderAdminSchools();
    fillAdminClassSchoolFilter();
    renderAdminClasses();
}


function renderAdminTeachers() {
    const table = document.getElementById("admin_teachers_table");

    if (!table) {
        return;
    }

    if (TEACHER_STATE.adminTeachers.length === 0) {
        table.innerHTML = "<div class=\"progress-empty\">Учителей пока нет.</div>";
        return;
    }

    table.innerHTML = `
        <table class="teacher-admin-list">
            <thead>
                <tr>
                    <th>ФИО</th>
                    <th>Email</th>
                    <th>Классы</th>
                    <th>Статус</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                ${TEACHER_STATE.adminTeachers.map(teacher => `
                    <tr>
                        <td>${escapeHtml(teacher.full_name)}</td>
                        <td>${escapeHtml(teacher.email)}</td>
                        <td>${teacher.active_classes} / ${teacher.archived_classes}</td>
                        <td>${teacher.is_active ? "активен" : "архив"}</td>
                        <td>
                            ${renderAdminTeacherAction(teacher)}
                        </td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}


function renderAdminTeacherAction(teacher) {
    if (teacher.is_active) {
        return `
            <button
                type="button"
                class="teacher-admin-action"
                onclick="deactivateAdminTeacher(${teacher.id})"
            >
                Архивировать
            </button>
        `;
    }

    return `
        <button
            type="button"
            class="teacher-admin-action"
            onclick="restoreAdminTeacher(${teacher.id})"
        >
            Восстановить
        </button>
    `;
}


async function upsertAdminTeacher(event) {
    event.preventDefault();

    const result = document.getElementById("admin_teacher_result");
    const payload = {
        full_name: document.getElementById("admin_teacher_full_name").value.trim(),
        email: document.getElementById("admin_teacher_email").value.trim().toLowerCase(),
    };

    if (!payload.full_name || !payload.email) {
        result.textContent = "Заполни ФИО и email.";
        return;
    }

    result.textContent = "Сохраняю...";

    try {
        const response = await teacherFetch(
            "/admin/teachers",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            }
        );
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "teacher save failed");
        }

        document.getElementById("admin_teacher_full_name").value = "";
        document.getElementById("admin_teacher_email").value = "";
        result.textContent = data.action === "created"
            ? "Учитель добавлен."
            : "Учитель обновлён.";
        await loadTeacherDashboard();
    } catch (error) {
        console.error("Teacher save failed:", error);
        result.textContent = "Не получилось сохранить учителя.";
    }
}


function fillAdminClassSchoolFilter() {
    const select = document.getElementById("admin_class_school_filter");

    if (!select) {
        return;
    }

    const schools = [
        ...new Set(TEACHER_STATE.adminClasses.map(classItem => classItem.school))
    ].filter(Boolean).sort((left, right) => String(left).localeCompare(String(right), "ru"));
    const previousValue = TEACHER_STATE.adminClassSchoolFilter;

    select.innerHTML = `
        <option value="">Все школы</option>
        ${schools.map(school => `
            <option value="${escapeHtml(school)}">${escapeHtml(school)}</option>
        `).join("")}
    `;

    if (schools.includes(previousValue)) {
        select.value = previousValue;
    } else {
        TEACHER_STATE.adminClassSchoolFilter = "";
    }
}


function handleAdminClassSchoolFilterChange() {
    const select = document.getElementById("admin_class_school_filter");

    TEACHER_STATE.adminClassSchoolFilter = select?.value || "";
    renderAdminClasses();
}


function renderAdminSchools() {
    const table = document.getElementById("admin_schools_table");

    if (!table) {
        return;
    }

    if (TEACHER_STATE.adminSchools.length === 0) {
        table.innerHTML = "<div class=\"progress-empty\">Школ пока нет.</div>";
        return;
    }

    table.innerHTML = `
        <table class="teacher-admin-list">
            <thead>
                <tr>
                    <th>Школа</th>
                    <th>Классы</th>
                    <th>Ученики</th>
                    <th>Статус</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                ${TEACHER_STATE.adminSchools.map(school => `
                    <tr>
                        <td>${escapeHtml(school.name)}</td>
                        <td>${school.active_classes} / ${school.archived_classes}</td>
                        <td>${school.active_students}</td>
                        <td>${school.is_active ? "активна" : "архив"}</td>
                        <td>
                            ${renderAdminSchoolAction(school)}
                        </td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}


function renderAdminSchoolAction(school) {
    if (school.is_active) {
        return `
            <button
                type="button"
                class="teacher-admin-action"
                onclick="deactivateAdminSchool(${school.id})"
            >
                Архивировать
            </button>
        `;
    }

    return `
        <button
            type="button"
            class="teacher-admin-action"
            onclick="restoreAdminSchool(${school.id})"
        >
            Восстановить
        </button>
    `;
}


function renderAdminClasses() {
    const table = document.getElementById("admin_classes_table");

    if (!table) {
        return;
    }

    const filteredClasses = TEACHER_STATE.adminClassSchoolFilter
        ? TEACHER_STATE.adminClasses.filter(classItem => (
            classItem.school === TEACHER_STATE.adminClassSchoolFilter
        ))
        : TEACHER_STATE.adminClasses;

    if (filteredClasses.length === 0) {
        table.innerHTML = "<div class=\"progress-empty\">Классов пока нет.</div>";
        return;
    }

    table.innerHTML = `
        <table class="teacher-admin-list">
            <thead>
                <tr>
                    <th>Класс</th>
                    <th>База</th>
                    <th>Учитель</th>
                    <th>Ученики</th>
                    <th>Статус</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                ${filteredClasses.map(classItem => `
                    <tr>
                        <td>${escapeHtml(classItem.school)} · ${escapeHtml(classItem.class_name)}</td>
                        <td>${escapeHtml(TEACHER_STATE.groupsById[classItem.task_class_id] || classItem.task_class_id)}</td>
                        <td>${escapeHtml(classItem.teacher_name || classItem.teacher_email || "Без учителя")}</td>
                        <td>${classItem.active_students}</td>
                        <td>${classItem.is_active ? "активен" : "архив"}</td>
                        <td>
                            ${renderAdminClassAction(classItem)}
                        </td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}


function renderAdminClassAction(classItem) {
    if (classItem.is_active) {
        return `
            <button
                type="button"
                class="teacher-admin-action"
                onclick="deactivateAdminClass(${classItem.id})"
            >
                Архивировать
            </button>
        `;
    }

    return `
        <button
            type="button"
            class="teacher-admin-action"
            onclick="restoreAdminClass(${classItem.id})"
        >
            Восстановить
        </button>
    `;
}


async function deactivateAdminTeacher(teacherId) {
    const teacher = TEACHER_STATE.adminTeachers.find(item => item.id === teacherId);

    if (!teacher || !window.confirm(`Архивировать учителя ${teacher.full_name}?`)) {
        return;
    }

    await runAdminAction(
        `/admin/teachers/${teacherId}/deactivate`,
        "Не получилось архивировать учителя."
    );
}


async function restoreAdminTeacher(teacherId) {
    await runAdminAction(
        `/admin/teachers/${teacherId}/restore`,
        "Не получилось восстановить учителя."
    );
}


async function deactivateAdminSchool(schoolId) {
    const school = TEACHER_STATE.adminSchools.find(item => item.id === schoolId);

    if (!school || !window.confirm(`Архивировать школу ${school.name}?`)) {
        return;
    }

    await runAdminAction(
        `/admin/schools/${schoolId}/deactivate`,
        "Не получилось архивировать школу."
    );
}


async function restoreAdminSchool(schoolId) {
    await runAdminAction(
        `/admin/schools/${schoolId}/restore`,
        "Не получилось восстановить школу."
    );
}


async function deactivateAdminClass(classId) {
    const classItem = TEACHER_STATE.adminClasses.find(item => item.id === classId);

    if (!classItem || !window.confirm(`Архивировать класс ${classItem.school} · ${classItem.class_name}?`)) {
        return;
    }

    await runAdminAction(
        `/teacher/classes/${classId}/deactivate`,
        "Не получилось архивировать класс."
    );
}


async function restoreAdminClass(classId) {
    await runAdminAction(
        `/admin/classes/${classId}/restore`,
        "Не получилось восстановить класс."
    );
}


async function runAdminAction(url, errorMessage) {
    try {
        const response = await teacherFetch(
            url,
            { method: "POST" }
        );

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || "admin action failed");
        }

        TEACHER_STATE.selectedFilters = null;
        TEACHER_STATE.currentJournal = null;
        await loadTeacherDashboard();
    } catch (error) {
        console.error("Admin action failed:", error);
        alert(error.message === "School has active classes"
            ? "Сначала архивируй активные классы этой школы."
            : error.message === "Teacher has active classes"
                ? "Сначала архивируй или передай активные классы этого учителя."
            : errorMessage);
    }
}


function fillTeacherImportSchools() {
    const select = document.getElementById("teacher_import_school");

    if (!select) {
        return;
    }

    select.innerHTML = TEACHER_STATE.schools.map(school => `
        <option value="${escapeHtml(school.name)}">
            ${escapeHtml(school.name)}
        </option>
    `).join("");
}


function fillTeacherImportTeachers() {
    const select = document.getElementById("teacher_import_teacher");

    if (!select) {
        return;
    }

    const activeTeachers = TEACHER_STATE.adminTeachers.filter(teacher => teacher.is_active === 1);

    select.innerHTML = activeTeachers.map(teacher => `
        <option value="${teacher.id}">
            ${escapeHtml(teacher.full_name)}
        </option>
    `).join("");
}


function renderTeacherClassesList() {
    const list = document.getElementById("teacher_classes_list");

    if (!list) {
        return;
    }

    if (!hasTeacherClassRecords()) {
        list.innerHTML = "<div class=\"progress-empty\">Пока нет созданных классов.</div>";
        return;
    }

    const classes = [...TEACHER_STATE.classes].sort((left, right) => (
        String(left.school).localeCompare(String(right.school), "ru") ||
        compareClassNames(left.grade, right.grade) ||
        String(left.class_group || "").localeCompare(String(right.class_group || ""), "ru") ||
        compareClassNames(left.task_class_id, right.task_class_id)
    ));

    list.innerHTML = classes.map(classItem => `
        <article class="teacher-class-row">
            <div class="teacher-class-main">
                <strong>${escapeHtml(classItem.school)} · ${escapeHtml(classItem.class_name)}</strong>
                <span>${escapeHtml(TEACHER_STATE.groupsById[classItem.task_class_id] || classItem.task_class_id)}</span>
            </div>

            <div class="teacher-class-meta">
                ${formatStudentsCount(classItem.students_count || 0)}
            </div>

            <div class="teacher-class-actions">
                <button
                    type="button"
                    class="teacher-secondary-button"
                    onclick="openTeacherClassJournal(${classItem.id})"
                >
                    Открыть журнал
                </button>

                <button
                    type="button"
                    class="teacher-delete-class-button"
                    onclick="deactivateTeacherClass(${classItem.id})"
                    aria-label="Удалить класс"
                    title="Удалить класс"
                >
                    &times;
                </button>
            </div>
        </article>
    `).join("");
}


function openTeacherClassJournal(classId) {
    const classItem = TEACHER_STATE.classes.find(item => String(item.id) === String(classId));

    if (!classItem) {
        return;
    }

    const schoolSelect = document.getElementById("teacher_school_select");
    const classSelect = document.getElementById("teacher_student_class_select");

    schoolSelect.value = classItem.school;
    fillTeacherStudentClasses();
    classSelect.value = String(classItem.id);
    rememberTeacherFilters();
    switchTeacherView("journal");
    renderTeacherJournal();
}


async function deactivateTeacherClass(classId) {
    const classItem = TEACHER_STATE.classes.find(item => String(item.id) === String(classId));

    if (!classItem) {
        return;
    }

    const confirmed = window.confirm(
        `Удалить класс ${classItem.school} · ${classItem.class_name}? Ученики исчезнут из активного журнала, история решений сохранится.`
    );

    if (!confirmed) {
        return;
    }

    try {
        const response = await teacherFetch(
            `/teacher/classes/${classId}/deactivate`,
            { method: "POST" }
        );

        if (!response.ok) {
            throw new Error("class deactivate failed");
        }

        TEACHER_STATE.selectedFilters = null;
        TEACHER_STATE.currentJournal = null;
        await loadTeacherDashboard();
    } catch (error) {
        console.error("Class deactivate failed:", error);
        alert("Не получилось удалить класс.");
    }
}


function readTeacherFilters() {
    const schoolSelect = document.getElementById("teacher_school_select");
    const classSelect = document.getElementById("teacher_student_class_select");
    const selectedClass = getSelectedTeacherClass();

    if (!schoolSelect || !classSelect) {
        return null;
    }

    return {
        school: schoolSelect.value,
        classKey: classSelect.value,
        teacherClassId: selectedClass?.id || "",
        taskClassId: selectedClass?.task_class_id || "",
    };
}


function rememberTeacherFilters() {
    TEACHER_STATE.selectedFilters = readTeacherFilters();
}


function fillTeacherImportTaskBases() {
    const select = document.getElementById("teacher_import_task_class");
    const bases = [
        ...new Set(TEACHER_STATE.tasks.map(task => task.class_id))
    ].sort(compareClassNames);

    select.innerHTML = bases.map(classId => `
        <option value="${escapeHtml(classId)}">
            ${escapeHtml(TEACHER_STATE.groupsById[classId] || classId)}
        </option>
    `).join("");
}


function downloadStudentCsvTemplate() {
    const rows = [
        ["full_name", "email"],
        ["Иванов Иван", "ivanov@example.com"],
        ["Петрова Анна", "petrova@example.com"],
    ];
    const csv = rows
        .map(row => row.map(escapeCsvValue).join(","))
        .join("\n");
    const blob = new Blob(
        [`\ufeff${csv}`],
        { type: "text/csv;charset=utf-8" }
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = "students-template.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}


async function importTeacherStudents(event) {
    event.preventDefault();

    const button = document.getElementById("teacher_import_button");
    const result = document.getElementById("teacher_import_result");
    const fileInput = document.getElementById("teacher_import_file");
    const file = fileInput.files[0];

    if (!file) {
        result.textContent = "Выбери CSV-файл.";
        return;
    }

    const formData = new FormData();
    formData.append("school", document.getElementById("teacher_import_school").value);
    formData.append("grade", document.getElementById("teacher_import_grade").value);
    formData.append("class_group", document.getElementById("teacher_import_class_group").value.trim());
    formData.append("task_class_id", document.getElementById("teacher_import_task_class").value);

    if (TEACHER_STATE.user?.role === "admin") {
        const teacherId = document.getElementById("teacher_import_teacher").value;

        if (!teacherId) {
            result.textContent = "Выбери учителя.";
            return;
        }

        formData.append("teacher_id", teacherId);
    }

    formData.append("file", file);

    button.disabled = true;
    result.textContent = "Загружаю...";

    try {
        const response = await teacherFetch(
            "/teacher/import-students",
            {
                method: "POST",
                body: formData,
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "import failed");
        }

        result.textContent = [
            `создано: ${data.created}`,
            `обновлено: ${data.updated}`,
            `ошибок: ${data.errors.length}`
        ].join(" · ");

        if (data.errors.length > 0) {
            console.warn("Import errors:", data.errors);
        }

        fileInput.value = "";
        await loadTeacherDashboard();
    } catch (error) {
        console.error("Student import failed:", error);
        result.textContent = "Не получилось импортировать CSV.";
    } finally {
        button.disabled = false;
    }
}


async function addSingleTeacherStudent(event) {
    event.preventDefault();

    const button = document.getElementById("teacher_single_button");
    const result = document.getElementById("teacher_single_result");
    const filters = readTeacherFilters();

    if (!filters?.school || !filters?.classKey || !filters?.taskClassId) {
        result.textContent = "Сначала открой нужный журнал класса.";
        return;
    }

    const selectedClass = getSelectedTeacherClass();

    if (!selectedClass) {
        result.textContent = "Сначала открой нужный журнал класса.";
        return;
    }

    const payload = {
        full_name: document.getElementById("teacher_single_full_name").value.trim(),
        email: document.getElementById("teacher_single_email").value.trim(),
        school: selectedClass.school,
        grade: selectedClass.grade,
        class_group: selectedClass.class_group,
        task_class_id: selectedClass.task_class_id,
    };

    if (!payload.full_name || !payload.email) {
        result.textContent = "Заполни ФИО и email.";
        return;
    }

    button.disabled = true;
    result.textContent = "Добавляю...";

    try {
        const response = await teacherFetch(
            "/teacher/students",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            }
        );
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "student save failed");
        }

        result.textContent = data.action === "created"
            ? "Ученик добавлен."
            : "Ученик обновлён.";

        document.getElementById("teacher_single_full_name").value = "";
        document.getElementById("teacher_single_email").value = "";

        rememberTeacherFilters();
        await loadTeacherDashboard();
    } catch (error) {
        console.error("Single student save failed:", error);
        result.textContent = "Не получилось добавить ученика.";
    } finally {
        button.disabled = false;
    }
}


function fillTeacherFilters(filters = null) {
    const schoolSelect = document.getElementById("teacher_school_select");
    const schools = hasTeacherClassRecords()
        ? uniqueValues(TEACHER_STATE.classes, "school")
        : uniqueValues(TEACHER_STATE.students, "school");

    fillSelect(
        schoolSelect,
        schools
    );

    setSelectValueIfExists(schoolSelect, filters?.school);

    fillTeacherStudentClasses();
    setSelectValueIfExists(
        document.getElementById("teacher_student_class_select"),
        filters?.classKey
    );

    if (filters?.taskClassId && getSelectedTeacherTaskClassId() !== filters.taskClassId) {
        selectTeacherClassByTaskBase(filters.taskClassId);
    }
}


function handleTeacherSchoolChange() {
    rememberTeacherFilters();
    fillTeacherStudentClasses();
    renderTeacherJournal();
}


function handleTeacherClassChange() {
    rememberTeacherFilters();
    renderTeacherJournal();
}


function fillTeacherStudentClasses() {
    const school = document.getElementById("teacher_school_select").value;

    if (hasTeacherClassRecords()) {
        fillTeacherStudentClassesFromRecords(school);
        return;
    }

    fillTeacherStudentClassesFromStudents(school);
}


function fillTeacherStudentClassesFromRecords(school) {
    const classes = TEACHER_STATE.classes
        .filter(item => item.school === school)
        .map(item => ({
            id: item.id,
            grade: item.grade,
            class_group: item.class_group || "",
            task_class_id: item.task_class_id,
            title: item.class_name,
            key: String(item.id),
        }))
        .sort((left, right) => (
            compareClassNames(left.grade, right.grade) ||
            String(left.class_group).localeCompare(String(right.class_group), "ru") ||
            compareClassNames(left.task_class_id, right.task_class_id)
        ));

    const select = document.getElementById("teacher_student_class_select");

    select.innerHTML = classes.map(item => `
        <option value="${escapeHtml(item.key)}">${escapeHtml(item.title)}</option>
    `).join("");
}


function fillTeacherStudentClassesFromStudents(school) {
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


function getSelectedTeacherClass() {
    const classKey = document.getElementById("teacher_student_class_select").value;

    if (hasTeacherClassRecords()) {
        return TEACHER_STATE.classes.find(item => String(item.id) === String(classKey)) || null;
    }

    const [grade, classGroup = ""] = classKey.split("|");
    const taskClassId = getSelectedTeacherTaskClassIdFromStudents(grade, classGroup);
    const student = TEACHER_STATE.students.find(candidate => (
        String(candidate.grade) === String(grade) &&
        String(candidate.class_group || "") === String(classGroup || "") &&
        candidate.task_class_id === taskClassId
    ));

    if (!student) {
        return null;
    }

    return {
        id: student.class_id,
        school: student.school,
        grade: student.grade,
        class_group: student.class_group || "",
        class_name: student.class_name,
        task_class_id: taskClassId,
    };
}


function getSelectedTeacherTaskClassId() {
    const selectedClass = getSelectedTeacherClass();

    return selectedClass?.task_class_id || "";
}


function getSelectedTeacherTaskClassIdFromStudents(grade, classGroup) {
    const availableTaskBases = new Set(
        TEACHER_STATE.tasks.map(task => task.class_id)
    );
    const bases = [
        ...new Set(
            TEACHER_STATE.students
                .filter(student => (
                    String(student.grade) === String(grade) &&
                    String(student.class_group || "") === String(classGroup || "") &&
                    student.task_class_id &&
                    availableTaskBases.has(student.task_class_id)
                ))
                .map(student => student.task_class_id)
        )
    ].sort(compareClassNames);

    return bases[0] || "";
}


function selectTeacherClassByTaskBase(taskClassId) {
    const classSelect = document.getElementById("teacher_student_class_select");
    const originalValue = classSelect.value;

    for (const option of classSelect.options) {
        classSelect.value = option.value;

        if (getSelectedTeacherTaskClassId() === taskClassId) {
            return;
        }
    }

    classSelect.value = originalValue;
}


function hasTeacherClassRecords() {
    return Array.isArray(TEACHER_STATE.classes) && TEACHER_STATE.classes.length > 0;
}


async function renderTeacherJournal() {
    const classKey = document.getElementById("teacher_student_class_select").value;
    const selectedClass = getSelectedTeacherClass();
    const school = selectedClass?.school || document.getElementById("teacher_school_select").value;
    const classId = selectedClass?.task_class_id || "";
    const table = document.getElementById("teacher_journal_table");
    const summary = document.getElementById("teacher_journal_summary");
    const exportButton = document.getElementById("teacher_export_button");

    if (classKey && !classId) {
        table.innerHTML = "<div class=\"progress-empty\">Для этого класса пока не выбрана база заданий.</div>";
        summary.textContent = "";
        exportButton.disabled = true;
        return;
    }

    if (!school || !classKey || !classId) {
        table.innerHTML = "<div class=\"progress-empty\">Выбери школу и класс.</div>";
        summary.textContent = "";
        exportButton.disabled = true;
        return;
    }

    const grade = selectedClass.grade;
    const classGroup = selectedClass.class_group || "";

    table.innerHTML = "<div class=\"progress-empty\">Загружаю...</div>";
    summary.textContent = "";

    try {
        const params = new URLSearchParams({
            school,
            grade,
            class_group: classGroup,
            class_id: classId,
        });

        if (selectedClass.id) {
            params.set("teacher_class_id", selectedClass.id);
        }

        const response = await teacherFetch(`/teacher/journal?${params.toString()}`);

        if (!response.ok) {
            throw new Error("teacher journal request failed");
        }

        const journal = await response.json();

        summary.textContent = [
            `${journal.students.length} учеников`,
            `${journal.tasks.length} задач`
        ].join(" · ");
        exportButton.disabled = journal.students.length === 0;

        table.innerHTML = renderJournalTable(journal);
    } catch (error) {
        console.error("Teacher journal failed:", error);
        table.innerHTML = "<div class=\"progress-empty\">Не получилось загрузить журнал.</div>";
        summary.textContent = "";
        exportButton.disabled = true;
    }
}


async function downloadTeacherJournalCsv() {
    const classKey = document.getElementById("teacher_student_class_select").value;
    const selectedClass = getSelectedTeacherClass();
    const school = selectedClass?.school || document.getElementById("teacher_school_select").value;
    const classId = selectedClass?.task_class_id || "";
    const button = document.getElementById("teacher_export_button");

    if (!school || !classKey || !classId || !selectedClass) {
        return;
    }

    const grade = selectedClass.grade;
    const classGroup = selectedClass.class_group || "";
    const params = new URLSearchParams({
        school,
        grade,
        class_group: classGroup,
        class_id: classId,
    });

    if (selectedClass.id) {
        params.set("teacher_class_id", selectedClass.id);
    }

    button.disabled = true;

    try {
        const response = await teacherFetch(`/teacher/journal/export?${params.toString()}`);

        if (!response.ok) {
            throw new Error("teacher journal export failed");
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = url;
        link.download = buildTeacherJournalFileName(school, grade, classGroup, classId);
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    } catch (error) {
        console.error("Teacher journal export failed:", error);
        alert("Не получилось скачать CSV.");
    } finally {
        button.disabled = false;
    }
}


function buildTeacherJournalFileName(school, grade, classGroup, classId) {
    const rawName = [
        "journal",
        school,
        `${grade}${classGroup ? `-${classGroup}` : ""}`,
        classId,
    ].join("-");

    return `${rawName.replace(/[\\/:*?"<>|]+/g, "_")}.csv`;
}


function renderJournalTable(journal) {
    if (journal.students.length === 0) {
        TEACHER_STATE.currentJournal = null;
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
    const journalColumns = buildJournalColumns(taskColumns);
    const headerGroups = buildJournalHeaderGroups(journalColumns);

    for (const progress of journal.progress) {
        progressByCell.set(
            `${progress.student_id}|${getTaskKey(progress)}`,
            progress
        );
    }

    const teacherClassId = journal.class?.id || getSelectedTeacherClass()?.id || null;

    TEACHER_STATE.currentJournal = {
        teacherClassId,
        taskColumns,
        journalColumns,
        progressByCell,
    };

    return `
        <table class="teacher-journal">
            <thead>
                <tr>
                    <th class="teacher-student-column" rowspan="2">Ученик</th>
                    ${headerGroups.map(group => `
                        <th
                            class="${group.className}"
                            colspan="${group.count}"
                        >
                            ${group.title}
                        </th>
                    `).join("")}
                    <th class="teacher-total-column" rowspan="2">Сдано</th>
                </tr>
                <tr>
                    ${journalColumns.map(column => `
                        <th class="${getJournalSubheadingClass(column)}">
                            ${column.type === "chapter-summary" ? "Σ/%" : column.task.number}
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
                          <tr data-student-id="${student.id}">
                              <td class="teacher-student-column">
                                <div class="teacher-student-cell">
                                    <strong>${escapeHtml(student.full_name)}</strong>
                                    <button
                                        type="button"
                                        class="teacher-remove-student"
                                        onclick="deactivateTeacherStudent(${student.id})"
                                        aria-label="Убрать ученика из журнала"
                                        title="Убрать ученика из журнала"
                                    >
                                        &times;
                                    </button>
                                </div>
                            </td>
                            ${journalColumns.map(column => (
                                renderJournalColumnCell(column, student, progressByCell, teacherClassId)
                            )).join("")}
                              <td
                                  class="teacher-total-column"
                                  data-total-student-id="${student.id}"
                              >
                                  ${passedCount}/${taskColumns.length}
                              </td>
                          </tr>
                      `;
                }).join("")}
            </tbody>
        </table>
    `;
}


async function deactivateTeacherStudent(studentId) {
    if (!window.confirm("Убрать ученика из журнала? История решений сохранится.")) {
        return;
    }

    rememberTeacherFilters();

    try {
        const response = await teacherFetch(
            `/teacher/students/${studentId}/deactivate`,
            {
                method: "POST",
            }
        );

        if (!response.ok) {
            throw new Error("student deactivate failed");
        }

        await loadTeacherDashboard();
    } catch (error) {
        console.error("Student deactivate failed:", error);
        document.getElementById("teacher_single_result").textContent =
            "Не получилось убрать ученика.";
    }
}


function buildJournalColumns(taskColumns) {
    const columns = [];

    for (let index = 0; index < taskColumns.length; index += 1) {
        const task = taskColumns[index];
        const nextTask = taskColumns[index + 1];

        columns.push({
            type: "task",
            task,
        });

        if (!nextTask || nextTask.chapter !== task.chapter) {
            columns.push({
                type: "chapter-summary",
                chapter: task.chapter,
                tasks: taskColumns.filter(candidate => candidate.chapter === task.chapter),
            });
        }
    }

    return columns;
}


function buildJournalHeaderGroups(journalColumns) {
    const groups = [];

    for (const column of journalColumns) {
        const title = column.type === "chapter-summary"
            ? column.chapter
            : column.task.block;
        const className = column.type === "chapter-summary"
            ? "teacher-block-heading teacher-chapter-summary-heading teacher-major-start"
            : `teacher-block-heading ${column.task.isMajorStart ? "teacher-major-start" : ""}`;
        const lastGroup = groups[groups.length - 1];

        if (
            column.type === "task" &&
            lastGroup &&
            lastGroup.type === "task" &&
            lastGroup.title === title
        ) {
            lastGroup.count += 1;
            continue;
        }

        groups.push({
            type: column.type,
            title,
            count: 1,
            className,
        });
    }

    return groups;
}


function getJournalSubheadingClass(column) {
    if (column.type === "chapter-summary") {
        return "teacher-task-heading teacher-chapter-summary-heading teacher-major-start";
    }

    return `teacher-task-heading ${column.task.isMajorStart ? "teacher-major-start" : ""}`;
}


function renderJournalColumnCell(column, student, progressByCell, teacherClassId) {
    if (column.type === "chapter-summary") {
        return renderChapterSummaryCell(column, student, progressByCell);
    }

    const progress = progressByCell.get(`${student.id}|${column.task.key}`);
    return renderJournalCell(progress, column.task, student, teacherClassId);
}


function renderChapterSummaryCell(column, student, progressByCell) {
    const passedCount = column.tasks.filter(task => {
        const progress = progressByCell.get(`${student.id}|${task.key}`);
        return progress && progress.is_passed === 1;
    }).length;
    const percent = Math.round((passedCount / column.tasks.length) * 100);
    const hue = Math.round(percent * 1.2);
    const backgroundColor = `hsl(${hue}, 78%, 88%)`;
    const textColor = `hsl(${hue}, 55%, 24%)`;

    return `
        <td
            class="teacher-journal-cell teacher-chapter-summary teacher-major-start"
            data-summary-student-id="${student.id}"
            data-summary-chapter="${column.chapter}"
            style="background: ${backgroundColor}; color: ${textColor};"
            title="Глава ${column.chapter}: ${passedCount}/${column.tasks.length}, ${percent}%"
        >
            <strong>${passedCount}</strong>
            <span>${percent}%</span>
        </td>
    `;
}


function renderJournalCell(progress, task, student, teacherClassId) {
    const attempts = progress ? progress.attempts_count : 0;
    let statusClass = "empty";

    if (progress && progress.is_passed === 1) {
        statusClass = "passed";
    } else if (attempts > 0) {
        statusClass = "tried";
    }

    return `
        <td
            class="teacher-journal-cell teacher-clickable-cell ${statusClass} ${task.isMajorStart ? "teacher-major-start" : ""}"
            data-progress-student-id="${student.id}"
            data-progress-key="${task.key}"
            onclick="openTeacherProgressDialog(${student.id}, ${teacherClassId || "null"}, '${task.class_id}', '${task.chapter}', '${task.topic}', '${task.number}', ${attempts}, ${progress && progress.is_passed === 1 ? 1 : 0})"
            title="${task.chapter}.${task.topic}.${task.number}: ${attempts} попыток"
        >
            ${attempts}
            ${renderTeacherOverrideMarker(progress)}
        </td>
    `;
}


function renderTeacherOverrideMarker(progress) {
    if (!progress || progress.teacher_override === null || progress.teacher_override === undefined) {
        return "";
    }

    const markerClass = progress.teacher_override === 1
        ? "teacher-override-pass"
        : "teacher-override-fail";
    const title = progress.teacher_override === 1
        ? "Учитель зачёл"
        : "Учитель снял зачёт";

    return `<span class="teacher-override-marker ${markerClass}" title="${title}"></span>`;
}


function openTeacherProgressDialog(
    studentId,
    teacherClassId,
    classId,
    chapter,
    topic,
    number,
    attemptsCount,
    isPassed
) {
    TEACHER_STATE.manualProgressTarget = {
        student_id: studentId,
        teacher_class_id: teacherClassId,
        class_id: classId,
        chapter,
        topic,
        number,
    };

    document.getElementById("teacher_progress_dialog_title").textContent =
        `Задача ${chapter}.${topic}.${number}`;
    document.getElementById("teacher_progress_dialog_meta").textContent =
        `Попыток: ${attemptsCount}`;
    document.getElementById("teacher_progress_dialog_status").textContent =
        isPassed ? "Статус: зачтено" : "Статус: не зачтено";
    document.getElementById("teacher_progress_dialog").hidden = false;
}


function closeTeacherProgressDialog() {
    TEACHER_STATE.manualProgressTarget = null;
    document.getElementById("teacher_progress_dialog").hidden = true;
}


async function setTeacherProgressOverride(isPassed) {
    const target = TEACHER_STATE.manualProgressTarget;
    const status = document.getElementById("teacher_progress_dialog_status");

    if (!target) {
        return;
    }

    status.textContent = "Сохраняю...";
    rememberTeacherFilters();

    try {
        const response = await teacherFetch(
            "/teacher/progress",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    ...target,
                    is_passed: isPassed,
                }),
            }
        );

        if (!response.ok) {
            throw new Error("teacher progress override failed");
        }

        const progress = await response.json();
        closeTeacherProgressDialog();
        updateTeacherJournalProgress(progress);
    } catch (error) {
        console.error("Teacher progress override failed:", error);
        status.textContent = "Не получилось сохранить.";
    }
}


function updateTeacherJournalProgress(progress) {
    const journal = TEACHER_STATE.currentJournal;

    if (!journal) {
        return;
    }

    const key = getTaskKey(progress);
    const cellKey = `${progress.student_id}|${key}`;

    journal.progressByCell.set(cellKey, progress);
    updateTeacherTaskCell(progress);
    updateTeacherChapterSummaryCell(progress.student_id, progress.chapter);
    updateTeacherTotalCell(progress.student_id);
}


function updateTeacherTaskCell(progress) {
    const journal = TEACHER_STATE.currentJournal;
    const key = getTaskKey(progress);
    const task = journal.taskColumns.find(candidate => candidate.key === key);
    const cell = document.querySelector(
        `[data-progress-student-id="${progress.student_id}"][data-progress-key="${key}"]`
    );

    if (!task || !cell) {
        return;
    }

    const attempts = progress.attempts_count || 0;
    const isPassed = progress.is_passed === 1;
    const statusClass = isPassed
        ? "passed"
        : attempts > 0
            ? "tried"
            : "empty";

    cell.className = [
        "teacher-journal-cell",
        "teacher-clickable-cell",
        statusClass,
        task.isMajorStart ? "teacher-major-start" : "",
    ].filter(Boolean).join(" ");
    cell.innerHTML = `${attempts}${renderTeacherOverrideMarker(progress)}`;
    cell.title = `${task.chapter}.${task.topic}.${task.number}: ${attempts} попыток`;
    cell.setAttribute(
        "onclick",
        `openTeacherProgressDialog(${progress.student_id}, ${journal.teacherClassId || "null"}, '${task.class_id}', '${task.chapter}', '${task.topic}', '${task.number}', ${attempts}, ${isPassed ? 1 : 0})`
    );
}


function updateTeacherChapterSummaryCell(studentId, chapter) {
    const journal = TEACHER_STATE.currentJournal;
    const column = journal.journalColumns.find(candidate => (
        candidate.type === "chapter-summary" &&
        candidate.chapter === chapter
    ));
    const cell = document.querySelector(
        `[data-summary-student-id="${studentId}"][data-summary-chapter="${chapter}"]`
    );

    if (!column || !cell) {
        return;
    }

    const html = renderChapterSummaryCell(
        column,
        { id: studentId },
        journal.progressByCell
    );
    const template = document.createElement("template");

    template.innerHTML = html.trim();
    cell.replaceWith(template.content.firstElementChild);
}


function updateTeacherTotalCell(studentId) {
    const journal = TEACHER_STATE.currentJournal;
    const totalCell = document.querySelector(
        `[data-total-student-id="${studentId}"]`
    );

    if (!totalCell) {
        return;
    }

    const passedCount = journal.taskColumns.filter(task => {
        const progress = journal.progressByCell.get(`${studentId}|${task.key}`);
        return progress && progress.is_passed === 1;
    }).length;

    totalCell.textContent = `${passedCount}/${journal.taskColumns.length}`;
}


function fillSelect(select, values) {
    select.innerHTML = values.map(value => `
        <option value="${escapeHtml(value)}">${escapeHtml(value)}</option>
    `).join("");
}


function setSelectValueIfExists(select, value) {
    if (!select || !value) {
        return;
    }

    const hasValue = [...select.options].some(option => option.value === value);

    if (hasValue) {
        select.value = value;
    }
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


function formatStudentsCount(count) {
    const lastTwo = count % 100;
    const lastOne = count % 10;

    if (lastTwo >= 11 && lastTwo <= 14) {
        return `${count} учеников`;
    }

    if (lastOne === 1) {
        return `${count} ученик`;
    }

    if (lastOne >= 2 && lastOne <= 4) {
        return `${count} ученика`;
    }

    return `${count} учеников`;
}


function escapeCsvValue(value) {
    const text = String(value ?? "");

    if (!/[",\n\r]/.test(text)) {
        return text;
    }

    return `"${text.replaceAll("\"", "\"\"")}"`;
}


function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll("\"", "&quot;")
        .replaceAll("'", "&#039;");
}

