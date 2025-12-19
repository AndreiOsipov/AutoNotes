const API_URL = "http://127.0.0.1:8000/transcribe";
let currentSession = null;
let currentMode = "text";
let history = [];

// Initialize
document.addEventListener("DOMContentLoaded", () => {
    loadHistory();
    document.getElementById("videoInput").addEventListener("change", handleFileSelect);
});

function setMode(mode) {
    currentMode = mode;
    document.querySelectorAll(".mode-btn").forEach(btn => btn.classList.remove("active"));
    event.target.classList.add("active");
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;

    currentSession = {
    id: Date.now(),
    fileName: file.name,
    timestamp: new Date().toLocaleString("ru-RU"),
    subtitles: null,
    status: "processing"
    };

    showResults();
    uploadAndTranscribe(file);
}

async function uploadAndTranscribe(file) {
    const formData = new FormData();
    formData.append("video", file);

    const statusDiv = document.getElementById("statusMessage");
    statusDiv.innerHTML = "";

    try {
    const response = await fetch(API_URL, {
        method: "POST",
        body: formData
    });

    if (!response.ok) {
        throw new Error(`Ошибка сервера: ${response.status}`);
    }

    const data = await response.json();
    const subtitles = data.subtitles || "Субтитры не найдены";

    currentSession.subtitles = subtitles;
    currentSession.status = "completed";

    displaySubtitles(subtitles);
    saveToHistory();
    statusDiv.innerHTML = '<div class="success">✓ Субтитры успешно сгенерированы</div>';
    } catch (error) {
    currentSession.status = "error";
    const errorMsg = error.message || "Ошибка обработки видео";
    statusDiv.innerHTML = `<div class="error">✗ ${errorMsg}</div>`;
    document.getElementById("subtitlesDisplay").innerHTML = 
        `<div style="color: var(--color-text-secondary);">Ошибка: ${errorMsg}</div>`;
    }
}

function displaySubtitles(subtitles) {
    document.getElementById("subtitlesDisplay").textContent = subtitles;
    document.getElementById("resultTitle").textContent = currentSession.fileName;
    document.getElementById("resultMeta").textContent = 
    `Обработано: ${currentSession.timestamp}`;
}

function showResults() {
    document.getElementById("uploadZone").style.display = "none";
    document.getElementById("resultsArea").classList.add("active");
}

function saveToHistory() {
    history.unshift({
    id: currentSession.id,
    fileName: currentSession.fileName,
    timestamp: currentSession.timestamp,
    subtitles: currentSession.subtitles
    });
    history = history.slice(0, 50); // Максимум 50 записей
    localStorage.setItem("subtitleHistory", JSON.stringify(history));
    renderHistory();
}

function loadHistory() {
    const stored = localStorage.getItem("subtitleHistory");
    history = stored ? JSON.parse(stored) : [];
    renderHistory();
}

function renderHistory() {
    const container = document.getElementById("historyContainer");
    if (history.length === 0) {
    container.innerHTML = '<p style="color: var(--color-text-secondary); font-size: 12px; text-align: center; margin-top: 20px;">История пуста</p>';
    return;
    }

    container.innerHTML = history.map(item => `
    <div class="history-item ${currentSession?.id === item.id ? 'active' : ''}" onclick="loadHistoryItem(${item.id})">
        <div class="history-item-name">${escapeHtml(item.fileName)}</div>
        <div class="history-item-time">${item.timestamp}</div>
    </div>
    `).join("");
}

function loadHistoryItem(id) {
    const item = history.find(h => h.id === id);
    if (!item) return;

    currentSession = item;
    displaySubtitles(item.subtitles);
    showResults();
    renderHistory();
}

function copyToClipboard() {
    if (!currentSession?.subtitles) return;
    navigator.clipboard.writeText(currentSession.subtitles);
    alert("Скопировано в буфер обмена!");
}

function downloadSubtitles() {
    if (!currentSession?.subtitles) return;

    const srtContent = convertToSRT(currentSession.subtitles);
    const blob = new Blob([srtContent], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = currentSession.fileName.replace(/\.[^.]+$/, ".srt");
    link.click();
    URL.revokeObjectURL(url);
}

function convertToSRT(text) {
    // Простое преобразование в формат SRT
    const lines = text.split("\n").filter(l => l.trim());
    let srtContent = "";
    let counter = 1;

    for (let i = 0; i < lines.length; i += 2) {
    if (i + 1 < lines.length) {
        srtContent += `${counter}\n`;
        srtContent += `00:00:${String(counter).padStart(2, '0')},000 --> 00:00:${String(counter + 1).padStart(2, '0')},000\n`;
        srtContent += `${lines[i]}\n\n`;
        counter++;
    }
    }
    return srtContent;
}

function newSession() {
    currentSession = null;
    document.getElementById("uploadZone").style.display = "block";
    document.getElementById("resultsArea").classList.remove("active");
    document.getElementById("videoInput").value = "";
    document.getElementById("statusMessage").innerHTML = "";
    renderHistory();
}

function escapeHtml(text) {
    const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
    return text.replace(/[&<>"']/g, m => map[m]);
}
