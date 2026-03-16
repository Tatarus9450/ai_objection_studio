const state = {
    webcam: {
        active: false,
        stream: null,
        loopHandle: null,
        scratchContext: null,
        fpsFrames: 0,
        fpsStart: 0,
        lastSummaryKey: "",
    },
};

const PRICE_TABLE = {
    choco_pie: 5,
    euro_cake: 5,
    frit_c: 5,
    jolly_cola: 12,
    yumyum: 4,
};

const refs = {
    confInput: document.getElementById("conf-input"),
    confValue: document.getElementById("conf-value"),
    iouInput: document.getElementById("iou-input"),
    iouValue: document.getElementById("iou-value"),
    resolutionSelect: document.getElementById("resolution-select"),
    classFilter: document.getElementById("class-filter"),
    statusText: document.getElementById("status-text"),
    webcamFps: document.getElementById("webcam-fps"),
    webcamVideo: document.getElementById("webcam-video"),
    webcamCanvas: document.getElementById("webcam-canvas"),
    scratchCanvas: document.getElementById("scratch-canvas"),
    startWebcam: document.getElementById("start-webcam"),
    stopWebcam: document.getElementById("stop-webcam"),
    liveSummary: document.getElementById("live-summary"),
    liveSummaryTotal: document.getElementById("live-summary-total"),
    pricingSummary: document.getElementById("pricing-summary"),
    pricingTotalItems: document.getElementById("pricing-total-items"),
    pricingTotalAmount: document.getElementById("pricing-total-amount"),
};

function getSettings() {
    return {
        conf: refs.confInput.value,
        iou: refs.iouInput.value,
        resolution: refs.resolutionSelect.value,
        class_filter: refs.classFilter.value.trim(),
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

async function fetchFrameDetection(formData) {
    const response = await fetch("/api/detect/frame", {
        method: "POST",
        headers: {
            "X-Response-Mode": "jpeg",
        },
        body: formData,
    });

    if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.error || "Request failed");
    }

    const summaryHeader = response.headers.get("X-Live-Summary");
    const perfHeader = response.headers.get("X-Frame-Perf");

    return {
        blob: await response.blob(),
        summary: summaryHeader ? JSON.parse(decodeURIComponent(summaryHeader)) : null,
        perf: perfHeader ? JSON.parse(decodeURIComponent(perfHeader)) : null,
    };
}

function setStatus(message) {
    refs.statusText.textContent = message;
}

function syncSliderLabels() {
    refs.confValue.textContent = Number(refs.confInput.value).toFixed(2);
    refs.iouValue.textContent = Number(refs.iouInput.value).toFixed(2);
}

function renderSummary(summary) {
    if (!summary) {
        refs.liveSummary.innerHTML = '<p class="placeholder">ยังไม่มีผลสรุปจากการตรวจจับ</p>';
        refs.liveSummaryTotal.textContent = "-";
        state.webcam.lastSummaryKey = "";
        renderPricingSummary(null);
        return;
    }

    const summaryKey = JSON.stringify([summary.total_objects, summary.by_class || []]);
    if (summaryKey === state.webcam.lastSummaryKey) {
        return;
    }

    state.webcam.lastSummaryKey = summaryKey;
    refs.liveSummaryTotal.textContent = `${summary.total_objects} รายการ`;
    const classLines = (summary.by_class || [])
        .map((item) => `<div class="summary-line"><span>${item.name}</span><strong>${item.count}</strong></div>`)
        .join("");

    refs.liveSummary.innerHTML = classLines || `<p class="placeholder">${summary.detail_text}</p>`;
    renderPricingSummary(summary);
}

function renderPricingSummary(summary) {
    if (!summary || !Array.isArray(summary.by_class) || summary.by_class.length === 0) {
        refs.pricingSummary.innerHTML = '<p class="placeholder">รอผลตรวจจับเพื่อคำนวณจำนวนสินค้าและยอดรวม</p>';
        refs.pricingTotalItems.textContent = "0 ชิ้น";
        refs.pricingTotalAmount.textContent = "0 บาท";
        return;
    }

    const pricedItems = summary.by_class
        .map((item) => {
            const unitPrice = PRICE_TABLE[item.name] ?? 0;
            return {
                ...item,
                unitPrice,
                subtotal: unitPrice * item.count,
            };
        })
        .filter((item) => item.count > 0);

    const totalItems = Number.isFinite(summary.total_objects)
        ? summary.total_objects
        : summary.by_class.reduce((sum, item) => sum + item.count, 0);
    const totalAmount = pricedItems.reduce((sum, item) => sum + item.subtotal, 0);

    const lines = pricedItems
        .map((item) => `
            <div class="pricing-line">
                <span>${item.name} × ${item.count}</span>
                <strong>${item.subtotal} บาท</strong>
            </div>
        `)
        .join("");

    refs.pricingSummary.innerHTML = lines || '<p class="placeholder">ยังไม่มีสินค้าที่อยู่ในตารางราคา</p>';
    refs.pricingTotalItems.textContent = `${totalItems} ชิ้น`;
    refs.pricingTotalAmount.textContent = `${totalAmount} บาท`;
}

