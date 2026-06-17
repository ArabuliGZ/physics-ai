// ==================================
// ===== ЗАПОЛНЕНИЕ КЛАССОВ =====
// ==================================

function fillGroups() {

    const groupSelect =
        document.getElementById("group_select");

    // Получаем уникальные группы

    const groups = [
        ...new Set(TASKS.map(t => t.class_id))
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

    const topicSelect =
        document.getElementById("topic_select");

    topicSelect.innerHTML = "";

    // Фильтруем задачи

    const filtered = TASKS.filter(t => {

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

    showSelectedTask();
}


// ==================================
// ===== ПОКАЗ ВЫБРАННОЙ ЗАДАЧИ =====
// ==================================

async function showSelectedTask() {

    HISTORY = [];

    document.getElementById(
        "chat"
    ).innerHTML = "";

    const group =
        document.getElementById("group_select").value;

    const taskNumber =
        document.getElementById("task_select").value;

    // Ищем нужную задачу

    const task = TASKS.find(t => {

        return (
            t.class_id === group &&
            t.chapter === document.getElementById("chapter_select").value &&
            t.topic === document.getElementById("topic_select").value &&
            t.number === taskNumber
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

        const mediaInfo =
            getTaskMediaInfoFromTask(task);

        if (mediaInfo) {

            CURRENT_TASK_IMAGE_URL = mediaInfo.url;

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

                CURRENT_TASK_IMAGE_URL = null;

                return;
            }

            CURRENT_TASK_IMAGE_URL = fallbackMediaInfo.url;

            renderTaskMedia(
                imageBlock,
                fallbackMediaInfo
            );
        }
    }

    else {

        CURRENT_TASK_IMAGE_URL = null;
    }

    // Перерисовываем LaTeX

    MathJax.typesetClear([view]);

    MathJax.typesetPromise([view]);
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
