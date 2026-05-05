(function () {
    "use strict";

    const PLACEHOLDER_PATTERN = /{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}/g;

    function getPreviewContext() {
        const contextElement = document.getElementById("email-template-preview-context");
        if (!contextElement) {
            return {};
        }
        try {
            return JSON.parse(contextElement.textContent);
        } catch (error) {
            return {};
        }
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function renderTemplate(content, context, forHtml) {
        return (content || "").replace(PLACEHOLDER_PATTERN, function (match, placeholder) {
            if (!Object.prototype.hasOwnProperty.call(context, placeholder)) {
                return match;
            }
            const value = String(context[placeholder]);
            if (!forHtml) {
                return value;
            }
            return escapeHtml(value).replace(/\n/g, "<br>");
        });
    }

    function initializeEditor(container) {
        const textarea = document.querySelector('[data-rich-text-source="email-template-html"]');
        const subjectInput = document.querySelector('[name="subject"]');
        const editor = container.querySelector("[data-editor-surface]");
        const preview = document.querySelector("[data-editor-preview]");
        const previewSubject = document.querySelector("[data-editor-preview-subject]");
        const previewContent = document.querySelector("[data-editor-preview-content]");
        const previewContext = getPreviewContext();

        if (!textarea || !editor) {
            return;
        }

        editor.innerHTML = textarea.value;

        function syncPreview() {
            if (previewSubject && subjectInput) {
                previewSubject.textContent = renderTemplate(
                    subjectInput.value,
                    previewContext,
                    false
                );
            }
            if (previewContent) {
                previewContent.innerHTML = renderTemplate(
                    textarea.value,
                    previewContext,
                    true
                );
            }
        }

        function syncTextarea() {
            textarea.value = editor.innerHTML.trim();
            syncPreview();
        }

        function focusEditor() {
            editor.focus();
        }

        function insertLineBreak() {
            focusEditor();
            if (!document.execCommand("insertLineBreak", false, null)) {
                document.execCommand("insertHTML", false, "<br>");
            }
            syncTextarea();
        }

        container.querySelectorAll("[data-editor-command]").forEach(function (button) {
            button.addEventListener("mousedown", function (event) {
                event.preventDefault();
            });
            button.addEventListener("click", function () {
                focusEditor();
                document.execCommand(button.dataset.editorCommand, false, null);
                syncTextarea();
            });
        });

        container.querySelectorAll("[data-editor-block]").forEach(function (button) {
            button.addEventListener("mousedown", function (event) {
                event.preventDefault();
            });
            button.addEventListener("click", function () {
                focusEditor();
                document.execCommand("formatBlock", false, button.dataset.editorBlock);
                syncTextarea();
            });
        });

        const linkButton = container.querySelector("[data-editor-link]");
        if (linkButton) {
            linkButton.addEventListener("mousedown", function (event) {
                event.preventDefault();
            });
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
            button.addEventListener("mousedown", function (event) {
                event.preventDefault();
            });
            button.addEventListener("click", function () {
                focusEditor();
                document.execCommand("insertText", false, button.dataset.editorPlaceholder);
                syncTextarea();
            });
        });

        editor.addEventListener("keydown", function (event) {
            if (event.key === "Enter" && event.shiftKey) {
                event.preventDefault();
                insertLineBreak();
            }
        });

        editor.addEventListener("input", syncTextarea);
        textarea.addEventListener("input", function () {
            editor.innerHTML = textarea.value;
            syncPreview();
        });
        if (subjectInput) {
            subjectInput.addEventListener("input", syncPreview);
        }

        if (textarea.form) {
            textarea.form.addEventListener("submit", syncTextarea);
        }

        syncTextarea();
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-rich-text-editor]").forEach(initializeEditor);
    });
}());
