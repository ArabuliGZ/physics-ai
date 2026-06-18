// ==================================
// ===== ЕДИНОЕ СОСТОЯНИЕ ПРИЛОЖЕНИЯ =====
// ==================================

// Этот файл подключается первым, чтобы все остальные JS-модули могли
// безопасно читать и обновлять STATE.
const STATE = {

    tasks: [],

    groupsById: {},

    student: {
        current: null
    },

    selected: {
        classId: null,
        chapter: null,
        topic: null,
        number: null,
        task: null,
        taskMediaUrl: null
    },

    chat: {
        history: [],
        hintLevel: 0
    },

    upload: {
        attachedFile: null,
        solutionImage: null
    }
};
