const state = {
    currentMode: "webcam",
    imageResultData: "",
    webcam: {
        active: false,
        stream: null,
        sessionId: null,
        loopHandle: null,
        recording: false,
        mediaRecorder: null,
        recordedChunks: [],
        fpsFrames: 0,
        fpsStart: 0,
    },
};

const refs = {
    modelSelect: document.getElementById("model-select"),
    modelCount: document.getElementById("model-count"),
    refreshModels: document.getElementById("refresh-models"),
    confInput: document.getElementById("conf-input"),
    confValue: document.getElementById("conf-value"),
    iouInput: document.getElementById("iou-input"),
    iouValue: document.getElementById("iou-value"),
    resolutionSelect: document.getElementById("resolution-select"),
    classFilter: document.getElementById("class-filter"),
    csvToggle: document.getElementById("csv-toggle"),
    statusText: document.getElementById("status-text"),
    currentModeLabel: document.getElementById("current-mode-label"),
    webcamFps: document.getElementById("webcam-fps"),
    lastExportLink: document.getElementById("last-export-link"),
    modeButtons: Array.from(document.querySelectorAll(".mode-button")),
    modePanels: Array.from(document.querySelectorAll(".mode-panel")),
    webcamVideo: document.getElementById("webcam-video"),
    webcamCanvas: document.getElementById("webcam-canvas"),
    scratchCanvas: document.getElementById("scratch-canvas"),
    startWebcam: document.getElementById("start-webcam"),
    stopWebcam: document.getElementById("stop-webcam"),
    snapshotWebcam: document.getElementById("snapshot-webcam"),
    recordWebcam: document.getElementById("record-webcam"),
    liveSummary: document.getElementById("live-summary"),
    liveSummaryTotal: document.getElementById("live-summary-total"),
    imageFile: document.getElementById("image-file"),
    imagePreview: document.getElementById("image-preview"),
    imageResult: document.getElementById("image-result"),
    runImage: document.getElementById("run-image"),
    saveImageSnapshot: document.getElementById("save-image-snapshot"),
    imageSummary: document.getElementById("image-summary"),
    imageSummaryTotal: document.getElementById("image-summary-total"),
    videoFile: document.getElementById("video-file"),
    videoResult: document.getElementById("video-result"),
    runVideo: document.getElementById("run-video"),
    videoSummary: document.getElementById("video-summary"),
    videoSummaryTotal: document.getElementById("video-summary-total"),
};

function getSettings() {
    return {
        model_name: refs.modelSelect.value,
        conf: refs.confInput.value,
        iou: refs.iouInput.value,
        resolution: refs.resolutionSelect.value,
        class_filter: refs.classFilter.value.trim(),
        log_csv: refs.csvToggle.checked,
    };
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const payload = await response.json();
    if (!response.ok || payload.ok === false) {
        throw new Error(payload.error || "Request failed");
    }
    return payload;
}

function setStatus(message) {
    refs.statusText.textContent = message;
}

function setLastExport(url, label) {
    if (!url) {
        refs.lastExportLink.textContent = "ยังไม่มีไฟล์";
        refs.lastExportLink.href = "#";
        return;
    }
    refs.lastExportLink.textContent = label || "เปิดไฟล์ล่าสุด";
    refs.lastExportLink.href = url;
}

function setMode(mode) {
    state.currentMode = mode;
    refs.currentModeLabel.textContent = {
        webcam: "Live Camera",
        image: "Image Probe",
        video: "Video Forge",
    }[mode];

    refs.modeButtons.forEach((button) => {
        button.classList.toggle("active", button.dataset.mode === mode);
    });

    refs.modePanels.forEach((panel) => {
        panel.classList.toggle("active", panel.id === `mode-${mode}`);
    });
}

