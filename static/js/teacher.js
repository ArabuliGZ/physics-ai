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
    adminClassNameFilter: "",
    adminClassTeacherFilter: "",
    adminClassTaskBaseFilter: "",
    adminTeacherEditingId: null,
    adminSchoolEditingId: null,
    activeAdminView: "classes",
    manualProgressTarget: null,
    currentJournal: null,
    activeView: "classes",
    confirmResolver: null,
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
        switchTeacherView("classes");

        return;
    }

    loginModal.hidden = false;
    app.hidden = true;
    userName.textContent = "";
    renderAdminAccess();
}


function resetTeacherWorkspaceUi() {
    TEACHER_STATE.activeView = "classes";
    TEACHER_STATE.activeAdminView = "classes";

    const adminCreateClassPanel = document.getElementById("admin_create_class_panel");

    if (adminCreateClassPanel) {
        adminCreateClassPanel.hidden = true;
    }

    [
        "admin_import_result",
        "teacher_single_result",
        "admin_teacher_result",
        "admin_school_result",
    ].forEach(elementId => {
        const element = document.getElementById(elementId);

        if (element) {
            element.textContent = "";
        }
    });

    cancelAdminTeacherEdit();
    cancelAdminSchoolEdit();

    if (document.getElementById("teacher_app")) {
        switchTeacherView("classes");
        switchAdminView("classes");
    }
}


function switchTeacherView(viewName) {
    const adminViewByTeacherView = {
        "admin-schools": "schools",
        "admin-teachers": "teachers",
    };
    let isAdminView = Object.prototype.hasOwnProperty.call(adminViewByTeacherView, viewName);

    if (isAdminView && TEACHER_STATE.user?.role !== "admin") {
        viewName = "classes";
        isAdminView = false;
    }

    const isClassesView = viewName === "classes";

    TEACHER_STATE.activeView = viewName;

    if (isAdminView) {
        switchAdminView(adminViewByTeacherView[viewName]);
    } else if (isClassesView) {
        switchAdminView("classes");
    }

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
            section.hidden = section.dataset.teacherView !== (isAdminView || isClassesView ? "admin" : viewName);
        });
}


function switchAdminView(viewName) {
    const allowedViews = new Set(["classes", "teachers", "schools"]);

    if (!allowedViews.has(viewName)) {
        viewName = "classes";
    }

    TEACHER_STATE.activeAdminView = viewName;

    document
        .querySelectorAll("[data-admin-view]")
        .forEach(section => {
            section.hidden = section.dataset.adminView !== viewName;
        });

    document
        .querySelectorAll("[data-admin-tab]")
        .forEach(tab => {
            tab.classList.toggle("active", tab.dataset.adminTab === viewName);
        });
}


function renderAdminAccess() {
    const isAdmin = TEACHER_STATE.user?.role === "admin";

    document
        .querySelectorAll("[data-admin-only]")
        .forEach(element => {
            element.hidden = !isAdmin;
        });

    if (!isAdmin && TEACHER_STATE.activeView.startsWith("admin-")) {
        switchTeacherView("classes");
    }
}


