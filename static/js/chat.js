// ==================================
// ===== ДОБАВЛЕНИЕ СООБЩЕНИЯ =====
// ==================================

function addMessage(text, sender) {

    const chat = document.getElementById("chat");

    // Проверяем:
    // был ли пользователь внизу ДО сообщения

    const wasNearBottom =

        chat.scrollHeight
        - chat.scrollTop
        - chat.clientHeight

        < 100;

    const div = document.createElement("div");

    div.classList.add("message");

    div.classList.add(sender);

    div.textContent = String(text ?? "");

    chat.appendChild(div);

    typesetMath([div]);

    // Автоскролл только если
    // пользователь был внизу

    if (wasNearBottom) {

        chat.scrollTop =
            chat.scrollHeight;
    }
}


// ==================================
// ===== ОТПРАВКА РЕШЕНИЯ =====
// ==================================
function canvasToCompressedJpeg(canvas) {

    const MAX_SIZE = 1080;

    let width = canvas.width;
    let height = canvas.height;

    if (width > height && width > MAX_SIZE) {
        height *= MAX_SIZE / width;
        width = MAX_SIZE;
    } else if (height > MAX_SIZE) {
        width *= MAX_SIZE / height;
        height = MAX_SIZE;
    }

    const outputCanvas = document.createElement("canvas");

    outputCanvas.width = Math.round(width);
    outputCanvas.height = Math.round(height);

    const outputContext = outputCanvas.getContext("2d");

    outputContext.drawImage(
        canvas,
        0,
        0,
        outputCanvas.width,
        outputCanvas.height
    );

    return outputCanvas.toDataURL(
        "image/jpeg",
        0.75
    );
}

async function compressImage(file) {

    return new Promise((resolve) => {

        const img = new Image();

        img.onload = () => {

            const MAX_SIZE = 1080;
            let width = img.width;
            let height = img.height;

            if (width > height && width > MAX_SIZE) {
                height *= MAX_SIZE / width;
                width = MAX_SIZE;
            } else if (height > MAX_SIZE) {
                width *= MAX_SIZE / height;
                height = MAX_SIZE;
            }

            const canvas = document.createElement("canvas");

            canvas.width = Math.round(width);
            canvas.height = Math.round(height);

            const ctx = canvas.getContext("2d");

            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

            resolve(
                canvas.toDataURL(
                    "image/jpeg",
                    0.75
                )
            );
        };

        img.src = URL.createObjectURL(file);
    });
}

async function renderPdfFirstPageAsImage(file) {

    if (!window.pdfjsLib) {
        throw new Error("PDF-модуль не загрузился. Обнови страницу и попробуй ещё раз.");
    }

    window.pdfjsLib.GlobalWorkerOptions.workerSrc =
        "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

    const data = await file.arrayBuffer();
    const pdf = await window.pdfjsLib.getDocument({ data }).promise;
    const page = await pdf.getPage(1);
    const baseViewport = page.getViewport({ scale: 1 });
    const renderScale = Math.min(
        2,
        Math.max(
            1,
            1440 / Math.max(baseViewport.width, baseViewport.height)
        )
    );
    const viewport = page.getViewport({ scale: renderScale });
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");

    canvas.width = Math.round(viewport.width);
    canvas.height = Math.round(viewport.height);

    await page.render({
        canvasContext: context,
        viewport,
    }).promise;

    return canvasToCompressedJpeg(canvas);
}

async function readHeicAsDataUrl(file) {

    const mimeType = file.name.toLowerCase().endsWith(".heif")
        || file.type === "image/heif"
        ? "image/heif"
        : "image/heic";

    return new Promise((resolve, reject) => {
        const reader = new FileReader();

        reader.onload = () => {
            const dataUrl = String(reader.result || "");
            const separatorIndex = dataUrl.indexOf(",");

            if (separatorIndex < 0) {
                reject(new Error("Не получилось прочитать файл HEIC или HEIF."));
                return;
            }

            resolve(
                `data:${mimeType};base64,${dataUrl.slice(separatorIndex + 1)}`
            );
        };

        reader.onerror = () => {
            reject(new Error("Не получилось прочитать файл HEIC или HEIF."));
        };

        reader.readAsDataURL(file);
    });
}

async function prepareSolutionAttachment(file) {

    if (!file) {
        return null;
    }

    if (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) {
        return renderPdfFirstPageAsImage(file);
    }

    if (isHeicSolutionFile(file)) {
        return readHeicAsDataUrl(file);
    }

    return compressImage(file);
}

