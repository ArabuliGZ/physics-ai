// ==================================
// ===== ГЛОБАЛЬНЫЕ ДАННЫЕ =====
// ==================================

// Все задачи из базы
let TASKS = [];

// История переписки с AI
let HISTORY = [];

// Счетчик подсказок
let HINT_LEVEL = 0;

let CURRENT_TASK_IMAGE_URL = null;


// ==================================
// ===== ЗАГРУЗКА ЗАДАЧ =====
// ==================================

async function loadTasks() {

    // Запрашиваем задачи у FastAPI

    const response = await fetch(
        "/tasks"
    );

    // Превращаем JSON в JS объект

    TASKS = await response.json();

    // Заполняем список классов

    fillGroups();

    if (task.image) {

        CURRENT_TASK_IMAGE_URL =
            `/tasks/images/${task.group}/${task.image}.png`;

    } else {

        CURRENT_TASK_IMAGE_URL = null;
    }

}


// ==================================
// ===== ЗАГРУЗКА ПРИ СТАРТЕ =====
// ==================================

autoResize(
    document.getElementById("solution")
);

loadTasks();