const searchInput = document.getElementById("search");
const resultsDiv = document.getElementById("results");
const urlForm = document.getElementById("url-form");
const fileInput = document.getElementById("file-input");
const statusEl = document.getElementById("status");
const loading = document.getElementById("loading");

const LIMIT = 20;
let offset = 0;
let loadingMore = false;
let allLoaded = false;

function renderTags(tags, itemId) {
    const tagList = tags
        ? tags
              .split(",")
              .map((t) => t.trim())
              .filter(Boolean)
        : [];
    const pills = tagList.map((t) => `<span class="tag">${t}</span>`).join("");
    return `<div class="tags" data-id="${itemId}">
        ${pills}
        <button class="add-tag" onclick="editTags(${itemId}, '${tags.replace(/'/g, "\\'")}')">+ tag</button>
    </div>`;
}

function editTags(id, currentTags) {
    const tagsDiv = document.querySelector(`.tags[data-id="${id}"]`);
    tagsDiv.innerHTML = `<input class="tag-input" type="text" value="${currentTags}" placeholder="comma separated tags" onkeydown="if(event.key==='Enter'){saveTags(${id},this.value);event.preventDefault()}" onblur="saveTags(${id},this.value)">`;
    tagsDiv.querySelector("input").focus();
}

function saveTags(id, tags) {
    const formData = new FormData();
    formData.append("tags", tags);
    fetch(`/api/tags/${id}`, { method: "POST", body: formData })
        .then((r) => r.json())
        .then(() => doSearch(false));
}

function copyLink(btn, path) {
    const url = new URL(path, window.location.href).href;
    navigator.clipboard.writeText(url).then(() => {
        const original = btn.textContent;
        btn.textContent = "copied!";
        setTimeout(() => (btn.textContent = original), 1200);
    });
}

function deleteMedia(id) {
    fetch(`/api/media/${id}`, { method: "DELETE" })
        .then((r) => r.json())
        .then(() => doSearch(false));
}

function renderMedia(item) {
    if (item.media_type === "image") {
        return `<img src="/videos/${item.filename}" loading="lazy">`;
    }
    return `<video controls preload="metadata"><source src="/videos/${item.filename}" type="video/mp4"></video>`;
}

function renderItems(items, append) {
    if (!append) resultsDiv.innerHTML = "";
    if (items.length === 0 && !append && searchInput.value) {
        resultsDiv.innerHTML = "<p>No results.</p>";
        return;
    }
    if (items.length < LIMIT) allLoaded = true;
    let anyTranscribing = false;
    items.forEach((item) => {
        const card = document.createElement("div");
        card.className = "card";
        const transcriptStatus = item.transcript === null ? `<div class="transcribing">transcribing...</div>` : "";
        if (item.transcript === null) anyTranscribing = true;
        card.innerHTML = `
            <button class="delete-btn" onclick="deleteMedia(${item.id})">x</button>
            ${renderTags(item.tags, item.id)}
            ${renderMedia(item)}
            ${transcriptStatus}
            ${item.url ? `<div class="source"><a href="${item.url}" target="_blank" rel="noopener">${item.url}</a></div>` : ""}
            <a class="download-btn" href="/videos/${item.filename}" download>download</a>
            <button class="copy-btn" onclick="copyLink(this, '/videos/${item.filename}')">copy link</button>
        `;
        resultsDiv.appendChild(card);
    });
    if (anyTranscribing) setTimeout(() => doSearch(false), 5000);
}

function doSearch(append) {
    if (!append) {
        offset = 0;
        allLoaded = false;
    }
    loadingMore = true;
    if (append) loading.style.display = "block";
    fetch(`/api/search?q=${encodeURIComponent(searchInput.value)}&offset=${offset}&limit=${LIMIT}`)
        .then((r) => r.json())
        .then((items) => {
            renderItems(items, append);
            offset += items.length;
            loadingMore = false;
            loading.style.display = "none";
        });
}

async function uploadFiles(files) {
    for (let i = 0; i < files.length; i++) {
        statusEl.textContent = `uploading ${i + 1} of ${files.length}...`;
        const formData = new FormData();
        formData.append("file", files[i]);
        await fetch("/api/upload", { method: "POST", body: formData }).then((r) => r.json());
    }
    statusEl.textContent = "";
    doSearch(false);
}

searchInput.addEventListener("input", () => doSearch(false));
searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        doSearch(false);
    }
});

window.addEventListener("scroll", () => {
    if (loadingMore || allLoaded) return;
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 200) {
        doSearch(true);
    }
});

urlForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const formData = new FormData(urlForm);
    statusEl.textContent = "processing...";
    urlForm.querySelectorAll("input").forEach((i) => (i.disabled = true));

    fetch("/api/add", { method: "POST", body: formData })
        .then((r) => {
            if (!r.ok) throw new Error(`server error ${r.status}`);
            return r.json();
        })
        .then(() => {
            statusEl.textContent = "done!";
            setTimeout(() => { statusEl.textContent = ""; }, 1500);
            urlForm.reset();
            urlForm.querySelectorAll("input").forEach((i) => (i.disabled = false));
            doSearch(false);
        })
        .catch((err) => {
            statusEl.textContent = `error: ${err.message}`;
            urlForm.querySelectorAll("input").forEach((i) => (i.disabled = false));
            setTimeout(() => { statusEl.textContent = ""; }, 5000);
        });
});

fileInput.addEventListener("change", () => {
    uploadFiles(fileInput.files);
    fileInput.value = "";
});

doSearch(false);
