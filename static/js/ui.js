function autoResize(textarea) {

    textarea.style.height = "44px";

    textarea.style.height =
        textarea.scrollHeight + "px";
}


// ==================================
// ===== ENTER ДЛЯ ОТПРАВКИ =====
// ==================================

function handleEnter(event) {

    if (
        event.key === "Enter" &&
        !event.shiftKey
    ) {

        event.preventDefault();

        checkSolution();
    }
}


const imageInput =
    document.getElementById(
        "imageInput"
    );

imageInput.addEventListener(
    "change",
    previewImage
);

function previewImage(event) {

    const file =
        event.target.files[0];

    if (!file)
        return;

    STATE.upload.attachedFile = file;
    STATE.upload.solutionImage = file;

    const preview =
        document.getElementById(
            "imagePreview"
        );

    preview.innerHTML = "";

    const wrapper =
        document.createElement("div");

    wrapper.classList.add(
        "preview-wrapper"
    );

    const img =
        document.createElement("img");

    img.src =
        URL.createObjectURL(file);

    img.classList.add(
        "preview-image"
    );

    const remove =
        document.createElement("button");

    remove.classList.add(
        "remove-image"
    );

    remove.innerHTML = "×";

    remove.onclick = removeImage;

    wrapper.appendChild(img);
    wrapper.appendChild(remove);

    preview.appendChild(wrapper);
}

function clearImagePreview() {

    STATE.upload.attachedFile = null;

    document.getElementById(
        "imagePreview"
    ).innerHTML = "";

    document.getElementById(
        "imageInput"
    ).value = "";
}

function removeImage() {

    clearImagePreview();
}
