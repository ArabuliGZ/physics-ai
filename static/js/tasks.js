// ==================================
// ===== ЗАПОЛНЕНИЕ КЛАССОВ =====
// ==================================

function fillGroups() {

    const groupSelect =
        document.getElementById("group_select");

    // Получаем уникальные группы

    const groups = [
        ...new Set(STATE.tasks.map(t => t.class_id))
    ].sort((left, right) => {
        const leftNumber = parseInt(left, 10);
        const rightNumber = parseInt(right, 10);

        if (!Number.isNaN(leftNumber) && !Number.isNaN(rightNumber)) {
            return leftNumber - rightNumber;
        }

        return String(left).localeCompare(String(right), "ru");
    });

    groupSelect.innerHTML = "";

    for (const group of groups) {

        if (!group)
            continue;

        const option = document.createElement("option");

        option.value = group;

        option.textContent = STATE.groupsById[group] || group;;

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

    STATE.selected.classId = group;

    const chapterSelect =
        document.getElementById("chapter_select");

    chapterSelect.innerHTML = "";

    // Фильтруем задачи по классу

    const filtered = STATE.tasks.filter(
        t => t.class_id === group
    );

    const chapters = [
        ...new Set(
            filtered.map(
                t => t.chapter
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

    STATE.selected.classId = group;
    STATE.selected.chapter = chapter;

    const topicSelect =
        document.getElementById("topic_select");

    topicSelect.innerHTML = "";

    // Фильтруем задачи

    const filtered = STATE.tasks.filter(t => {

        return (
            t.class_id === group &&
            t.chapter === chapter
        );
    });

    // Получаем темы

    const topics = [
        ...new Set(
            filtered.map(
                t => t.topic
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

    return fillTasks();
}


// ==================================
// ===== ЗАПОЛНЕНИЕ ЗАДАЧ =====
// ==================================

async function fillTasks() {

    const group =
        document.getElementById("group_select").value;

    const chapter =
        document.getElementById("chapter_select").value;

    const topic =
        document.getElementById("topic_select").value;

    STATE.selected.classId = group;
    STATE.selected.chapter = chapter;
    STATE.selected.topic = topic;

    const taskSelect =
        document.getElementById("task_select");

    taskSelect.innerHTML = "";

    // Фильтруем задачи

    const filtered = STATE.tasks.filter(t => {

        return (
            t.class_id === group &&
            t.chapter === chapter &&
            t.topic === topic
        );
    });

    filtered.sort((a, b) => {

        const aNum =
            parseInt(a.number);

        const bNum =
            parseInt(b.number);

        return aNum - bNum;
    });

    // Добавляем задачи

    for (const task of filtered) {

        const option = document.createElement("option");

        option.value = task.number;

        option.textContent =
            task.number;

        taskSelect.appendChild(option);
    }

    if (filtered.length > 0) {

        taskSelect.value = filtered[0].number;
    }

    await showSelectedTask();
    updateProgressTable();
}


// ==================================
// ===== ПОКАЗ ВЫБРАННОЙ ЗАДАЧИ =====
// ==================================

async function showSelectedTask() {

    STATE.chat.history = [];

    document.getElementById(
        "chat"
    ).innerHTML = "";

    const group =
        document.getElementById("group_select").value;

    const chapter =
        document.getElementById("chapter_select").value;

    const topic =
        document.getElementById("topic_select").value;

    const taskNumber =
        document.getElementById("task_select").value;

    STATE.selected.classId = group;
    STATE.selected.chapter = chapter;
    STATE.selected.topic = topic;
    STATE.selected.number = taskNumber;

    // Ищем нужную задачу

    const task = STATE.tasks.find(t => {

        return (
            t.class_id === group &&
            t.chapter === chapter &&
            t.topic === topic &&
            t.number === taskNumber
        );
    });

    if (!task)
        return;

    STATE.selected.task = task;

    const view =
        document.getElementById("problem_view");

    // Показываем условие

    view.innerHTML = task.problem;

    const imageBlock =
        document.getElementById("problem_image");

    imageBlock.innerHTML = "";

    // Если есть картинка

    if (task.image) {

        const mediaInfo =
            getTaskMediaInfoFromTask(task);

        if (mediaInfo) {

            STATE.selected.taskMediaUrl = mediaInfo.url;

            renderTaskMedia(
                imageBlock,
                mediaInfo
            );
        }

        else {

            const fallbackMediaInfo = await findExistingTaskMedia(
                task.class_id,
                task.image
            );

            if (!fallbackMediaInfo) {

                STATE.selected.taskMediaUrl = null;

                return;
            }

            STATE.selected.taskMediaUrl = fallbackMediaInfo.url;

            renderTaskMedia(
                imageBlock,
                fallbackMediaInfo
            );
        }
    }

    else {

        STATE.selected.taskMediaUrl = null;
    }

    // Перерисовываем LaTeX

    MathJax.typesetClear([view]);

    MathJax.typesetPromise([view]);
}


async function updateProgressTable() {
    const table = document.getElementById("progress_table");
    const summary = document.getElementById("progress_summary");

    if (!table || !summary) {
        return;
    }

    if (!STATE.student.current) {
        table.innerHTML = "<div class=\"progress-empty\">Войди, чтобы видеть прогресс.</div>";
        summary.textContent = "";
        return;
    }

    const group = document.getElementById("group_select").value;
    if (!group) {
        table.innerHTML = "";
        summary.textContent = "";
        return;
    }

    table.innerHTML = "<div class=\"progress-empty\">Загружаю...</div>";
    summary.textContent = "";

    const params = new URLSearchParams({
        class_id: group
    });

    try {
        const response = await fetch(
            `/students/${STATE.student.current.id}/class-task-map?${params.toString()}`
        );

        if (!response.ok) {
            throw new Error("task map failed");
        }

        const rows = await response.json();
        const solvedCount = rows.filter(row => row.is_passed === 1).length;
        const triedCount = rows.filter(row => row.attempts_count > 0).length;

        summary.textContent =
            `${triedCount}/${rows.length} с попытками, ${solvedCount} сдано`;

        table.innerHTML = `
            <div class="progress-grid">
                ${renderProgressGroups(rows)}
            </div>
        `;
    } catch {
        table.innerHTML = "<div class=\"progress-empty\">Не получилось загрузить прогресс.</div>";
    }
}


function renderProgressGroups(rows) {
    const sections = [
        ...new Set(rows.map(row => `${row.chapter}.${row.topic}`))
    ].sort(compareDottedKeys);

    const sectionColumns = sections.map((section, index) => ({
        section,
        isMajorStart: index > 0 && section.split(".")[0] !== sections[index - 1].split(".")[0],
    }));

    const taskNumbers = [
        ...new Set(rows.map(row => row.number))
    ].sort((left, right) => parseInt(left) - parseInt(right));

    const rowByPosition = new Map();

    for (const row of rows) {
        const key = `${row.chapter}.${row.topic}`;
        rowByPosition.set(`${row.number}|${key}`, row);
    }

    return `
        <div class="progress-matrix">
            <div class="progress-matrix-head">
                <div class="progress-section-title"></div>
                <div class="progress-cells">
                    ${sectionColumns.map(column => `
                        <div class="progress-number ${column.isMajorStart ? "progress-major-start" : ""}">
                            ${column.section}
                        </div>
                    `).join("")}
                </div>
            </div>

            ${taskNumbers.map(number => `
                <div class="progress-section">
                    <div class="progress-section-title">${number}</div>
                    <div class="progress-cells">
                        ${sectionColumns.map(column => {
                            const row = rowByPosition.get(`${number}|${column.section}`);
                            const boundaryClass = column.isMajorStart ? "progress-major-start" : "";

                            return row
                                ? renderProgressCell(row, boundaryClass)
                                : `<div class="progress-cell-placeholder ${boundaryClass}"></div>`;
                        }).join("")}
                    </div>
                </div>
            `).join("")}
        </div>
    `;
}


function compareDottedKeys(left, right) {
    const leftParts = left.split(".").map(part => parseInt(part, 10));
    const rightParts = right.split(".").map(part => parseInt(part, 10));
    const maxLength = Math.max(leftParts.length, rightParts.length);

    for (let index = 0; index < maxLength; index += 1) {
        const leftPart = leftParts[index] || 0;
        const rightPart = rightParts[index] || 0;

        if (leftPart !== rightPart) {
            return leftPart - rightPart;
        }
    }

    return 0;
}


function renderProgressCell(row, boundaryClass = "") {
    const isCurrent =
        row.chapter === STATE.selected.chapter &&
        row.topic === STATE.selected.topic &&
        row.number === STATE.selected.number;

    let statusClass = "empty";

    if (row.is_passed === 1) {
        statusClass = "passed";
    } else if (row.attempts_count > 0) {
        statusClass = "tried";
    }

    return `
        <button
            type="button"
            class="progress-cell ${statusClass} ${boundaryClass} ${isCurrent ? "current" : ""}"
            title="${row.chapter}.${row.topic}.${row.number}: ${row.attempts_count} попыток"
            onclick="openTaskFromProgress('${row.chapter}', '${row.topic}', '${row.number}')"
        >
            <strong>${row.attempts_count}</strong>
        </button>
    `;
}


async function openTaskFromProgress(chapter, topic, taskNumber) {
    const chapterSelect = document.getElementById("chapter_select");
    const topicSelect = document.getElementById("topic_select");
    const taskSelect = document.getElementById("task_select");

    chapterSelect.value = chapter;
    await fillTopics();

    topicSelect.value = topic;
    await fillTasks();

    taskSelect.value = taskNumber;
    await showSelectedTask();
    updateProgressTable();
}


async function loadTaskMediaInfo(group, mediaName) {

    const url =
        `/task-media-info/${encodeURIComponent(group)}/${encodeURIComponent(mediaName)}`;

    try {

        const response = await fetch(url);

        if (!response.ok) {

            return null;
        }

        return await response.json();

    } catch (error) {

        return null;
    }
}


function getTaskMediaInfoFromTask(task) {

    if (!task.image_url) {

        return null;
    }

    return {
        url: task.image_url,
        mime_type: task.image_mime_type,
        is_pdf: task.image_is_pdf,
        is_image: task.image_is_image
    };
}


async function findExistingTaskMedia(group, mediaName) {

    const extensions = [
        ".png",
        ".jpg",
        ".jpeg",
        ".JPG",
        ".pdf"
    ];

    const hasExtension =
        /\.(png|jpe?g|pdf)$/i.test(mediaName);

    const candidates = hasExtension
        ? [mediaName]
        : extensions.map(extension => mediaName + extension);

    for (const candidate of candidates) {

        const url =
            `/tasks/images/${encodeURIComponent(group)}/${encodeURIComponent(candidate)}`;

        try {

            const response = await fetch(
                url,
                {
                    method: "HEAD"
                }
            );

            if (!response.ok) {

                continue;
            }

            const mimeType =
                response.headers.get("content-type")
                || getMimeTypeFromUrl(url);

            return {
                url: url,
                mime_type: mimeType,
                is_pdf: mimeType.includes("application/pdf"),
                is_image: mimeType.startsWith("image/")
            };

        } catch (error) {

            continue;
        }
    }

    return null;
}


function getMimeTypeFromUrl(url) {

    const lowerUrl = url.toLowerCase();

    if (lowerUrl.endsWith(".pdf")) {

        return "application/pdf";
    }

    if (
        lowerUrl.endsWith(".jpg") ||
        lowerUrl.endsWith(".jpeg")
    ) {

        return "image/jpeg";
    }

    return "image/png";
}


function renderTaskMedia(imageBlock, mediaInfo) {

    if (mediaInfo.is_pdf) {

        renderTaskPdf(
            imageBlock,
            mediaInfo.url
        );

        return;
    }

    renderTaskImage(
        imageBlock,
        mediaInfo.url
    );
}


function renderTaskImage(imageBlock, url) {

    const img = document.createElement("img");

    img.src = url;

    img.style.maxWidth = "100%";

    img.style.borderRadius = "10px";

    img.style.marginTop = "10px";

    imageBlock.appendChild(img);
}


function renderTaskPdf(imageBlock, url) {

    const frame = document.createElement("iframe");

    frame.src = url;

    frame.style.width = "100%";

    frame.style.height = "360px";

    frame.style.border = "1px solid #e5e7eb";

    frame.style.borderRadius = "10px";

    frame.style.marginTop = "10px";

    imageBlock.appendChild(frame);
}
