const API_BASE = "";

let registry = {};
let currentCategory = "";
let currentModel = "";
let currentTaskId = "";
let pollInterval = null;
let currentModelSchema = null;
let taskStartTime = null;
let elapsedInterval = null;

async function loadRegistry() {
    try {
        const res = await fetch(`${API_BASE}/api/registry`);
        registry = await res.json();
        populateCategories();
    } catch (e) {
        showToast("Failed to load model registry", "error");
    }
}

function populateCategories() {
    const select = document.getElementById("category-select");
    registry.categories.forEach(cat => {
        const opt = document.createElement("option");
        opt.value = cat.key;
        opt.textContent = cat.label;
        select.appendChild(opt);
    });
}

function populateModels(categoryKey) {
    const select = document.getElementById("model-select");
    select.innerHTML = '<option value="">Select a model...</option>';
    select.disabled = true;

    const category = registry.categories.find(c => c.key === categoryKey);
    if (!category) return;

    category.models.forEach(model => {
        const opt = document.createElement("option");
        opt.value = model.key;
        opt.textContent = model.label;
        select.appendChild(opt);
    });

    select.disabled = false;
}

async function loadModelSchema(categoryKey, modelKey) {
    try {
        const res = await fetch(`${API_BASE}/api/registry/${categoryKey}/${modelKey}`);
        currentModelSchema = await res.json();
        renderForm(currentModelSchema);
        const desc = document.getElementById("model-description");
        desc.innerHTML = `<p>${currentModelSchema.description}</p>`;
        if (currentModelSchema.key_capabilities) {
            desc.innerHTML += `<div class="model-capabilities"><h4>Key Capabilities</h4><ul>${currentModelSchema.key_capabilities.map(c => `<li>${c}</li>`).join("")}</ul></div>`;
        }
        if (currentModelSchema.use_cases) {
            desc.innerHTML += `<div class="model-use-cases"><h4>Use Cases</h4><ul>${currentModelSchema.use_cases.map(u => `<li>${u}</li>`).join("")}</ul></div>`;
        }
        desc.classList.add("visible");
    } catch (e) {
        showToast("Failed to load model schema", "error");
    }
}

