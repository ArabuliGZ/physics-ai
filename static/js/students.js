function saveStudent(student) {
    STATE.student.current = student;
}


function clearSavedStudent() {
    STATE.student.current = null;
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

        return;
    }

    name.textContent = "";
    bar.hidden = true;
    modal.hidden = false;
}


function resetStudentWorkspace() {
    STATE.chat.history = [];
    STATE.chat.hintLevel = 0;

    STATE.upload.attachedFile = null;
    STATE.upload.solutionImage = null;

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
        email: document.getElementById("student_email").value.trim()
    };

    if (!payload.email) {
        errorBox.textContent = "Введи email.";
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
        errorBox.textContent = "Ученик с таким email не найден.";
    } finally {
        button.disabled = false;
    }
}


function logoutStudent() {
    clearSavedStudent();
    resetStudentWorkspace();
    renderStudentSession();
}
