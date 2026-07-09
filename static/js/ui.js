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

const MAX_SOLUTION_IMAGE_BYTES = 10 * 1024 * 1024;
const ALLOWED_SOLUTION_FILE_TYPES = new Set([
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
]);
const ALLOWED_SOLUTION_FILE_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".pdf",
];

imageInput.addEventListener(
    "change",
    previewImage
);

function showImageUploadError(message) {

    const preview =
        document.getElementById(
            "imagePreview"
        );

    preview.innerHTML = "";

    const error =
        document.createElement("div");

    error.classList.add(
        "upload-error"
    );

    error.textContent = message;

    preview.appendChild(error);
}

function isAllowedSolutionFile(file) {

    const fileName = file.name.toLowerCase();

    return ALLOWED_SOLUTION_FILE_TYPES.has(file.type)
        || ALLOWED_SOLUTION_FILE_EXTENSIONS.some(extension =>
            fileName.endsWith(extension)
        );
}

function previewImage(event) {

    const file =
        event.target.files[0];

    if (!file)
        return;

    if (!isAllowedSolutionFile(file)) {

        resetSolutionImageMemory();
        showImageUploadError(
            "Можно прикрепить только JPG, PNG, WEBP или PDF."
        );

        return;
    }

    if (file.size > MAX_SOLUTION_IMAGE_BYTES) {

        resetSolutionImageMemory();
        showImageUploadError(
            "Файл слишком большой. Максимальный размер — 10 МБ."
        );

        return;
    }

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

    if (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) {

        const fileBadge =
            document.createElement("div");

        fileBadge.classList.add(
            "preview-file"
        );

        fileBadge.textContent =
            file.name || "PDF";

        wrapper.appendChild(fileBadge);

    } else {

        const img =
            document.createElement("img");

        img.src =
            URL.createObjectURL(file);

        img.classList.add(
            "preview-image"
        );

        wrapper.appendChild(img);
    }

    const remove =
        document.createElement("button");

    remove.classList.add(
        "remove-image"
    );

    remove.innerHTML = "×";

    remove.onclick = removeImage;

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

function resetSolutionImageMemory() {

    STATE.upload.attachedFile = null;
    STATE.upload.solutionImage = null;

    clearImagePreview();
}

function removeImage() {

    resetSolutionImageMemory();
}
