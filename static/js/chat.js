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

    div.innerHTML = text;

    chat.appendChild(div);

    MathJax.typesetClear([div]);
    MathJax.typesetPromise([div]);

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
async function compressImage(file) {

    return new Promise((resolve) => {

        const img = new Image();

        img.onload = () => {

            // ===== RESIZE =====

            const MAX_SIZE = 1080;

            let width = img.width;
            let height = img.height;

            if (width > height) {

                if (width > MAX_SIZE) {

                    height *= MAX_SIZE / width;
                    width = MAX_SIZE;
                }

            } else {

                if (height > MAX_SIZE) {

                    width *= MAX_SIZE / height;
                    height = MAX_SIZE;
                }
            }

            // ===== CANVAS =====

            const canvas = document.createElement("canvas");

            canvas.width = width;
            canvas.height = height;

            const ctx = canvas.getContext("2d");

            ctx.drawImage(img, 0, 0, width, height);

            // ===== JPEG EXPORT =====

            const compressedBase64 =
                canvas.toDataURL(
                    "image/jpeg",
                    0.75
                );

            resolve(compressedBase64);
        };

        img.src = URL.createObjectURL(file);
    });
}

async function sendSolution(problemText, studentSolution, attachedFile = null) {
    let imageBase64 = null;

    if (attachedFile) {

        imageBase64 =
            await compressImage(attachedFile);
    }

    const payload = {
        problem: problemText,
        solution: studentSolution,
        history: HISTORY,
        hint_level: HINT_LEVEL,
        problem_image_base64: imageBase64
    };

    const response = await fetch("/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    const data = await response.json();
    return data;
}


async function checkSolution() {
    const button = document.querySelector(".send-button");
    if (button.disabled) return;
    button.disabled = true;

    const solutionInput = document.getElementById("solution");
    const solution = solutionInput.value.trim();
    solutionInput.value = "";
    solutionInput.style.height = "44px";

    // Собираем картинку, если прикреплена
    let imageFile = CURRENT_SOLUTION_IMAGE || null;

    // Получаем текст задачи
    const mode = document.querySelector('input[name="mode"]:checked').value;
    let problemText = "";
    if (mode === "manual") {
        problemText = document.getElementById("problem").value;
    } else {
        problemText = document.getElementById("problem_view").innerText;
    }

    // Добавляем сообщение пользователя в чат и историю
    addUserMessage(solution, ATTACHED_FILE);
    HISTORY.push({ role: "user", content: solution });
    ATTACHED_FILE = null; // сброс прикрепленной картинки

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
    
    removeImage();
    const data = await sendSolution(problemText, solution, imageFile);
    
    

    // Сохраняем ответ AI в историю
    HISTORY.push({ role: "assistant", content: data.message });

    // Убираем loading
    loadingDiv.remove();

    // Показываем ответ AI
    addMessage(data.message, "assistant");

    button.disabled = false;
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
        textDiv.innerHTML = text;
        messageDiv.appendChild(textDiv);
        MathJax.typesetPromise([textDiv]);
    }

    // Если есть прикреплённая картинка, добавляем в один bubble
    if (attachedFile) {
        const img = document.createElement("img");
        img.src = URL.createObjectURL(attachedFile);
        img.classList.add("image-message");
        messageDiv.appendChild(img);
    }

    chat.appendChild(messageDiv);

    // Автопрокрутка вниз
    chat.scrollTop = chat.scrollHeight;
}