async function sendSolution(problemText, studentSolution, attachedFile = null) {
    let imageBase64 = null;

    if (attachedFile) {

        imageBase64 =
            await prepareSolutionAttachment(attachedFile);
    }

    const payload = {
        problem: problemText,
        solution: studentSolution,
        history: STATE.chat.history,
        hint_level: STATE.chat.hintLevel,
        problem_image_base64: imageBase64,
        task_image_url: STATE.selected.taskMediaUrl,
        student_id: STATE.student.current?.id || null,
        class_id: STATE.selected.classId,
        chapter: STATE.selected.chapter,
        topic: STATE.selected.topic,
        number: STATE.selected.number
    };

    const fetchWithStudentAuth =
        typeof studentFetch === "function"
            ? studentFetch
            : fetch;

    const response = await fetchWithStudentAuth("/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (response.status === 401) {
        throw new Error("student_session_expired");
    }

    if (!response.ok) {
        throw new Error(data.detail || "Не получилось отправить решение.");
    }

    return data;
}


async function checkSolution() {
    const button = document.querySelector(".send-button");
    if (button.disabled) return;

    if (!STATE.student.current) {
        addMessage(
            "Сначала войди как ученик.",
            "assistant"
        );
        return;
    }

    button.disabled = true;

    const solutionInput = document.getElementById("solution");
    const solution = solutionInput.value.trim();
    solutionInput.value = "";
    solutionInput.style.height = "44px";

    // Собираем картинку, если прикреплена
    let imageFile = STATE.upload.solutionImage || null;

    // Получаем текст выбранной задачи
    const problemText =
        document.getElementById("problem_view").innerText;

    // Добавляем сообщение пользователя в чат и историю
    addUserMessage(solution, STATE.upload.attachedFile);
    STATE.chat.history.push({ role: "user", content: solution });
    STATE.upload.attachedFile = null; // сброс прикрепленной картинки

    // Показываем "AI думает..."
    const loadingDiv = document.createElement("div");
    loadingDiv.classList.add("message-wrapper", "assistant-wrapper");
    loadingDiv.innerHTML = `
        <div class="message assistant loading">
            <span class="typing">
                <span></span>
                <span></span>
                <span></span>
            </span>
        </div>
    `;
    document.getElementById("chat").appendChild(loadingDiv);

    const chat = document.getElementById("chat");

    chat.scrollTop = chat.scrollHeight;
    
    // Отправляем решение и картинку на backend через sendSolution
    
    clearImagePreview();

    try {

        const data = await sendSolution(problemText, solution, imageFile);

        // Сохраняем ответ AI в историю
        STATE.chat.history.push({ role: "assistant", content: data.message });

        // Показываем ответ AI
        addMessage(data.message, "assistant");

        if (data.attempt_saved === false) {
            console.warn("Attempt was not saved:", data);
        }

        if (typeof updateProgressTable === "function") {
            await updateProgressTable({ force: true });
        }

    } catch (error) {

        if (error.message !== "student_session_expired") {
            addMessage(
                "Не получилось отправить решение. Попробуй еще раз.",
                "assistant"
            );
        }

    } finally {

        // Убираем loading и возвращаем кнопку в рабочее состояние.
        loadingDiv.remove();
        button.disabled = false;
    }
}

function addUserMessage(text, attachedFile = null) {
    const chat = document.getElementById("chat");

    // Создаем контейнер для всего сообщения
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", "user");

    // Если есть текст, добавляем в отдельный блок
    if (text) {
        const textDiv = document.createElement("div");
        textDiv.classList.add("text-content");
        textDiv.textContent = text;
        messageDiv.appendChild(textDiv);
        typesetMath([textDiv]);
    }

    // Если есть прикреплённая картинка, добавляем в один bubble
    if (attachedFile) {
        if (
            attachedFile.type === "application/pdf"
            || attachedFile.name.toLowerCase().endsWith(".pdf")
            || isHeicSolutionFile(attachedFile)
        ) {
            const fileDiv = document.createElement("div");
            fileDiv.classList.add("message-file");
            fileDiv.textContent = attachedFile.name || "Файл";
            messageDiv.appendChild(fileDiv);
        } else {
            const img = document.createElement("img");
            img.src = URL.createObjectURL(attachedFile);
            img.classList.add("image-message");
            messageDiv.appendChild(img);
        }
    }

    chat.appendChild(messageDiv);

    // Автопрокрутка вниз
    chat.scrollTop = chat.scrollHeight;
}
