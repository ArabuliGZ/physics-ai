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

let GROUP_NAMES = {};

async function loadTasks() {

    // ===== TASKS =====

    const tasksResponse =
        await fetch("/tasks");

    TASKS =
        await tasksResponse.json();

    // ===== GROUPS =====

    const groupsResponse =
        await fetch("/groups");

    const groups =
        await groupsResponse.json();

    // ===== CREATE MAPPING =====

    GROUP_NAMES = {};

    groups.forEach(group => {

        GROUP_NAMES[group.id] =
            group.name;
    });

    // ===== FILL UI =====
    console.log(GROUP_NAMES);
    fillGroups();
}


// ==================================
// ===== ЗАГРУЗКА ПРИ СТАРТЕ =====
// ==================================

autoResize(
    document.getElementById("solution")
);

loadTasks();