function renderSummary(container, totalLabel, summary, type) {
    if (!summary) {
        container.innerHTML = '<p class="placeholder">No summary available.</p>';
        totalLabel.textContent = "-";
        return;
    }

    if (type === "video") {
        totalLabel.textContent = `${summary.frames_processed} frames`;
        const classLines = (summary.by_class || [])
            .map((item) => `<div class="summary-line"><span>${item.name}</span><strong>${item.count}</strong></div>`)
            .join("");

        container.innerHTML = `
            <div class="summary-meta">
                <div>Frames processed: <strong>${summary.frames_processed}</strong></div>
                <div>Total detections: <strong>${summary.detections_total}</strong></div>
                <div>Peak objects in frame: <strong>${summary.peak_objects_in_frame}</strong></div>
            </div>
            ${classLines || '<p class="placeholder">ไม่พบวัตถุในวิดีโอนี้</p>'}
        `;
        return;
    }

    totalLabel.textContent = `${summary.total_objects} objects`;
    const classLines = (summary.by_class || [])
        .map((item) => `<div class="summary-line"><span>${item.name}</span><strong>${item.count}</strong></div>`)
        .join("");

    container.innerHTML = classLines || '<p class="placeholder">ไม่พบวัตถุในเฟรมนี้</p>';
}

async function loadModels() {
    setStatus("Loading models...");
    const payload = await fetchJson("/api/models");
    refs.modelSelect.innerHTML = payload.models
        .map((model) => `<option value="${model}">${model}</option>`)
        .join("");
    refs.modelSelect.value = payload.default_model;
    refs.modelCount.textContent = String(payload.models.length);
    setStatus("Ready");
}

function syncSliderLabels() {
    refs.confValue.textContent = Number(refs.confInput.value).toFixed(2);
    refs.iouValue.textContent = Number(refs.iouInput.value).toFixed(2);
}

function previewImageFile() {
    const [file] = refs.imageFile.files;
    if (!file) {
        return;
    }
    const fileUrl = URL.createObjectURL(file);
    refs.imagePreview.src = fileUrl;
}

async function runImageDetection() {
    const [file] = refs.imageFile.files;
    if (!file) {
        setStatus("Please choose an image first.");
        return;
    }

    setStatus("Running image detection...");
    const formData = new FormData();
    formData.append("file", file);
    formData.append("settings", JSON.stringify(getSettings()));
    formData.append("log_csv", String(refs.csvToggle.checked));

    const payload = await fetchJson("/api/detect/image", {
        method: "POST",
        body: formData,
    });

    state.imageResultData = payload.image_data;
    refs.imageResult.src = payload.image_data;
    refs.saveImageSnapshot.disabled = false;
    renderSummary(refs.imageSummary, refs.imageSummaryTotal, payload.summary, "image");
    if (payload.csv_url) {
        setLastExport(payload.csv_url, "CSV log");
    }
    setStatus("Image detection completed.");
}

async function saveImageSnapshot() {
    if (!state.imageResultData) {
        return;
    }
    setStatus("Saving snapshot...");
    const payload = await fetchJson("/api/save-snapshot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_data: state.imageResultData }),
    });
    setLastExport(payload.file_url, payload.filename);
    setStatus("Snapshot saved.");
}

async function runVideoProcessing() {
    const [file] = refs.videoFile.files;
    if (!file) {
        setStatus("Please choose a video first.");
        return;
    }

    setStatus("Processing video... this can take a while.");
    refs.runVideo.disabled = true;

    try {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("settings", JSON.stringify(getSettings()));
        formData.append("log_csv", String(refs.csvToggle.checked));

        const payload = await fetchJson("/api/process/video", {
            method: "POST",
            body: formData,
        });

        refs.videoResult.src = payload.processed_video_url;
        renderSummary(refs.videoSummary, refs.videoSummaryTotal, payload.summary, "video");
        setLastExport(payload.processed_video_url, "Processed video");
        if (payload.csv_url) {
            setLastExport(payload.csv_url, "CSV log");
        }
        setStatus("Video processing completed.");
    } finally {
        refs.runVideo.disabled = false;
    }
}

function drawDataUrlToCanvas(dataUrl, canvas) {
    return new Promise((resolve, reject) => {
        const image = new Image();
        image.onload = () => {
            if (canvas.width !== image.width || canvas.height !== image.height) {
                canvas.width = image.width;
                canvas.height = image.height;
            }
            const context = canvas.getContext("2d");
            context.clearRect(0, 0, canvas.width, canvas.height);
            context.drawImage(image, 0, 0, image.width, image.height);
            resolve();
        };
        image.onerror = reject;
        image.src = dataUrl;
    });
}

