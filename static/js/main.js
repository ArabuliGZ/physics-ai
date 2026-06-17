// ==================================
// ===== ЗАГРУЗКА ЗАДАЧ =====
// ==================================

async function loadTasks() {

    // ===== ЗАДАЧИ =====

    const tasksResponse =
        await fetch("/tasks");

    STATE.tasks =
        await tasksResponse.json();

    // ===== GROUPS =====

    const groupsResponse =
        await fetch("/groups");

    const groups =
        await groupsResponse.json();

    // ===== CREATE MAPPING =====

    STATE.groupsById = {};

    groups.forEach(group => {

        STATE.groupsById[group.id] =
            group.name;
    });

    // ===== FILL UI =====
    fillGroups();
}


// ==================================
// ===== ЗАГРУЗКА ПРИ СТАРТЕ =====
// ==================================

autoResize(
    document.getElementById("solution")
);

loadTasks();