async function drawBlobToCanvas(blob, canvas) {
    const context = canvas.getContext("2d");
    if ("createImageBitmap" in window) {
        const bitmap = await createImageBitmap(blob);
        try {
            if (canvas.width !== bitmap.width || canvas.height !== bitmap.height) {
                canvas.width = bitmap.width;
                canvas.height = bitmap.height;
            }
            context.clearRect(0, 0, canvas.width, canvas.height);
            context.drawImage(bitmap, 0, 0, bitmap.width, bitmap.height);
        } finally {
            bitmap.close();
        }
        return;
    }

    await new Promise((resolve, reject) => {
        const image = new Image();
        image.onload = () => {
            if (canvas.width !== image.width || canvas.height !== image.height) {
                canvas.width = image.width;
                canvas.height = image.height;
            }
            context.clearRect(0, 0, canvas.width, canvas.height);
            context.drawImage(image, 0, 0, image.width, image.height);
            URL.revokeObjectURL(image.src);
            resolve();
        };
        image.onerror = reject;
        image.src = URL.createObjectURL(blob);
    });
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
    const video = {
        frameRate: { ideal: 30, max: 30 },
    };

    if (selectedResolution === "Native") {
        video.width = { ideal: 1280 };
        video.height = { ideal: 720 };
        return video;
    }

    const preferredEdge = Math.max(320, Number(selectedResolution) || 640);
    video.width = { ideal: preferredEdge };
    video.height = {
        ideal: Math.round(preferredEdge * 9 / 16),
    };
    return video;
}

function scheduleWebcamLoop() {
    if (!state.webcam.active) {
        return;
    }
    state.webcam.loopHandle = window.setTimeout(runWebcamFrame, 0);
}

async function startWebcamDetection() {
    if (state.webcam.active) {
        return;
    }

    setStatus("กำลังขอสิทธิ์เข้าถึงกล้อง...");
    const stream = await navigator.mediaDevices.getUserMedia({
        video: getPreferredCameraConstraints(),
        audio: false,
    });

    state.webcam.stream = stream;
    state.webcam.active = true;
    state.webcam.lastSummaryKey = "";
    state.webcam.fpsFrames = 0;
    state.webcam.fpsStart = performance.now();
    refs.webcamVideo.srcObject = stream;

    refs.startWebcam.disabled = true;
    refs.stopWebcam.disabled = false;

    setStatus("กำลังตรวจจับขนมผ่านกล้อง");
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

    refs.startWebcam.disabled = false;
    refs.stopWebcam.disabled = true;
    refs.webcamFps.textContent = "-";
    state.webcam.lastSummaryKey = "";
    setStatus("หยุดการตรวจจับแล้ว");
}

async function runWebcamFrame() {
    if (!state.webcam.active || refs.webcamVideo.readyState < 2) {
        scheduleWebcamLoop();
        return;
    }

    const scratch = refs.scratchCanvas;
    const { width, height } = getLiveCaptureSize(refs.webcamVideo.videoWidth, refs.webcamVideo.videoHeight);
    if (scratch.width !== width || scratch.height !== height) {
        scratch.width = width;
        scratch.height = height;
        state.webcam.scratchContext = scratch.getContext("2d", { alpha: false });
    }
    const scratchContext = state.webcam.scratchContext || scratch.getContext("2d", { alpha: false });
    state.webcam.scratchContext = scratchContext;
    scratchContext.drawImage(refs.webcamVideo, 0, 0, scratch.width, scratch.height);
    const frameBlob = await canvasToJpegBlob(scratch, 0.62);

    try {
        const formData = new FormData();
        formData.append("file", frameBlob, "frame.jpg");
        formData.append("settings", JSON.stringify(getSettings()));

        const payload = await fetchFrameDetection(formData);

        await drawBlobToCanvas(payload.blob, refs.webcamCanvas);
        renderSummary(payload.summary);
        updateWebcamFps();
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

function bindEvents() {
    refs.confInput.addEventListener("input", syncSliderLabels);
    refs.iouInput.addEventListener("input", syncSliderLabels);
    refs.startWebcam.addEventListener("click", () => startWebcamDetection().catch((error) => setStatus(error.message)));
    refs.stopWebcam.addEventListener("click", () => stopWebcamDetection().catch((error) => setStatus(error.message)));

    window.addEventListener("beforeunload", () => {
        if (state.webcam.stream) {
            state.webcam.stream.getTracks().forEach((track) => track.stop());
        }
    });
}

async function init() {
    bindEvents();
    syncSliderLabels();
    renderSummary({
        total_objects: 0,
        by_class: [],
        detail_text: "เริ่มกล้องเพื่อดูผลการตรวจจับขนมแบบสด",
    });
    setStatus("พร้อมใช้งาน");
}

init().catch((error) => setStatus(error.message));