async function startWebcamDetection() {
    if (state.webcam.active) {
        return;
    }

    setStatus("Requesting camera access...");
    const stream = await navigator.mediaDevices.getUserMedia({
        video: getPreferredCameraConstraints(),
        audio: false,
    });

    state.webcam.stream = stream;
    state.webcam.active = true;
    state.webcam.fpsFrames = 0;
    state.webcam.fpsStart = performance.now();
    refs.webcamVideo.srcObject = stream;

    refs.startWebcam.disabled = true;
    refs.stopWebcam.disabled = false;
    refs.snapshotWebcam.disabled = false;
    refs.recordWebcam.disabled = false;

    setStatus("Live detection running.");
    scheduleWebcamLoop();
}

async function stopWebcamDetection() {
    state.webcam.active = false;

    if (state.webcam.loopHandle) {
        clearTimeout(state.webcam.loopHandle);
        state.webcam.loopHandle = null;
    }

    if (state.webcam.stream) {
        state.webcam.stream.getTracks().forEach((track) => track.stop());
        state.webcam.stream = null;
    }

    if (state.webcam.recording) {
        await toggleRecording();
    }

    if (state.webcam.sessionId) {
        try {
            const payload = await fetchJson("/api/session/end", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: state.webcam.sessionId }),
            });
            if (payload.csv_url) {
                setLastExport(payload.csv_url, "Live CSV log");
            }
        } catch (error) {
            console.error(error);
        }
        state.webcam.sessionId = null;
    }

    refs.startWebcam.disabled = false;
    refs.stopWebcam.disabled = true;
    refs.snapshotWebcam.disabled = true;
    refs.recordWebcam.disabled = true;
    refs.recordWebcam.textContent = "Start Recording";
    refs.webcamFps.textContent = "-";
    setStatus("Live detection stopped.");
}

function scheduleWebcamLoop() {
    if (!state.webcam.active) {
        return;
    }
    state.webcam.loopHandle = window.setTimeout(runWebcamFrame, 0);
}

function getLiveCaptureSize(videoWidth, videoHeight) {
    const selectedResolution = refs.resolutionSelect.value;
    if (selectedResolution === "Native") {
        return { width: videoWidth, height: videoHeight };
    }

    const maxEdge = Number(selectedResolution);
    if (!Number.isFinite(maxEdge) || maxEdge <= 0) {
        return { width: videoWidth, height: videoHeight };
    }

    const scale = Math.min(1, maxEdge / Math.max(videoWidth, videoHeight));
    return {
        width: Math.max(2, Math.round(videoWidth * scale)),
        height: Math.max(2, Math.round(videoHeight * scale)),
    };
}

function canvasToJpegBlob(canvas, quality) {
    return new Promise((resolve, reject) => {
        canvas.toBlob((blob) => {
            if (!blob) {
                reject(new Error("Could not encode webcam frame."));
                return;
            }
            resolve(blob);
        }, "image/jpeg", quality);
    });
}

function getPreferredCameraConstraints() {
    const selectedResolution = refs.resolutionSelect.value;
    const preferredEdge = selectedResolution === "Native"
        ? 1280
        : Math.max(320, Number(selectedResolution) || 640);

    return {
        width: { ideal: preferredEdge },
        height: { ideal: Math.round(preferredEdge * 9 / 16) },
    };
}

async function runWebcamFrame() {
    if (!state.webcam.active || refs.webcamVideo.readyState < 2) {
        scheduleWebcamLoop();
        return;
    }

    const scratch = refs.scratchCanvas;
    const { width, height } = getLiveCaptureSize(refs.webcamVideo.videoWidth, refs.webcamVideo.videoHeight);
    scratch.width = width;
    scratch.height = height;
    const scratchContext = scratch.getContext("2d");
    scratchContext.drawImage(refs.webcamVideo, 0, 0, scratch.width, scratch.height);
    const frameBlob = await canvasToJpegBlob(scratch, 0.72);

    try {
        const formData = new FormData();
        formData.append("file", frameBlob, "frame.jpg");
        formData.append("settings", JSON.stringify(getSettings()));
        if (state.webcam.sessionId) {
            formData.append("session_id", state.webcam.sessionId);
        }

        const payload = await fetchJson("/api/detect/frame", {
            method: "POST",
            body: formData,
        });

        state.webcam.sessionId = payload.session_id || state.webcam.sessionId;
        await drawDataUrlToCanvas(payload.image_data, refs.webcamCanvas);
        renderSummary(refs.liveSummary, refs.liveSummaryTotal, payload.summary, "webcam");
        updateWebcamFps();

        if (payload.csv_url && refs.csvToggle.checked) {
            setLastExport(payload.csv_url, "Live CSV log");
        }
    } catch (error) {
        setStatus(error.message);
    }

    scheduleWebcamLoop();
}

