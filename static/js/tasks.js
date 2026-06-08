// ==================================
// ===== ЗАПОЛНЕНИЕ КЛАССОВ =====
// ==================================

function fillGroups() {

    const groupSelect =
        document.getElementById("group_select");

    // Получаем уникальные группы

    const groups = [
        ...new Set(TASKS.map(t => t.group))
    ];

    groupSelect.innerHTML = "";

    for (const group of groups) {

        if (!group)
            continue;

        const option = document.createElement("option");

        option.value = group;

        option.textContent = GROUP_NAMES[group] || group;;

        groupSelect.appendChild(option);
    }

    fillChapters();
}


// ==================================
// ===== ЗАПОЛНЕНИЕ ГЛАВ =====
// ==================================

function fillChapters() {

    const group =
        document.getElementById("group_select").value;

    const chapterSelect =
        document.getElementById("chapter_select");

    chapterSelect.innerHTML = "";

    // Фильтруем задачи по классу

    const filtered = TASKS.filter(
        t => t.group === group
    );

    // Берем первую часть ID:
    // 3.5.2 -> 3

    const chapters = [
        ...new Set(
            filtered.map(
                t => t.id.split(".")[0]
            )
        )
    ];

    chapters.sort((a, b) => {

        return parseInt(a) - parseInt(b);
    });

    for (const chapter of chapters) {

        const option = document.createElement("option");

        option.value = chapter;

        option.textContent = chapter;

        chapterSelect.appendChild(option);
    }

    fillTopics();
}


// ==================================
// ===== ЗАПОЛНЕНИЕ ТЕМ =====
// ==================================

function fillTopics() {

    const group =
        document.getElementById("group_select").value;

    const chapter =
        document.getElementById("chapter_select").value;

    const topicSelect =
        document.getElementById("topic_select");

    topicSelect.innerHTML = "";

    // Фильтруем задачи

    const filtered = TASKS.filter(t => {

        const parts = t.id.split(".");

        return (
            t.group === group &&
            parts[0] === chapter
        );
    });

    // Получаем темы

    const topics = [
        ...new Set(
            filtered.map(
                t => t.id.split(".")[1]
            )
        )
    ];

    topics.sort((a, b) => {

        return parseInt(a) - parseInt(b);
    });

    for (const topic of topics) {

        const option = document.createElement("option");

        option.value = topic;

        option.textContent = topic;

        topicSelect.appendChild(option);
    }

    if (topics.length > 0) {

        topicSelect.value = topics[0];
    }

    fillTasks();
}


// ==================================
// ===== ЗАПОЛНЕНИЕ ЗАДАЧ =====
// ==================================

function fillTasks() {

    const group =
        document.getElementById("group_select").value;

    const chapter =
        document.getElementById("chapter_select").value;

    const topic =
        document.getElementById("topic_select").value;

    const taskSelect =
        document.getElementById("task_select");

    taskSelect.innerHTML = "";

    // Фильтруем задачи

    const filtered = TASKS.filter(t => {

        const parts = t.id.split(".");

        return (
            t.group === group &&
            parts[0] === chapter &&
            parts[1] === topic
        );
    });

    filtered.sort((a, b) => {

        const aNum =
            parseInt(a.id.split(".")[2]);

        const bNum =
            parseInt(b.id.split(".")[2]);

        return aNum - bNum;
    });

    // Добавляем задачи

    for (const task of filtered) {

        const option = document.createElement("option");

        option.value = task.id;

        option.textContent =
            task.id.split(".")[2];

        taskSelect.appendChild(option);
    }

    if (filtered.length > 0) {

        taskSelect.value = filtered[0].id;
    }

    showSelectedTask();
}


// ==================================
// ===== ПОКАЗ ВЫБРАННОЙ ЗАДАЧИ =====
// ==================================

function showSelectedTask() {

    HISTORY = [];

    document.getElementById(
        "chat"
    ).innerHTML = "";

    const group =
        document.getElementById("group_select").value;

    const taskId =
        document.getElementById("task_select").value;

    // Ищем нужную задачу

    const task = TASKS.find(t => {

        return (
            t.group === group &&
            t.id === taskId
        );
    });

    if (!task)
        return;

    const view =
        document.getElementById("problem_view");

    // Показываем условие

    view.innerHTML = task.problem;

    const imageBlock =
        document.getElementById("problem_image");

    imageBlock.innerHTML = "";

    // Если есть картинка

    if (task.image) {

        CURRENT_TASK_IMAGE_URL =`/tasks/images/${task.group}/${task.image}.png`;

        const img = document.createElement("img");

        img.src =
            `/tasks/images/${task.group}/${task.image}.png`;

        img.style.maxWidth = "100%";

        img.style.borderRadius = "10px";

        img.style.marginTop = "10px";

        imageBlock.appendChild(img);
    }

    else {

        CURRENT_TASK_IMAGE_URL = null;
    }

    // Перерисовываем LaTeX

    MathJax.typesetClear([view]);

    MathJax.typesetPromise([view]);
}