function renderForm(schema) {
    const container = document.getElementById("form-container");
    container.innerHTML = "";

    const form = document.createElement("form");
    form.id = "generate-form";

    const fields = schema.fields;

    for (const [key, field] of Object.entries(fields)) {
        const group = document.createElement("div");
        group.className = "form-group";
        group.dataset.fieldKey = key;

        if (field.conditional_mode) {
            group.dataset.conditionalMode = field.conditional_mode;
        }

        if (field.type === "textarea") {
            group.innerHTML = `
                <label>${field.label}${field.required ? '<span class="required">*</span>' : ''}</label>
                <textarea name="${key}" placeholder="${field.placeholder || ''}" ${field.required ? 'required' : ''} ${field.max_length ? `maxlength="${field.max_length}"` : ''}></textarea>
                ${field.help ? `<div class="help-text">${field.help}</div>` : ''}
            `;
        } else if (field.type === "select") {
            const options = field.options.map(o =>
                `<option value="${o.value}" ${o.value == field.default ? 'selected' : ''}>${o.label}</option>`
            ).join("");
            group.innerHTML = `
                <label>${field.label}${field.required ? '<span class="required">*</span>' : ''}</label>
                <select name="${key}" ${field.required ? 'required' : ''}>${options}</select>
                ${field.help ? `<div class="help-text">${field.help}</div>` : ''}
            `;
        } else if (field.type === "file") {
            group.innerHTML = `
                <label>${field.label}${field.required ? '<span class="required">*</span>' : ''}</label>
                <input type="file" name="${key}" accept="${field.accept || '*'}" ${field.required ? 'required' : ''} class="standalone-file-input">
                <div class="file-upload-feedback" data-feedback="${key}"></div>
                ${field.help ? `<div class="help-text">${field.help}</div>` : ''}
            `;
        } else if (field.type === "url_or_file") {
            const urlPlaceholder = field.url_placeholder || "https://example.com/file";
            const fileAccept = field.accept || "*";
            const isVideo = field.accept && field.accept.startsWith("video");
            group.innerHTML = `
                <label>${field.label}${field.required ? '<span class="required">*</span>' : ''}</label>
                <div class="url-file-toggle" data-field="${key}">
                    <div class="toggle-tabs">
                        <button type="button" class="toggle-tab active" data-mode="url" data-target="${key}">URL</button>
                        <button type="button" class="toggle-tab" data-mode="file" data-target="${key}">Upload File</button>
                    </div>
                    <div class="toggle-content">
                        <div class="toggle-panel active" data-panel="url-${key}">
                            <div class="url-input-row">
                                <input type="url" name="${key}" placeholder="${urlPlaceholder}" ${field.required ? 'required' : ''} class="url-input">
                                <button type="button" class="url-verify-btn" data-target="${key}" title="Verify URL is reachable">
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                                    Verify
                                </button>
                            </div>
                            <div class="url-verify-result" data-result="${key}"></div>
                        </div>
                        <div class="toggle-panel" data-panel="file-${key}">
                            <div class="file-upload-area" data-field="${key}">
                                <input type="file" name="${key}" accept="${fileAccept}" class="file-input">
                                <div class="file-upload-feedback" data-feedback="${key}"></div>
                            </div>
                        </div>
                    </div>
                </div>
                ${field.help ? `<div class="help-text">${field.help}</div>` : ''}
            `;
        } else if (field.type === "range") {
            group.innerHTML = `
                <label>${field.label}${field.required ? '<span class="required">*</span>' : ''}</label>
                <input type="range" name="${key}" min="${field.min}" max="${field.max}" step="${field.step || 1}" value="${field.default || 0}">
                <div class="range-value"><span class="range-display">${field.default || 0}</span></div>
                ${field.help ? `<div class="help-text">${field.help}</div>` : ''}
            `;
            const range = group.querySelector('input[type="range"]');
            const display = group.querySelector(".range-display");
            range.addEventListener("input", () => {
                display.textContent = range.value;
            });
        } else if (field.type === "checkbox") {
            group.innerHTML = `
                <label class="checkbox-label">
                    <input type="checkbox" name="${key}" ${field.default ? 'checked' : ''}>
                    ${field.label}
                </label>
                ${field.help ? `<div class="help-text">${field.help}</div>` : ''}
            `;
        } else if (field.type === "url") {
            group.innerHTML = `
                <label>${field.label}${field.required ? '<span class="required">*</span>' : ''}</label>
                <input type="url" name="${key}" placeholder="${field.placeholder || ''}" ${field.required ? 'required' : ''}>
                ${field.help ? `<div class="help-text">${field.help}</div>` : ''}
            `;
        } else {
            group.innerHTML = `
                <label>${field.label}${field.required ? '<span class="required">*</span>' : ''}</label>
                <input type="${field.type}" name="${key}" value="${field.default || ''}" ${field.required ? 'required' : ''} ${field.min !== undefined ? `min="${field.min}"` : ''} ${field.max !== undefined ? `max="${field.max}"` : ''}>
                ${field.help ? `<div class="help-text">${field.help}</div>` : ''}
            `;
        }

        form.appendChild(group);
    }

    const actions = document.createElement("div");
    actions.className = "form-actions";
    actions.innerHTML = `
        <button type="submit" class="btn btn-primary" id="submit-btn">Generate</button>
    `;
    form.appendChild(actions);

    form.addEventListener("submit", handleSubmit);
    form.addEventListener("change", handleModeChange);
    container.appendChild(form);

    document.getElementById("result-container").style.display = "none";
    updateFieldVisibility();
    initUrlFileToggles(form);
    initStandaloneFileInputs(form);
}

