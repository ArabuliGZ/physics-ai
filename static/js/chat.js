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

async function checkSolution() {
    
    const button =
        document.querySelector(".send-button");

    if (button.disabled)
        return;

    button.disabled = true;

    const chat =
        document.getElementById("chat");

    // Был ли пользователь внизу
    // ДО любых изменений чата

    const shouldAutoScroll =

        chat.scrollHeight
        - chat.scrollTop
        - chat.clientHeight

        < 100;

    // Получаем условие

    let problem = "";

    const mode =
        document.querySelector(
            'input[name="mode"]:checked'
        ).value;

    if (mode === "manual") {

        problem =
            document.getElementById("problem").value;

    } else {

        problem =
            document.getElementById("problem_view").innerText;
    }

    // Получаем решение ученика

    const solutionInput =
        document.getElementById("solution");

    const solution =
        solutionInput.value;

    solutionInput.value = "";

    solutionInput.style.height = "44px";

    // Добавляем решение в историю

    HISTORY.push({
        role: "user",
        content: solution
    });

    // Сообщение пользователя

    addMessage(
        solution,
        "user"
    );

    // Loading сообщение

    const loadingDiv = document.createElement("div");

    loadingDiv.classList.add(
        "message",
        "assistant",
        "loading"
    );

    loadingDiv.innerHTML = `
        <span class="typing">
            <span></span>
            <span></span>
            <span></span>
        </span>
    `;

    chat.appendChild(loadingDiv);

    // Скроллим только если
    // пользователь был внизу

    if (shouldAutoScroll) {

        requestAnimationFrame(() => {

            chat.scrollTop =
                chat.scrollHeight;
        });
    }

    // Отправляем запрос на backend

    const response = await fetch(
        "http://127.0.0.1:8000/check",

        {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({

                problem: problem,
                solution: solution,
                history: HISTORY
            })
        }
    );

    // Получаем JSON ответ

    const data = await response.json();

    HISTORY.push({
        role: "assistant",
        content: data.message
    });

    // Удаляем loading сообщение

    loadingDiv.remove();

    // Ответ AI

    addMessage(
        data.message,
        "assistant"
    );

    button.disabled = false;
}