function updateWebcamFps() {
    state.webcam.fpsFrames += 1;
    const now = performance.now();
    const elapsed = now - state.webcam.fpsStart;
    if (elapsed < 1000) {
        return;
    }
    const fps = (state.webcam.fpsFrames * 1000) / elapsed;
    refs.webcamFps.textContent = `${fps.toFixed(1)} fps`;
    state.webcam.fpsFrames = 0;
    state.webcam.fpsStart = now;
}

async function saveWebcamSnapshot() {
    if (!refs.webcamCanvas.width || !refs.webcamCanvas.height) {
        return;
    }

    setStatus("Saving webcam snapshot...");
    const dataUrl = refs.webcamCanvas.toDataURL("image/jpeg", 0.9);
    const payload = await fetchJson("/api/save-snapshot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_data: dataUrl }),
    });
    setLastExport(payload.file_url, payload.filename);
    setStatus("Snapshot saved.");
}

function pickRecordingMimeType() {
    const candidates = [
        "video/webm;codecs=vp9",
        "video/webm;codecs=vp8",
        "video/webm",
    ];
    return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

async function toggleRecording() {
    if (!state.webcam.recording) {
        if (!refs.webcamCanvas.width || !refs.webcamCanvas.height) {
            return;
        }

        const captureStream = refs.webcamCanvas.captureStream(12);
        const mimeType = pickRecordingMimeType();
        state.webcam.recordedChunks = [];
        state.webcam.mediaRecorder = mimeType
            ? new MediaRecorder(captureStream, { mimeType })
            : new MediaRecorder(captureStream);

        state.webcam.mediaRecorder.ondataavailable = (event) => {
            if (event.data && event.data.size > 0) {
                state.webcam.recordedChunks.push(event.data);
            }
        };

        state.webcam.mediaRecorder.onstop = async () => {
            const blob = new Blob(state.webcam.recordedChunks, {
                type: state.webcam.mediaRecorder.mimeType || "video/webm",
            });
            const formData = new FormData();
            formData.append("file", blob, "live_recording.webm");
            const payload = await fetchJson("/api/save-recording", {
                method: "POST",
                body: formData,
            });
            setLastExport(payload.file_url, payload.filename);
            setStatus("Recording saved.");
        };

        state.webcam.mediaRecorder.start();
        state.webcam.recording = true;
        refs.recordWebcam.textContent = "Stop Recording";
        setStatus("Recording live canvas...");
        return;
    }

    await new Promise((resolve) => {
        state.webcam.mediaRecorder.addEventListener("stop", resolve, { once: true });
        state.webcam.mediaRecorder.stop();
    });
    state.webcam.recording = false;
    refs.recordWebcam.textContent = "Start Recording";
}

function bindEvents() {
    refs.modeButtons.forEach((button) => {
        button.addEventListener("click", () => setMode(button.dataset.mode));
    });

    refs.refreshModels.addEventListener("click", loadModels);
    refs.confInput.addEventListener("input", syncSliderLabels);
    refs.iouInput.addEventListener("input", syncSliderLabels);
    refs.imageFile.addEventListener("change", previewImageFile);
    refs.runImage.addEventListener("click", () => runImageDetection().catch((error) => setStatus(error.message)));
    refs.saveImageSnapshot.addEventListener("click", () => saveImageSnapshot().catch((error) => setStatus(error.message)));
    refs.runVideo.addEventListener("click", () => runVideoProcessing().catch((error) => setStatus(error.message)));
    refs.startWebcam.addEventListener("click", () => startWebcamDetection().catch((error) => setStatus(error.message)));
    refs.stopWebcam.addEventListener("click", () => stopWebcamDetection().catch((error) => setStatus(error.message)));
    refs.snapshotWebcam.addEventListener("click", () => saveWebcamSnapshot().catch((error) => setStatus(error.message)));
    refs.recordWebcam.addEventListener("click", () => toggleRecording().catch((error) => setStatus(error.message)));
    window.addEventListener("beforeunload", () => {
        if (state.webcam.stream) {
            state.webcam.stream.getTracks().forEach((track) => track.stop());
        }
    });
}

async function init() {
    bindEvents();
    syncSliderLabels();
    await loadModels();
}

init().catch((error) => setStatus(error.message));