function initUrlFileToggles(form) {
    form.querySelectorAll(".toggle-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            const target = tab.dataset.target;
            const mode = tab.dataset.mode;
            const toggle = tab.closest(".url-file-toggle");

            toggle.querySelectorAll(".toggle-tab").forEach(t => t.classList.remove("active"));
            toggle.querySelectorAll(".toggle-panel").forEach(p => p.classList.remove("active"));

            tab.classList.add("active");
            toggle.querySelector(`[data-panel="${mode}-${target}"]`).classList.add("active");

            const urlInput = toggle.querySelector(".url-input");
            const fileInput = toggle.querySelector(".file-input");
            if (mode === "url") {
                urlInput.required = true;
                fileInput.required = false;
                fileInput.value = "";
                clearFileFeedback(target);
            } else {
                fileInput.required = true;
                urlInput.required = false;
                urlInput.value = "";
                clearVerifyResult(target);
            }
        });
    });

    form.querySelectorAll(".url-verify-btn").forEach(btn => {
        btn.addEventListener("click", async () => {
            const target = btn.dataset.target;
            const toggle = btn.closest(".url-file-toggle");
            const urlInput = toggle.querySelector(".url-input");
            const resultDiv = toggle.querySelector(`.url-verify-result[data-result="${target}"]`);
            const url = urlInput.value.trim();

            if (!url) {
                showVerifyResult(resultDiv, "error", "Enter a URL first");
                return;
            }

            btn.classList.add("verifying");
            btn.innerHTML = `<svg class="verify-spinner" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Checking...`;

            try {
                const res = await fetch(`${API_BASE}/api/verify-url?url=${encodeURIComponent(url)}`);
                const data = await res.json();

                if (data.ok) {
                    let details = `HTTP ${data.status_code}`;
                    if (data.content_type) details += ` · ${data.content_type}`;
                    if (data.content_length && data.content_length !== "unknown") {
                        const bytes = parseInt(data.content_length);
                        if (bytes > 1048576) details += ` · ${(bytes / 1048576).toFixed(1)} MB`;
                        else if (bytes > 1024) details += ` · ${(bytes / 1024).toFixed(0)} KB`;
                        else details += ` · ${bytes} B`;
                    }
                    showVerifyResult(resultDiv, "success", details);
                } else {
                    showVerifyResult(resultDiv, "error", data.error || "URL not reachable");
                }
            } catch (err) {
                showVerifyResult(resultDiv, "error", "Verification failed");
            }

            btn.classList.remove("verifying");
            btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg> Verify`;
        });
    });

    form.querySelectorAll(".file-input").forEach(input => {
        input.addEventListener("change", () => {
            const toggle = input.closest(".url-file-toggle");
            const fieldKey = toggle.dataset.field;
            const feedback = toggle.querySelector(`.file-upload-feedback[data-feedback="${fieldKey}"]`);

            if (input.files && input.files.length > 0) {
                const file = input.files[0];
                const size = file.size;
                let sizeStr;
                if (size > 1048576) sizeStr = `${(size / 1048576).toFixed(1)} MB`;
                else if (size > 1024) sizeStr = `${(size / 1024).toFixed(0)} KB`;
                else sizeStr = `${size} B`;

                feedback.innerHTML = `
                    <div class="file-upload-success">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                        <span class="file-name">${escapeHtml(file.name)}</span>
                        <span class="file-size">${sizeStr}</span>
                    </div>
                `;

                fetch(`${API_BASE}/api/log-file-upload`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        field: fieldKey,
                        filename: file.name,
                        size: file.size,
                        content_type: file.type || "",
                    }),
                }).catch(() => {});
            } else {
                clearFileFeedback(fieldKey);
            }
        });
    });
}

function initStandaloneFileInputs(form) {
    form.querySelectorAll(".standalone-file-input").forEach(input => {
        input.addEventListener("change", () => {
            const fieldKey = input.name;
            const feedback = form.querySelector(`.file-upload-feedback[data-feedback="${fieldKey}"]`);

            if (input.files && input.files.length > 0) {
                const file = input.files[0];
                const size = file.size;
                let sizeStr;
                if (size > 1048576) sizeStr = `${(size / 1048576).toFixed(1)} MB`;
                else if (size > 1024) sizeStr = `${(size / 1024).toFixed(0)} KB`;
                else sizeStr = `${size} B`;

                if (feedback) {
                    feedback.innerHTML = `
                        <div class="file-upload-success">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                            <span class="file-name">${escapeHtml(file.name)}</span>
                            <span class="file-size">${sizeStr}</span>
                        </div>
                    `;
                }

                fetch(`${API_BASE}/api/log-file-upload`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        field: fieldKey,
                        filename: file.name,
                        size: file.size,
                        content_type: file.type || "",
                    }),
                }).catch(() => {});
            } else {
                if (feedback) feedback.innerHTML = "";
            }
        });
    });
}

function showVerifyResult(div, type, message) {
    div.className = `url-verify-result ${type}`;
    div.innerHTML = `<span class="verify-icon">${type === "success" ? "✓" : "✗"}</span><span class="verify-message">${escapeHtml(message)}</span>`;
}

function clearVerifyResult(fieldKey) {
    const div = document.querySelector(`.url-verify-result[data-result="${fieldKey}"]`);
    if (div) {
        div.className = "url-verify-result";
        div.innerHTML = "";
    }
}

function clearFileFeedback(fieldKey) {
    const feedback = document.querySelector(`.file-upload-feedback[data-feedback="${fieldKey}"]`);
    if (feedback) feedback.innerHTML = "";
}

function updateFieldVisibility() {
    const form = document.getElementById("generate-form");
    if (!form) return;

    const modeField = form.querySelector('[name="mode"]');
    const modeValue = modeField ? modeField.value : null;

    form.querySelectorAll(".form-group").forEach(group => {
        const condMode = group.dataset.conditionalMode;
        if (condMode && modeValue) {
            const allowedModes = condMode.split(",");
            group.style.display = allowedModes.includes(modeValue) ? "" : "none";
        }
    });
}

function handleModeChange(e) {
    if (e.target.name === "mode") {
        updateFieldVisibility();
    }
}

async function handleSubmit(e) {
    e.preventDefault();

    const form = e.target;
    const submitBtn = document.getElementById("submit-btn");
    submitBtn.disabled = true;
    submitBtn.textContent = "Submitting...";

    const formData = new FormData();
    formData.append("category", currentCategory);
    formData.append("model", currentModel);

    const params = {};
    const fileInputs = {};

    for (const input of form.elements) {
        if (!input.name || input.type === "submit") continue;

        const group = input.closest(".form-group");
        if (group && group.style.display === "none") continue;

        const toggle = input.closest(".url-file-toggle");
        if (toggle) {
            const activePanel = toggle.querySelector(".toggle-panel.active");
            const activeTab = toggle.querySelector(".toggle-tab.active");
            const mode = activeTab ? activeTab.dataset.mode : "url";

            const isInActivePanel = activePanel && activePanel.contains(input);
            if (!isInActivePanel) continue;

            if (mode === "url") {
                if (input.value) {
                    params[input.name] = input.value;
                }
            } else {
                if (input.files && input.files.length > 0) {
                    fileInputs[input.name] = input.files[0];
                }
            }
            continue;
        }

        if (input.type === "file") {
            if (input.files.length > 0) {
                fileInputs[input.name] = input.files[0];
            }
        } else if (input.type === "checkbox") {
            params[input.name] = input.checked;
        } else if (input.type === "range" || input.type === "number") {
            params[input.name] = parseFloat(input.value) || 0;
        } else {
            params[input.name] = input.value;
        }
    }

    formData.append("params", JSON.stringify(params));

    for (const [key, file] of Object.entries(fileInputs)) {
        let uploadKey = key;
        if (currentModel === "minimax-live" && key === "image_url") {
            uploadKey = "minimax_image_url";
        }
        formData.append(uploadKey, file);
    }

    try {
        const apiKey = getActiveApiKey();
        const headers = {};
        if (apiKey) headers["x-magnific-api-key"] = apiKey;

        const res = await fetch(`${API_BASE}/api/generate`, {
            method: "POST",
            headers,
            body: formData,
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Generation failed");
        }

        const result = await res.json();
        currentTaskId = result.task_id;
        showResult(result);
        addToTaskList(result);
        showToast("Task created successfully", "success");
        startPolling();
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Generate";
    }
}

function showResult(result) {
    const container = document.getElementById("result-container");
    const content = document.getElementById("result-content");
    const badge = document.getElementById("status-badge");
    const pollBtn = document.getElementById("poll-btn");
    const progressSection = document.getElementById("progress-section");

    container.style.display = "block";
    badge.textContent = result.status;
    badge.className = `status-badge ${result.status}`;
    content.innerHTML = `<p>Task ID: <code>${result.task_id}</code></p><p>Status: ${result.status}</p>`;
    pollBtn.style.display = result.status !== "COMPLETED" && result.status !== "FAILED" ? "inline-block" : "none";

    if (result.status === "IN_PROGRESS" || result.status === "CREATED") {
        progressSection.style.display = "flex";
        taskStartTime = Date.now();
        startElapsedTimer();
        updateProgressStatus(result.status);
    } else {
        progressSection.style.display = "none";
    }
}

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    const progressSection = document.getElementById("progress-section");
    progressSection.style.display = "flex";
    taskStartTime = Date.now();
    startElapsedTimer();
    pollInterval = setInterval(async () => {
        await checkTaskStatus();
    }, 3000);
}

async function checkTaskStatus() {
    if (!currentTaskId || !currentCategory || !currentModel) return;

    try {
        const apiKey = getActiveApiKey();
        const headers = {};
        if (apiKey) headers["x-magnific-api-key"] = apiKey;

        const res = await fetch(`${API_BASE}/api/tasks/${currentTaskId}?category=${currentCategory}&model=${currentModel}`, { headers });
        const result = await res.json();

        const badge = document.getElementById("status-badge");
        badge.textContent = result.status;
        badge.className = `status-badge ${result.status}`;

        updateProgressStatus(result.status, result);

        if (result.status === "COMPLETED") {
            clearInterval(pollInterval);
            stopElapsedTimer();
            hideProgressSection();
            renderCompleted(result);
        } else if (result.status === "FAILED") {
            clearInterval(pollInterval);
            stopElapsedTimer();
            hideProgressSection();
            document.getElementById("result-content").innerHTML = `<p class="error">Task failed</p>`;
            document.getElementById("poll-btn").style.display = "none";
            showToast("Task failed", "error");
        }
    } catch (e) {
        console.error("Poll error:", e);
    }
}

function formatElapsedTime(ms) {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    if (minutes > 0) {
        return `${minutes}m ${seconds}s`;
    }
    return `${seconds}s`;
}

function startElapsedTimer() {
    if (elapsedInterval) clearInterval(elapsedInterval);
    const elapsedEl = document.getElementById("elapsed-time");
    elapsedInterval = setInterval(() => {
        if (taskStartTime) {
            elapsedEl.textContent = formatElapsedTime(Date.now() - taskStartTime);
        }
    }, 1000);
}

function stopElapsedTimer() {
    if (elapsedInterval) {
        clearInterval(elapsedInterval);
        elapsedInterval = null;
    }
}

function updateProgressStatus(status, result) {
    const statusEl = document.getElementById("progress-status");
    const etaEl = document.getElementById("progress-eta");

    const statusMessages = {
        "CREATED": "Task created, waiting for processing...",
        "IN_PROGRESS": "Generating your content, please wait...",
        "QUEUED": "Task queued, waiting for available resources...",
        "PROCESSING": "Processing in progress...",
    };

    statusEl.textContent = statusMessages[status] || `Status: ${status}`;

    if (result && result.progress) {
        const progress = typeof result.progress === "number" ? result.progress : null;
        if (progress !== null && progress > 0) {
            statusEl.textContent = `Generating... ${Math.round(progress)}%`;
        }
    }

    if (taskStartTime) {
        const elapsed = Date.now() - taskStartTime;
        const elapsedSeconds = elapsed / 1000;
        if (elapsedSeconds > 30 && status === "IN_PROGRESS") {
            const estimatedTotal = elapsedSeconds * 1.5;
            const remaining = Math.max(0, estimatedTotal - elapsedSeconds);
            if (remaining > 10) {
                etaEl.textContent = `~${formatElapsedTime(remaining * 1000)} remaining`;
            } else {
                etaEl.textContent = "Completing soon...";
            }
        } else {
            etaEl.textContent = "";
        }
    }
}

function hideProgressSection() {
    document.getElementById("progress-section").style.display = "none";
}

function renderCompleted(result) {
    const content = document.getElementById("result-content");
    const urls = result.generated || [];

    if (urls.length === 0) {
        content.innerHTML = "<p>Task completed but no output found</p>";
        return;
    }

    let html = "";
    urls.forEach(url => {
        if (url.match(/\.(mp4|webm|mov)(\?.*)?$/i)) {
            html += `<video controls src="${url}"></video>`;
        } else if (url.match(/\.(mp3|wav|ogg|aac)(\?.*)?$/i)) {
            html += `<audio controls src="${url}"></audio>`;
        } else if (url.match(/^data:/)) {
            html += `<p class="prompt-text">${url}</p>`;
        } else {
            html += `<img src="${url}" alt="Generated content">`;
        }
    });

    content.innerHTML = html;
    document.getElementById("poll-btn").style.display = "none";
    showToast("Generation complete!", "success");
}

function addToTaskList(result) {
    const list = document.getElementById("task-list");
    const li = document.createElement("li");
    li.innerHTML = `
        <span>${currentModelSchema?.label || result.model} - ${result.task_id.slice(0, 8)}...</span>
        <span class="task-status ${result.status.toLowerCase()}"></span>
    `;
    li.addEventListener("click", () => {
        currentTaskId = result.task_id;
        showResult(result);
        if (result.status === "IN_PROGRESS" || result.status === "CREATED") {
            startPolling();
        } else if (result.status === "COMPLETED") {
            renderCompleted(result);
        }
    });
    list.insertBefore(li, list.firstChild);

    if (list.children.length > 20) {
        list.removeChild(list.lastChild);
    }
}

function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

document.getElementById("category-select").addEventListener("change", (e) => {
    currentCategory = e.target.value;
    currentModel = "";
    currentModelSchema = null;
    populateModels(currentCategory);
    document.getElementById("model-description").classList.remove("visible");
    document.getElementById("form-container").innerHTML = '<div class="placeholder"><p>Select a model to start generating</p></div>';
});

document.getElementById("model-select").addEventListener("change", async (e) => {
    currentModel = e.target.value;
    if (currentCategory && currentModel) {
        await loadModelSchema(currentCategory, currentModel);
    }
});

document.getElementById("poll-btn").addEventListener("click", checkTaskStatus);

document.getElementById("new-task-btn").addEventListener("click", () => {
    document.getElementById("result-container").style.display = "none";
    if (pollInterval) clearInterval(pollInterval);
    if (elapsedInterval) clearInterval(elapsedInterval);
    currentTaskId = "";
    taskStartTime = null;
    hideProgressSection();
});

document.getElementById("settings-btn").addEventListener("click", openSettings);
document.getElementById("settings-close-btn").addEventListener("click", closeSettings);
document.getElementById("settings-overlay").addEventListener("click", closeSettings);

let lastLogId = 0;
let logPollInterval = null;
let logPanelVisible = true;

function startLogPolling() {
    if (logPollInterval) clearInterval(logPollInterval);
    fetchLogs();
    logPollInterval = setInterval(fetchLogs, 1500);
}

async function fetchLogs() {
    try {
        const res = await fetch(`${API_BASE}/api/logs?last_id=${lastLogId}`);
        const data = await res.json();
        if (data.entries && data.entries.length > 0) {
            appendLogEntries(data.entries);
            lastLogId = data.entries[data.entries.length - 1].id;
        }
    } catch (e) {
        console.error("Log fetch error:", e);
    }
}

function appendLogEntries(entries) {
    const container = document.getElementById("log-entries");
    const countEl = document.getElementById("log-count");
    const wasAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 50;

    entries.forEach(entry => {
        const div = document.createElement("div");
        div.className = "log-entry";
        const time = new Date(entry.timestamp).toLocaleTimeString();
        div.innerHTML = `
            <span class="log-entry-time">${time}</span>
            <span class="log-entry-level ${entry.level}">${entry.level}</span>
            <span class="log-entry-category">[${entry.category}]</span>
            <span class="log-entry-message">${escapeHtml(entry.message)}</span>
        `;
        container.appendChild(div);
    });

    const totalEntries = container.children.length;
    countEl.textContent = totalEntries;

    if (wasAtBottom) {
        container.scrollTop = container.scrollHeight;
    }
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

document.getElementById("log-toggle-btn").addEventListener("click", () => {
    logPanelVisible = !logPanelVisible;
    const panel = document.getElementById("log-panel");
    const chevron = document.querySelector(".log-chevron");
    panel.classList.toggle("hidden-panel", !logPanelVisible);
    if (logPanelVisible) {
        const container = document.getElementById("log-entries");
        container.scrollTop = container.scrollHeight;
    }
});

document.getElementById("log-clear-btn").addEventListener("click", async () => {
    try {
        await fetch(`${API_BASE}/api/logs/clear`, { method: "POST" });
    } catch (e) {}
    document.getElementById("log-entries").innerHTML = "";
    document.getElementById("log-count").textContent = "0";
    lastLogId = 0;
});

document.addEventListener("DOMContentLoaded", () => {
    loadRegistry();
    startLogPolling();
});

const MAX_API_KEYS = 5;
const SETTINGS_STORAGE_KEY = "magnific_api_keys";

function loadApiKeys() {
    try {
        const stored = localStorage.getItem(SETTINGS_STORAGE_KEY);
        if (stored) {
            return JSON.parse(stored);
        }
    } catch (e) {}
    return [
        { key: "", enabled: false, validated: false, label: "" },
        { key: "", enabled: false, validated: false, label: "" },
        { key: "", enabled: false, validated: false, label: "" },
        { key: "", enabled: false, validated: false, label: "" },
        { key: "", enabled: false, validated: false, label: "" },
    ];
}

function saveApiKeys(keys) {
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(keys));
}

function getActiveApiKey() {
    const keys = loadApiKeys();
    for (const slot of keys) {
        if (slot.enabled && slot.key) {
            return slot.key;
        }
    }
    return null;
}

function renderApiKeys() {
    const keys = loadApiKeys();
    const container = document.getElementById("api-keys-container");
    container.innerHTML = "";

    keys.forEach((slot, i) => {
        const div = document.createElement("div");
        div.className = `api-key-slot${slot.enabled && slot.key ? " active-slot" : ""}`;

        let statusText = "Empty";
        let statusClass = "";
        if (slot.key) {
            if (slot.validationResult) {
                const sc = slot.validationResult.status_code;
                const body = slot.validationResult.body || "";
                let displayBody = body;
                try {
                    const parsed = JSON.parse(body);
                    displayBody = parsed.message || parsed.detail || parsed.error || body;
                } catch(e) {}
                statusText = displayBody || `HTTP ${sc}`;
                if (sc >= 200 && sc < 300) {
                    statusClass = "validated";
                } else if (sc === 400) {
                    statusClass = "validated";
                } else if (sc === 401 || sc === 403) {
                    statusClass = "error";
                } else if (sc >= 500) {
                    statusClass = "warning";
                } else {
                    statusClass = "error";
                }
            } else {
                statusText = "Not validated";
            }
        }

        const activeBadge = slot.enabled && slot.key ? '<span class="active-badge">● ACTIVE</span>' : '';

        let btnText = "Validate";
        let btnTitle = "";
        let btnExtraClass = "";
        if (slot.validationResult) {
            const sc = slot.validationResult.status_code;
            btnText = String(sc || "?");
            const body = slot.validationResult.body || "";
            let displayBody = body;
            try {
                const parsed = JSON.parse(body);
                displayBody = parsed.message || parsed.detail || parsed.error || body;
            } catch(e) {}
            btnTitle = displayBody;
            if (sc >= 200 && sc < 300 || sc === 400) {
                btnExtraClass = " valid";
            } else {
                btnExtraClass = " invalid";
            }
        }

        div.innerHTML = `
            <div class="api-key-slot-header">
                <span class="api-key-slot-label">Key ${i + 1} ${activeBadge}</span>
            </div>
            <div class="api-key-input-row">
                <input type="password" class="api-key-input" data-index="${i}" value="${slot.key}" placeholder="sk-...">
                <button class="api-key-validate-btn${btnExtraClass}" data-index="${i}" ${!slot.key ? 'disabled' : ''} title="${btnTitle}">${btnText}</button>
            </div>
            <div class="api-key-toggle-row">
                <span class="api-key-status ${statusClass}" title="${btnTitle}">${statusText}</span>
                <label class="toggle-switch">
                    <input type="checkbox" data-index="${i}" ${slot.enabled ? 'checked' : ''} ${!slot.key ? 'disabled' : ''}>
                    <span class="toggle-slider"></span>
                </label>
            </div>
        `;

        container.appendChild(div);
    });

    container.querySelectorAll(".api-key-input").forEach(input => {
        input.addEventListener("input", (e) => {
            const idx = parseInt(e.target.dataset.index);
            const keys = loadApiKeys();
            keys[idx].key = e.target.value;
            keys[idx].validationResult = null;
            keys[idx].label = "";
            if (!e.target.value) {
                keys[idx].enabled = false;
            }
            saveApiKeys(keys);
            renderApiKeys();
        });
    });

    container.querySelectorAll(".api-key-validate-btn").forEach(btn => {
        btn.addEventListener("click", async (e) => {
            const idx = parseInt(e.target.dataset.index);
            const keys = loadApiKeys();
            const apiKey = keys[idx].key.trim();

            if (!apiKey) return;

            btn.classList.add("validating");
            btn.textContent = "...";

            try {
                const res = await fetch(`${API_BASE}/api/validate-key`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ api_key: apiKey }),
                });

                const data = await res.json();
                keys[idx].validationResult = data;
            } catch (err) {
                keys[idx].validationResult = { status_code: 0, body: err.message };
            }

            saveApiKeys(keys);
            renderApiKeys();
        });
    });

    container.querySelectorAll(".toggle-switch input").forEach(toggle => {
        toggle.addEventListener("change", (e) => {
            const idx = parseInt(e.target.dataset.index);
            const keys = loadApiKeys();

            if (e.target.checked) {
                keys.forEach((k, j) => {
                    if (j !== idx) k.enabled = false;
                });
                keys[idx].enabled = true;
            } else {
                keys[idx].enabled = false;
            }

            saveApiKeys(keys);
            renderApiKeys();
        });
    });
}

function openSettings() {
    document.getElementById("settings-overlay").classList.add("active");
    document.getElementById("settings-panel").classList.add("active");
    renderApiKeys();
}

function closeSettings() {
    document.getElementById("settings-overlay").classList.remove("active");
    document.getElementById("settings-panel").classList.remove("active");
}
