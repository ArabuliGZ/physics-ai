function autoResize(textarea) {

    textarea.style.height = "44px";

    textarea.style.height =
        textarea.scrollHeight + "px";
}


// ==================================
// ===== ENTER ДЛЯ ОТПРАВКИ =====
// ==================================

function handleEnter(event) {

    if (
        event.key === "Enter" &&
        !event.shiftKey
    ) {

        event.preventDefault();

        checkSolution();
    }
}


// ==================================
// ===== ПЕРЕКЛЮЧЕНИЕ РЕЖИМОВ =====
// ==================================

function switchMode() {

    const mode =
        document.querySelector(
            'input[name="mode"]:checked'
        ).value;

    // ===== РУЧНОЙ ВВОД =====

    if (mode === "manual") {

        document.getElementById(
            "manual_block"
        ).style.display = "block";

        document.getElementById(
            "select_block"
        ).style.display = "none";

        document.getElementById(
            "problem"
        ).style.display = "block";

        document.getElementById(
            "problem_view"
        ).style.display = "none";
    }

    // ===== ВЫБОР ИЗ БАЗЫ =====

    else {

        document.getElementById(
            "manual_block"
        ).style.display = "none";

        document.getElementById(
            "select_block"
        ).style.display = "block";

        document.getElementById(
            "problem"
        ).style.display = "none";

        document.getElementById(
            "problem_view"
        ).style.display = "block";
    }
}