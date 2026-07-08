function saveStudent(student) {
    STATE.student.current = student;
}


function clearSavedStudent() {
    STATE.student.current = null;
}


function studentFetch(url, options = {}) {
    const headers = new Headers(options.headers || {});

    if (STATE.student.current?.session_token) {
        headers.set("Authorization", `Bearer ${STATE.student.current.session_token}`);
    }

    return fetch(url, {
        ...options,
        headers,
    });
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

    if (!passwordModal) {
        return;
    }

    passwordModal.hidden = !(
        STATE.student.current
        && mustChangePassword(STATE.student.current.must_change_password)
    );
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


function initStudentSession() {
    localStorage.removeItem("physics_ai_student");
    clearSavedStudent();
    renderStudentSession();
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
        document.getElementById("student_current_password").value = "";
        document.getElementById("student_new_password").value = "";
        document.getElementById("student_repeat_password").value = "";
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