function toggleAdminCreateClassForm() {
    const panel = document.getElementById("admin_create_class_panel");

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
    const password = document.getElementById("teacher_password").value;

    if (!email || !password) {
        errorBox.textContent = "Введи email и пароль.";
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
                body: JSON.stringify({ email, password }),
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
    const sessionToken = TEACHER_STATE.user?.session_token;

    if (sessionToken) {
        fetch(
            "/auth/logout",
            {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${sessionToken}`,
                },
            }
        ).catch(error => {
            console.warn("Teacher logout request failed:", error);
        });
    }

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

    if (TEACHER_STATE.user?.session_token) {
        headers.set("Authorization", `Bearer ${TEACHER_STATE.user.session_token}`);
    } else if (TEACHER_STATE.user?.email) {
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

        fillTeacherFilters(currentFilters || TEACHER_STATE.selectedFilters);
        await loadAdminDashboardIfNeeded();
        fillAdminImportForm();
        renderAdminClasses();
        switchAdminView(TEACHER_STATE.activeAdminView);
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
    fillAdminClassTeacherFilter();
    fillAdminImportForm();
    renderAdminClasses();
    switchAdminView(TEACHER_STATE.activeAdminView);
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
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody>
                ${TEACHER_STATE.adminTeachers.map(teacher => `
                    <tr class="${teacher.is_active ? "" : "teacher-admin-row-archived"}">
                        <td>${escapeHtml(teacher.full_name)}</td>
                        <td>${escapeHtml(teacher.email)}</td>
                        <td>${teacher.active_classes} / ${teacher.archived_classes}</td>
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
    const editButton = `
        <button
            type="button"
            class="teacher-admin-action"
            onclick="editAdminTeacher(${teacher.id})"
        >
            Изменить
        </button>
    `;

    if (teacher.is_active) {
        return `
            <div class="teacher-admin-actions">
                ${editButton}
                <button
                    type="button"
                    class="teacher-admin-action teacher-admin-action-archive"
                    onclick="deactivateAdminTeacher(${teacher.id})"
                >
                    Архивировать
                </button>
            </div>
        `;
    }

    return `
        <div class="teacher-admin-actions">
            ${editButton}
            <button
                type="button"
                class="teacher-admin-action teacher-admin-action-restore"
                onclick="restoreAdminTeacher(${teacher.id})"
            >
                Восстановить
            </button>
        </div>
    `;
}


function editAdminTeacher(teacherId) {
    const teacher = TEACHER_STATE.adminTeachers.find(item => item.id === teacherId);

    if (!teacher) {
        return;
    }

    TEACHER_STATE.adminTeacherEditingId = teacher.id;
    document.getElementById("admin_teacher_full_name").value = teacher.full_name || "";
    document.getElementById("admin_teacher_email").value = teacher.email || "";

    const submitButton = document.getElementById("admin_teacher_button");
    const cancelButton = document.getElementById("admin_teacher_cancel");

    if (submitButton) {
        submitButton.textContent = "Сохранить";
    }

    if (cancelButton) {
        cancelButton.hidden = false;
    }
}


function cancelAdminTeacherEdit() {
    TEACHER_STATE.adminTeacherEditingId = null;

    const fullNameInput = document.getElementById("admin_teacher_full_name");
    const emailInput = document.getElementById("admin_teacher_email");
    const submitButton = document.getElementById("admin_teacher_button");
    const cancelButton = document.getElementById("admin_teacher_cancel");

    if (fullNameInput) {
        fullNameInput.value = "";
    }

    if (emailInput) {
        emailInput.value = "";
    }

    if (submitButton) {
        submitButton.textContent = "Добавить";
    }

    if (cancelButton) {
        cancelButton.hidden = true;
    }
}


async function upsertAdminTeacher(event) {
    event.preventDefault();

    const result = document.getElementById("admin_teacher_result");
    const payload = {
        teacher_id: TEACHER_STATE.adminTeacherEditingId,
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
        cancelAdminTeacherEdit();
        result.textContent = data.action === "created"
            ? "Учитель добавлен."
            : "Учитель обновлён.";
        await loadTeacherDashboard();
    } catch (error) {
        console.error("Teacher save failed:", error);
        result.textContent = error.message === "Teacher email already exists"
            ? "Такой email уже есть."
            : "Не получилось сохранить учителя.";
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


function fillAdminClassTeacherFilter() {
    const select = document.getElementById("admin_class_teacher_filter");

    if (!select) {
        return;
    }

    const teacherIds = [
        ...new Set(TEACHER_STATE.adminClasses.map(classItem => classItem.teacher_id))
    ].filter(Boolean).map(String);
    const teachers = TEACHER_STATE.adminTeachers
        .filter(teacher => teacherIds.includes(String(teacher.id)))
        .sort((left, right) => String(left.full_name).localeCompare(String(right.full_name), "ru"));
    const previousValue = TEACHER_STATE.adminClassTeacherFilter;

    select.innerHTML = `
        <option value="">Все учителя</option>
        ${teachers.map(teacher => `
            <option value="${teacher.id}">${escapeHtml(teacher.full_name)}</option>
        `).join("")}
    `;

    if (teachers.some(teacher => String(teacher.id) === String(previousValue))) {
        select.value = previousValue;
    } else {
        TEACHER_STATE.adminClassTeacherFilter = "";
    }
}


function handleAdminClassFilterChange() {
    const schoolSelect = document.getElementById("admin_class_school_filter");
    const classSelect = document.getElementById("admin_class_name_filter");
    const teacherSelect = document.getElementById("admin_class_teacher_filter");
    const taskBaseSelect = document.getElementById("admin_class_task_base_filter");

    TEACHER_STATE.adminClassSchoolFilter = schoolSelect?.value || "";
    TEACHER_STATE.adminClassNameFilter = classSelect?.value || "";
    TEACHER_STATE.adminClassTeacherFilter = teacherSelect?.value || "";
    TEACHER_STATE.adminClassTaskBaseFilter = taskBaseSelect?.value || "";
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
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody>
                ${TEACHER_STATE.adminSchools.map(school => `
                    <tr class="${school.is_active ? "" : "teacher-admin-row-archived"}">
                        <td>${escapeHtml(school.name)}</td>
                        <td>${school.active_classes} / ${school.archived_classes}</td>
                        <td>${school.active_students}</td>
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
    const editButton = `
        <button
            type="button"
            class="teacher-admin-action"
            onclick="editAdminSchool(${school.id})"
        >
            Изменить
        </button>
    `;

    if (school.is_active) {
        return `
            <div class="teacher-admin-actions">
                ${editButton}
                <button
                    type="button"
                    class="teacher-admin-action teacher-admin-action-archive"
                    onclick="deactivateAdminSchool(${school.id})"
                >
                    Архивировать
                </button>
            </div>
        `;
    }

    return `
        <div class="teacher-admin-actions">
            ${editButton}
            <button
                type="button"
                class="teacher-admin-action teacher-admin-action-restore"
                onclick="restoreAdminSchool(${school.id})"
            >
                Восстановить
            </button>
        </div>
    `;
}


function editAdminSchool(schoolId) {
    const school = TEACHER_STATE.adminSchools.find(item => item.id === schoolId);

    if (!school) {
        return;
    }

    TEACHER_STATE.adminSchoolEditingId = school.id;
    document.getElementById("admin_school_name").value = school.name || "";

    const submitButton = document.getElementById("admin_school_button");
    const cancelButton = document.getElementById("admin_school_cancel");

    if (submitButton) {
        submitButton.textContent = "Сохранить";
    }

    if (cancelButton) {
        cancelButton.hidden = false;
    }
}


function cancelAdminSchoolEdit() {
    TEACHER_STATE.adminSchoolEditingId = null;

    const nameInput = document.getElementById("admin_school_name");
    const submitButton = document.getElementById("admin_school_button");
    const cancelButton = document.getElementById("admin_school_cancel");

    if (nameInput) {
        nameInput.value = "";
    }

    if (submitButton) {
        submitButton.textContent = "Добавить";
    }

    if (cancelButton) {
        cancelButton.hidden = true;
    }
}


async function upsertAdminSchool(event) {
    event.preventDefault();

    const result = document.getElementById("admin_school_result");
    const payload = {
        school_id: TEACHER_STATE.adminSchoolEditingId,
        name: document.getElementById("admin_school_name").value.trim(),
    };

    if (!payload.name) {
        result.textContent = "Напиши название школы.";
        return;
    }

    result.textContent = "Сохраняю...";

    try {
        const response = await teacherFetch(
            "/admin/schools",
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
            throw new Error(data.detail || "school save failed");
        }

        cancelAdminSchoolEdit();
        result.textContent = data.action === "created"
            ? "Школа добавлена."
            : "Школа обновлена.";
        await loadTeacherDashboard();
    } catch (error) {
        console.error("School save failed:", error);
        result.textContent = error.message === "School already exists"
            ? "Такая школа уже есть."
            : "Не получилось сохранить школу.";
    }
}


function renderAdminClasses() {
    const table = document.getElementById("admin_classes_table");
    const isAdmin = TEACHER_STATE.user?.role === "admin";

    if (!table) {
        return;
    }

    const classRows = getClassTableRows();
    const filteredClasses = classRows.filter(classItem => {
        const matchesSchool = !TEACHER_STATE.adminClassSchoolFilter
            || classItem.school === TEACHER_STATE.adminClassSchoolFilter;
        const matchesClassName = !TEACHER_STATE.adminClassNameFilter
            || String(classItem.grade) === String(TEACHER_STATE.adminClassNameFilter);
        const matchesTeacher = !isAdmin
            || !TEACHER_STATE.adminClassTeacherFilter
            || String(classItem.teacher_id) === String(TEACHER_STATE.adminClassTeacherFilter);
        const matchesTaskBase = !TEACHER_STATE.adminClassTaskBaseFilter
            || classItem.task_class_id === TEACHER_STATE.adminClassTaskBaseFilter;

        return matchesSchool && matchesClassName && matchesTeacher && matchesTaskBase;
    });

    table.innerHTML = `
        <table class="teacher-admin-list ${isAdmin ? "" : "teacher-admin-list-compact"}">
            <colgroup>
                <col class="admin-class-col-school">
                <col class="admin-class-col-class">
                <col class="admin-class-col-base">
                <col class="admin-class-col-students">
                <col class="admin-class-col-actions">
                ${isAdmin ? "<col class=\"admin-class-col-teacher\">" : ""}
            </colgroup>
            <thead>
                <tr>
                    <th>
                        <div class="teacher-admin-th-filter">
                            <span>Школа</span>
                            <select
                                id="admin_class_school_filter"
                                onchange="handleAdminClassFilterChange()"
                            >
                                ${renderAdminClassSchoolFilterOptions()}
                            </select>
                        </div>
                    </th>
                    <th>
                        <div class="teacher-admin-th-filter">
                            <span>Класс</span>
                            <select
                                id="admin_class_name_filter"
                                onchange="handleAdminClassFilterChange()"
                            >
                                ${renderAdminClassNameFilterOptions()}
                            </select>
                        </div>
                    </th>
                    <th>
                        <div class="teacher-admin-th-filter">
                            <span>База</span>
                            <select
                                id="admin_class_task_base_filter"
                                onchange="handleAdminClassFilterChange()"
                            >
                                ${renderAdminClassTaskBaseFilterOptions()}
                            </select>
                        </div>
                    </th>
                    <th><span class="teacher-admin-th-plain">Ученики</span></th>
                    <th><span class="teacher-admin-th-plain">Действия</span></th>
                    ${isAdmin ? `
                    <th>
                        <div class="teacher-admin-th-filter">
                            <span>Учитель</span>
                            <select
                                id="admin_class_teacher_filter"
                                onchange="handleAdminClassFilterChange()"
                            >
                                ${renderAdminClassTeacherFilterOptions()}
                            </select>
                        </div>
                    </th>
                    ` : ""}
                </tr>
            </thead>
            <tbody>
                ${filteredClasses.length === 0 ? `
                    <tr>
                        <td colspan="${isAdmin ? 6 : 5}">Классов по выбранным фильтрам нет.</td>
                    </tr>
                ` : filteredClasses.map(classItem => `
                    <tr class="${classItem.is_active ? "" : "teacher-admin-row-archived"}">
                        <td><span class="teacher-admin-cell-text">${escapeHtml(classItem.school)}</span></td>
                        <td>
                            <div class="teacher-admin-class-cell">
                                <span class="teacher-admin-cell-text">${escapeHtml(classItem.class_name)}</span>
                                ${renderAdminClassJournalButton(classItem)}
                            </div>
                        </td>
                        <td><span class="teacher-admin-cell-text">${escapeHtml(TEACHER_STATE.groupsById[classItem.task_class_id] || classItem.task_class_id)}</span></td>
                        <td><span class="teacher-admin-cell-text">${classItem.active_students}</span></td>
                        <td>
                            ${renderAdminClassAction(classItem)}
                        </td>
                        ${isAdmin ? `<td>${renderAdminClassTeacherControl(classItem)}</td>` : ""}
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}


function getClassTableRows() {
    const isAdmin = TEACHER_STATE.user?.role === "admin";
    const source = isAdmin ? TEACHER_STATE.adminClasses : TEACHER_STATE.classes;

    return source.map(classItem => ({
        ...classItem,
        active_students: classItem.active_students ?? classItem.students_count ?? 0,
        is_active: classItem.is_active ?? 1,
    }));
}


function renderAdminClassSchoolFilterOptions() {
    const classRows = getClassTableRows();
    const schools = [
        ...new Set(classRows.map(classItem => classItem.school))
    ].filter(Boolean).sort((left, right) => String(left).localeCompare(String(right), "ru"));

    if (!schools.includes(TEACHER_STATE.adminClassSchoolFilter)) {
        TEACHER_STATE.adminClassSchoolFilter = "";
    }

    return `
        <option value="">Все школы</option>
        ${schools.map(school => `
            <option
                value="${escapeHtml(school)}"
                ${school === TEACHER_STATE.adminClassSchoolFilter ? "selected" : ""}
            >
                ${escapeHtml(school)}
            </option>
        `).join("")}
    `;
}


function renderAdminClassNameFilterOptions() {
    const classRows = getClassTableRows();
    const grades = [
        ...new Set(classRows.map(classItem => classItem.grade))
    ].filter(grade => grade !== null && grade !== undefined).sort((left, right) => Number(left) - Number(right));

    if (!grades.map(String).includes(String(TEACHER_STATE.adminClassNameFilter))) {
        TEACHER_STATE.adminClassNameFilter = "";
    }

    return `
        <option value="">Все параллели</option>
        ${grades.map(grade => `
            <option
                value="${grade}"
                ${String(grade) === String(TEACHER_STATE.adminClassNameFilter) ? "selected" : ""}
            >
                ${grade}
            </option>
        `).join("")}
    `;
}


function renderAdminClassTeacherFilterOptions() {
    const classRows = getClassTableRows();
    const teacherIds = [
        ...new Set(classRows.map(classItem => classItem.teacher_id))
    ].filter(Boolean).map(String);
    const teachers = TEACHER_STATE.adminTeachers
        .filter(teacher => teacherIds.includes(String(teacher.id)))
        .sort((left, right) => String(left.full_name).localeCompare(String(right.full_name), "ru"));

    if (!teachers.some(teacher => String(teacher.id) === String(TEACHER_STATE.adminClassTeacherFilter))) {
        TEACHER_STATE.adminClassTeacherFilter = "";
    }

    return `
        <option value="">Все учителя</option>
        ${teachers.map(teacher => `
            <option
                value="${teacher.id}"
                ${String(teacher.id) === String(TEACHER_STATE.adminClassTeacherFilter) ? "selected" : ""}
            >
                ${escapeHtml(teacher.full_name)}
            </option>
        `).join("")}
    `;
}


function renderAdminClassTaskBaseFilterOptions() {
    const classRows = getClassTableRows();
    const taskBases = [
        ...new Set(classRows.map(classItem => classItem.task_class_id))
    ].filter(Boolean).sort(compareClassNames);

    if (!taskBases.includes(TEACHER_STATE.adminClassTaskBaseFilter)) {
        TEACHER_STATE.adminClassTaskBaseFilter = "";
    }

    return `
        <option value="">Все базы</option>
        ${taskBases.map(taskBase => `
            <option
                value="${escapeHtml(taskBase)}"
                ${taskBase === TEACHER_STATE.adminClassTaskBaseFilter ? "selected" : ""}
            >
                ${escapeHtml(TEACHER_STATE.groupsById[taskBase] || taskBase)}
            </option>
        `).join("")}
    `;
}


function renderAdminClassTeacherControl(classItem) {
    const currentTeacherExists = TEACHER_STATE.adminTeachers.some(teacher => (
        Number(teacher.id) === Number(classItem.teacher_id)
    ));
    const teachers = TEACHER_STATE.adminTeachers.filter(teacher => (
        teacher.is_active || Number(teacher.id) === Number(classItem.teacher_id)
    ));

    if (!currentTeacherExists && classItem.teacher_id) {
        teachers.push({
            id: classItem.teacher_id,
            full_name: classItem.teacher_name || classItem.teacher_email || "Архивный учитель",
            is_active: 0,
        });
    }

    return `
        <select
            class="teacher-admin-inline-select"
            onchange="updateAdminClassTeacher(${classItem.id}, this.value)"
        >
            ${teachers.map(teacher => `
                <option
                    value="${teacher.id}"
                    ${Number(teacher.id) === Number(classItem.teacher_id) ? "selected" : ""}
                >
                    ${escapeHtml(teacher.full_name)}${teacher.is_active ? "" : " · архив"}
                </option>
            `).join("")}
        </select>
    `;
}


function renderAdminClassAction(classItem) {
    if (classItem.is_active) {
        return `
            <div class="teacher-admin-actions">
                <button
                    type="button"
                    class="teacher-admin-action teacher-admin-action-archive"
                    onclick="deactivateAdminClass(${classItem.id})"
                >
                    Архивировать
                </button>
            </div>
        `;
    }

    return `
        <div class="teacher-admin-actions">
            <button
                type="button"
                class="teacher-admin-action teacher-admin-action-restore"
                onclick="restoreAdminClass(${classItem.id})"
            >
                Восстановить
            </button>
        </div>
    `;
}


function renderAdminClassJournalButton(classItem) {
    if (!classItem.is_active) {
        return `
            <button
                type="button"
                class="teacher-admin-class-journal-button"
                disabled
            >
                Открыть журнал
            </button>
        `;
    }

    return `
        <button
            type="button"
            class="teacher-admin-class-journal-button"
            onclick="openAdminClassJournal(${classItem.id})"
        >
            Открыть журнал
        </button>
    `;
}


async function openAdminClassJournal(classId) {
    const classItem = getClassTableRows().find(item => String(item.id) === String(classId));

    if (!classItem || !classItem.is_active) {
        return;
    }

    ensureTeacherClassAvailable(classItem);
    TEACHER_STATE.selectedFilters = {
        school: classItem.school,
        classKey: String(classItem.id),
        teacherClassId: classItem.id,
        taskClassId: classItem.task_class_id,
    };

    fillTeacherFilters(TEACHER_STATE.selectedFilters);
    switchTeacherView("journal");
    await renderTeacherJournal();
}


function ensureTeacherClassAvailable(classItem) {
    if (TEACHER_STATE.classes.some(item => String(item.id) === String(classItem.id))) {
        return;
    }

    TEACHER_STATE.classes.push({
        id: classItem.id,
        teacher_id: classItem.teacher_id,
        school: classItem.school,
        grade: classItem.grade,
        class_group: classItem.class_group || "",
        class_name: classItem.class_name,
        task_class_id: classItem.task_class_id,
        is_active: classItem.is_active,
        students_count: classItem.active_students || 0,
    });
}


async function updateAdminClassTeacher(classId, teacherId) {
    try {
        const response = await teacherFetch(
            `/admin/classes/${classId}/teacher`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    teacher_id: Number(teacherId),
                }),
            }
        );

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || "class teacher update failed");
        }

        await loadTeacherDashboard();
    } catch (error) {
        console.error("Class teacher update failed:", error);
        alert("Не получилось назначить учителя классу.");
        renderAdminClasses();
    }
}


async function deactivateAdminTeacher(teacherId) {
    const teacher = TEACHER_STATE.adminTeachers.find(item => item.id === teacherId);

    if (!teacher) {
        return;
    }

    const confirmed = await showTeacherConfirm({
        title: "Архивировать учителя",
        message: `Архивировать учителя ${teacher.full_name}?`,
        acceptText: "Архивировать",
    });

    if (!confirmed) {
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

    if (!school) {
        return;
    }

    const confirmed = await showTeacherConfirm({
        title: "Архивировать школу",
        message: `Архивировать школу ${school.name}?`,
        acceptText: "Архивировать",
    });

    if (!confirmed) {
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
    const classItem = getClassTableRows().find(item => String(item.id) === String(classId));

    if (!classItem) {
        return;
    }

    const confirmed = await showTeacherConfirm({
        title: "Архивировать класс",
        message: `Архивировать класс ${classItem.school} · ${classItem.class_name}?`,
        acceptText: "Архивировать",
    });

    if (!confirmed) {
        return;
    }

    await runAdminAction(
        `/teacher/classes/${classId}/deactivate`,
        "Не получилось архивировать класс."
    );
}


async function restoreAdminClass(classId) {
    const url = TEACHER_STATE.user?.role === "admin"
        ? `/admin/classes/${classId}/restore`
        : `/teacher/classes/${classId}/restore`;

    await runAdminAction(
        url,
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


function fillAdminImportForm() {
    fillImportSchoolSelect("admin");
    fillImportTeacherSelect("admin");
    fillImportTaskBaseSelect("admin");
}


function fillImportSchoolSelect(prefix) {
    const select = document.getElementById(`${prefix}_import_school`);

    if (!select) {
        return;
    }

    select.innerHTML = TEACHER_STATE.schools.map(school => `
        <option value="${escapeHtml(school.name)}">
            ${escapeHtml(school.name)}
        </option>
    `).join("");
}


function fillImportTeacherSelect(prefix) {
    const select = document.getElementById(`${prefix}_import_teacher`);

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


function fillImportTaskBaseSelect(prefix) {
    const select = document.getElementById(`${prefix}_import_task_class`);

    if (!select) {
        return;
    }

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


async function importAdminStudents(event) {
    event.preventDefault();

    await importStudentsFromCsv("admin", TEACHER_STATE.user?.role === "admin");
}


async function importStudentsFromCsv(prefix, requireTeacher) {
    const button = document.getElementById(`${prefix}_import_button`);
    const result = document.getElementById(`${prefix}_import_result`);
    const fileInput = document.getElementById(`${prefix}_import_file`);
    const file = fileInput.files[0];

    if (!file) {
        result.textContent = "Выбери CSV-файл.";
        return;
    }

    const formData = new FormData();
    formData.append("school", document.getElementById(`${prefix}_import_school`).value);
    formData.append("grade", document.getElementById(`${prefix}_import_grade`).value);
    formData.append("class_group", document.getElementById(`${prefix}_import_class_group`).value.trim());
    formData.append("task_class_id", document.getElementById(`${prefix}_import_task_class`).value);

    if (requireTeacher) {
        const teacherId = document.getElementById(`${prefix}_import_teacher`).value;

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
        .filter(item => item.school === school && item.is_active)
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
    const confirmed = await showTeacherConfirm({
        title: "Убрать ученика",
        message: "Убрать ученика из журнала? История решений сохранится.",
        acceptText: "Убрать",
    });

    if (!confirmed) {
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


function showTeacherConfirm({ title = "Подтверждение", message, acceptText = "Подтвердить" }) {
    const dialog = document.getElementById("teacher_confirm_dialog");

    document.getElementById("teacher_confirm_title").textContent = title;
    document.getElementById("teacher_confirm_message").textContent = message;
    document.getElementById("teacher_confirm_accept").textContent = acceptText;
    dialog.hidden = false;

    return new Promise(resolve => {
        TEACHER_STATE.confirmResolver = resolve;
    });
}


function closeTeacherConfirmDialog(confirmed) {
    const dialog = document.getElementById("teacher_confirm_dialog");
    const resolver = TEACHER_STATE.confirmResolver;

    dialog.hidden = true;
    TEACHER_STATE.confirmResolver = null;

    if (resolver) {
        resolver(Boolean(confirmed));
    }
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

