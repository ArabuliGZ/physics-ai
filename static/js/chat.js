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

    // Перерисовываем формулы

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
async function sendSolution(problemText, studentSolution, attachedFile = null) {
    let imageBase64 = null;

    if (attachedFile) {
        const reader = new FileReader();
        await new Promise((resolve) => {
            reader.onload = () => {
                imageBase64 = reader.result; // "data:image/png;base64,...."
                resolve();
            };
            reader.readAsDataURL(attachedFile);
        });
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
    let imageFile = ATTACHED_FILE || null;

    // Получаем текст задачи
    const mode = document.querySelector('input[name="mode"]:checked').value;
    let problemText = "";
    if (mode === "manual") {
        problemText = document.getElementById("problem").value;
    } else {
        problemText = document.getElementById("problem_view").innerText;
    }

    // Добавляем сообщение пользователя в чат и историю
    addMessage(solution, "user");
    
    if (ATTACHED_FILE) {
        const chat = document.getElementById("chat");

        const userImageDiv = document.createElement("div");
        userImageDiv.classList.add("message", "user"); // <- важно, чтобы был класс user
        userImageDiv.style.padding = "4px 8px"; 
        
        userImageDiv.innerHTML = `
            <img
                src="${URL.createObjectURL(ATTACHED_FILE)}"
                class="preview-image"
            >
        `;

        chat.appendChild(userImageDiv);

        // Очистить прикреплённый файл
        ATTACHED_FILE = null;
        document.getElementById("imagePreview").innerHTML = "";
        document.getElementById("imageInput").value = "";
    }
    
    HISTORY.push({ role: "user", content: solution });

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

    // Отправляем решение и картинку на backend через sendSolution
    const data = await sendSolution(problemText, solution, imageFile);

    // Сохраняем ответ AI в историю
    HISTORY.push({ role: "assistant", content: data.message });

    // Убираем loading
    loadingDiv.remove();

    // Показываем ответ AI
    addMessage(data.message, "assistant");

    button.disabled = false;
}