function saveStudent(student) {
    STATE.student.current = student;
    localStorage.setItem("physics_ai_student", JSON.stringify(student));
}


function clearSavedStudent() {
    STATE.student.current = null;
    STATE.student.passwordDialogOpen = false;
    localStorage.removeItem("physics_ai_student");
}


function handleExpiredStudentSession() {
    if (!STATE.student.current) {
        return;
    }

    clearSavedStudent();
    resetStudentWorkspace();
    renderStudentSession();

    const errorBox = document.getElementById("student_login_error");

    if (errorBox) {
        errorBox.textContent = "Сессия истекла. Войди снова.";
    }
}


async function studentFetch(url, options = {}) {
    const headers = new Headers(options.headers || {});

    if (STATE.student.current?.session_token) {
        headers.set("Authorization", `Bearer ${STATE.student.current.session_token}`);
    }

    const response = await fetch(url, {
        ...options,
        headers,
    });

    if (response.status === 401) {
        handleExpiredStudentSession();
    }

    return response;
}


function renderStudentSession() {
    const bar = document.getElementById("student_bar");
    const name = document.getElementById("student_name");
    const modal = document.getElementById("student_modal");

    if (STATE.student.current) {
        name.textContent = [
            STATE.student.current.full_name,
            STATE.student.current.class_name,
            STATE.student.current.school
        ].join(" · ");

        bar.hidden = false;
        modal.hidden = true;
        renderStudentPasswordPrompt();

        return;
    }

    name.textContent = "";
    bar.hidden = true;
    modal.hidden = false;
    renderStudentPasswordPrompt();
}


function mustChangePassword(value) {
    return value === true
        || Number(value) === 1
        || String(value).toLowerCase() === "true";
}


function renderStudentPasswordPrompt() {
    const passwordModal = document.getElementById("student_password_modal");
    const cancelButton = document.getElementById("student_password_cancel");

    if (!passwordModal) {
        return;
    }

    const isRequired = (
        STATE.student.current
        && mustChangePassword(STATE.student.current.must_change_password)
    );
    const isOpen = Boolean(STATE.student.current && STATE.student.passwordDialogOpen);

    passwordModal.hidden = !(isRequired || isOpen);

    if (cancelButton) {
        cancelButton.hidden = isRequired;
    }
}


function openStudentPasswordDialog() {
    if (!STATE.student.current) {
        return;
    }

    STATE.student.passwordDialogOpen = true;
    renderStudentPasswordPrompt();
}


function closeStudentPasswordDialog() {
    if (mustChangePassword(STATE.student.current?.must_change_password)) {
        return;
    }

    STATE.student.passwordDialogOpen = false;
    clearStudentPasswordForm();
    renderStudentPasswordPrompt();
}


function clearStudentPasswordForm() {
    document.getElementById("student_current_password").value = "";
    document.getElementById("student_new_password").value = "";
    document.getElementById("student_repeat_password").value = "";
    document.getElementById("student_password_error").textContent = "";
}


function resetStudentWorkspace() {
    STATE.chat.history = [];
    STATE.chat.hintLevel = 0;

    STATE.upload.attachedFile = null;
    STATE.upload.solutionImage = null;
    STATE.progress.renderedClassId = null;

    STATE.selected.classId = null;
    STATE.selected.chapter = null;
    STATE.selected.topic = null;
    STATE.selected.number = null;
    STATE.selected.task = null;
    STATE.selected.taskMediaUrl = null;

    document.getElementById("chat").innerHTML = "";

    const solutionInput = document.getElementById("solution");
    solutionInput.value = "";
    solutionInput.style.height = "44px";

    if (typeof clearImagePreview === "function") {
        clearImagePreview();
    }

    if (STATE.tasks.length > 0) {
        fillGroups();
    }

    if (typeof updateProgressTable === "function") {
        updateProgressTable();
    }
}


async function initStudentSession() {
    const savedStudent = localStorage.getItem("physics_ai_student");

    if (savedStudent) {
        try {
            STATE.student.current = JSON.parse(savedStudent);

            if (!STATE.student.current?.id || !STATE.student.current?.session_token) {
                throw new Error("invalid saved student");
            }
        } catch {
            clearSavedStudent();
        }
    } else {
        clearSavedStudent();
    }

    renderStudentSession();

    if (!STATE.student.current) {
        return;
    }

    const studentId = STATE.student.current.id;
    const sessionToken = STATE.student.current.session_token;

    try {
        const response = await studentFetch(`/students/${studentId}`);

        if (response.status === 403) {
            handleExpiredStudentSession();
            return;
        }

        if (!response.ok) {
            return;
        }

        const currentStudent = await response.json();

        saveStudent({
            ...currentStudent,
            session_token: sessionToken,
        });
        renderStudentSession();
    } catch (error) {
        console.warn("Student session validation failed:", error);
    }
}


async function handleStudentLogin(event) {
    event.preventDefault();

    const button = document.getElementById("student_login_button");
    const errorBox = document.getElementById("student_login_error");

    const payload = {
        email: document.getElementById("student_email").value.trim(),
        password: document.getElementById("student_password").value
    };

    if (!payload.email || !payload.password) {
        errorBox.textContent = "Введи email и пароль.";
        return;
    }

    button.disabled = true;
    errorBox.textContent = "";

    try {
        const response = await fetch(
            "/students/login",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            }
        );

        if (!response.ok) {
            throw new Error("student login failed");
        }

        const student = await response.json();

        saveStudent(student);
        resetStudentWorkspace();
        renderStudentSession();
    } catch (error) {
        console.error("Student login failed:", error);
        errorBox.textContent = "Неверный email или пароль.";
    } finally {
        button.disabled = false;
    }
}


async function handleStudentPasswordChange(event) {
    event.preventDefault();

    const button = document.getElementById("student_password_button");
    const errorBox = document.getElementById("student_password_error");
    const payload = {
        current_password: document.getElementById("student_current_password").value,
        new_password: document.getElementById("student_new_password").value,
        repeat_password: document.getElementById("student_repeat_password").value,
    };

    if (!payload.current_password || !payload.new_password || !payload.repeat_password) {
        errorBox.textContent = "Заполни все поля.";
        return;
    }

    if (payload.new_password !== payload.repeat_password) {
        errorBox.textContent = "Новые пароли не совпадают.";
        return;
    }

    if (payload.new_password.length < 6) {
        errorBox.textContent = "Пароль должен быть не короче 6 символов.";
        return;
    }

    button.disabled = true;
    errorBox.textContent = "";

    try {
        const response = await studentFetch(
            "/students/change-password",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            }
        );

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(data.detail || "password change failed");
        }

        STATE.student.current.must_change_password = 0;
        STATE.student.passwordDialogOpen = false;
        saveStudent(STATE.student.current);
        clearStudentPasswordForm();
        renderStudentSession();
    } catch (error) {
        console.error("Student password change failed:", error);
        errorBox.textContent = error.message === "invalid_current_password"
            ? "Текущий пароль введён неверно."
            : "Не получилось сменить пароль.";
    } finally {
        button.disabled = false;
    }
}


function logoutStudent() {
    const sessionToken = STATE.student.current?.session_token;

    if (sessionToken) {
        fetch(
            "/students/logout",
            {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${sessionToken}`,
                },
            }
        ).catch(error => {
            console.warn("Student logout request failed:", error);
        });
    }

    clearSavedStudent();
    resetStudentWorkspace();
    renderStudentSession();
}
