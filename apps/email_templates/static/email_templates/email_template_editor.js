(function () {
    "use strict";

    function initializeEditor(container) {
        const textarea = document.querySelector('[data-rich-text-source="email-template-html"]');
        const editor = container.querySelector("[data-editor-surface]");
        const preview = container.querySelector("[data-editor-preview]");
        const previewContent = container.querySelector("[data-editor-preview-content]");
        const previewToggle = container.querySelector("[data-editor-preview-toggle]");

        if (!textarea || !editor || !preview || !previewContent || !previewToggle) {
            return;
        }

        editor.innerHTML = textarea.value;

        function syncTextarea() {
            textarea.value = editor.innerHTML.trim();
            previewContent.innerHTML = textarea.value;
        }

        function focusEditor() {
            editor.focus();
        }

        container.querySelectorAll("[data-editor-command]").forEach(function (button) {
            button.addEventListener("click", function () {
                focusEditor();
                document.execCommand(button.dataset.editorCommand, false, null);
                syncTextarea();
            });
        });

        container.querySelectorAll("[data-editor-block]").forEach(function (button) {
            button.addEventListener("click", function () {
                focusEditor();
                document.execCommand("formatBlock", false, button.dataset.editorBlock);
                syncTextarea();
            });
        });

        const linkButton = container.querySelector("[data-editor-link]");
        if (linkButton) {
            linkButton.addEventListener("click", function () {
                const url = window.prompt("Link-Adresse eingeben (https://... oder {{ platzhalter }}):", "https://");
                if (!url) {
                    return;
                }
                focusEditor();
                document.execCommand("createLink", false, url);
                syncTextarea();
            });
        }

        document.querySelectorAll("[data-editor-placeholder]").forEach(function (button) {
            button.addEventListener("click", function () {
                focusEditor();
                document.execCommand("insertText", false, button.dataset.editorPlaceholder);
                syncTextarea();
            });
        });

        previewToggle.addEventListener("click", function () {
            syncTextarea();
            const previewIsHidden = preview.classList.contains("d-none");
            preview.classList.toggle("d-none", !previewIsHidden);
            editor.classList.toggle("d-none", previewIsHidden);
            previewToggle.textContent = previewIsHidden ? "Editor anzeigen" : "Vorschau anzeigen";
        });

        editor.addEventListener("input", syncTextarea);
        textarea.addEventListener("input", function () {
            editor.innerHTML = textarea.value;
            previewContent.innerHTML = textarea.value;
        });

        if (textarea.form) {
            textarea.form.addEventListener("submit", syncTextarea);
        }

        syncTextarea();
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-rich-text-editor]").forEach(initializeEditor);
    });
}());
