const form = document.getElementById("download-form");
const urlInput = document.getElementById("url-input");
const formatSelect = document.getElementById("format-select");
const qualitySelect = document.getElementById("quality-select");
const infoBtn = document.getElementById("info-btn");
const downloadBtn = document.getElementById("download-btn");

const infoCard = document.getElementById("info-card");
const infoThumbnail = document.getElementById("info-thumbnail");
const infoTitle = document.getElementById("info-title");
const infoMeta = document.getElementById("info-meta");

const jobCard = document.getElementById("job-card");
const jobStatusText = document.getElementById("job-status-text");
const progressBar = document.getElementById("progress-bar");
const downloadLink = document.getElementById("download-link");

const errorText = document.getElementById("error-text");

let pollTimer = null;

function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return "";
  seconds = Math.round(seconds);
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const pad = (n) => String(n).padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

function showError(message) {
  errorText.textContent = message;
  errorText.classList.remove("hidden");
}

function clearError() {
  errorText.textContent = "";
  errorText.classList.add("hidden");
}

async function fetchJson(url, options) {
  const resp = await fetch(url, options);
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(data.detail || `Request failed (${resp.status})`);
  }
  return data;
}

infoBtn.addEventListener("click", async () => {
  clearError();
  const url = urlInput.value.trim();
  if (!url) return;

  infoBtn.disabled = true;
  try {
    const info = await fetchJson("/api/info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    infoTitle.textContent = info.title || "Untitled";
    const parts = [];
    if (info.uploader) parts.push(info.uploader);
    if (info.duration) parts.push(formatDuration(info.duration));
    infoMeta.textContent = parts.join(" · ");
    if (info.thumbnail) {
      infoThumbnail.src = info.thumbnail;
      infoThumbnail.classList.remove("hidden");
    } else {
      infoThumbnail.classList.add("hidden");
    }
    infoCard.classList.remove("hidden");
  } catch (err) {
    showError(err.message);
  } finally {
    infoBtn.disabled = false;
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  const url = urlInput.value.trim();
  if (!url) return;

  if (pollTimer) clearInterval(pollTimer);
  downloadLink.classList.add("hidden");
  jobCard.classList.remove("hidden");
  jobStatusText.textContent = "Starting...";
  progressBar.style.width = "0%";
  downloadBtn.disabled = true;

  try {
    const { job_id: jobId } = await fetchJson("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url,
        format: formatSelect.value,
        quality: qualitySelect.value,
      }),
    });
    pollTimer = setInterval(() => pollJob(jobId), 1000);
  } catch (err) {
    showError(err.message);
    downloadBtn.disabled = false;
  }
});

async function pollJob(jobId) {
  try {
    const job = await fetchJson(`/api/jobs/${jobId}`);
    progressBar.style.width = `${job.progress}%`;

    if (job.status === "completed") {
      jobStatusText.textContent = `Done: ${job.title || "download"}`;
      downloadLink.href = `/api/jobs/${jobId}/file`;
      downloadLink.textContent = `Save ${job.filename}`;
      downloadLink.classList.remove("hidden");
      clearInterval(pollTimer);
      downloadBtn.disabled = false;
    } else if (job.status === "failed") {
      jobStatusText.textContent = "Failed";
      showError(job.error || "Download failed");
      clearInterval(pollTimer);
      downloadBtn.disabled = false;
    } else {
      jobStatusText.textContent =
        job.status === "downloading" ? `Downloading... ${job.progress}%` : "Pending...";
    }
  } catch (err) {
    showError(err.message);
    clearInterval(pollTimer);
    downloadBtn.disabled = false;
  }
}
