const el = (id) => document.getElementById(id);

const state = {
  mode: "realtime",
  audioFile: null,
  liveTimer: null,
};

const transcriptInput = el("transcriptInput");
const highlighted = el("highlighted");
const redacted = el("redacted");
const soap = el("soap");
const status = el("status");
const audioInput = el("audioInput");
const audioPreview = el("audioPreview");

const modeRealtime = el("modeRealtime");
const modeAccurate = el("modeAccurate");

function setMode(mode) {
  state.mode = mode;
  modeRealtime.classList.toggle("active", mode === "realtime");
  modeAccurate.classList.toggle("active", mode === "accurate");
  runLiveGuard();
}

function renderEntities(entities) {
  const container = el("entityChips");
  container.innerHTML = "";
  for (const row of entities || []) {
    const chip = document.createElement("div");
    chip.className = "entity-chip";
    chip.innerHTML = `
      <span class="chip-type">${row.entity}</span>
      <span class="chip-val">${row.value}</span>
      <span class="chip-conf">${row.confidence}</span>
    `;
    container.appendChild(chip);
  }
}

async function runLiveGuard() {
  const text = transcriptInput.value || "";
  if (!text.trim()) {
    highlighted.innerHTML = "";
    redacted.textContent = "";
    renderEntities([]);
    status.textContent = "Waiting for transcript input...";
    return;
  }
  const res = await fetch("/api/live-guard", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, mode: state.mode }),
  });
  const data = await res.json();
  highlighted.innerHTML = data.highlighted || "";
  redacted.textContent = data.redacted || "";
  renderEntities(data.entities || []);
  status.textContent = data.status || "";
}

async function runPipeline() {
  const form = new FormData();
  form.append("mode", state.mode);
  form.append("transcript", transcriptInput.value || "");
  form.append("summarize", el("includeSoap").checked ? "true" : "false");
  if (state.audioFile) form.append("audio", state.audioFile);

  status.textContent = "Running pipeline...";
  const res = await fetch("/api/full-pipeline", { method: "POST", body: form });
  const data = await res.json();
  transcriptInput.value = data.original || transcriptInput.value;
  highlighted.innerHTML = data.highlighted || "";
  redacted.textContent = data.redacted || "";
  soap.textContent = data.soap || "";
  renderEntities(data.entities || []);
  status.textContent = data.status || "Completed.";
}

function debounceLive() {
  clearTimeout(state.liveTimer);
  state.liveTimer = setTimeout(runLiveGuard, 350);
}

async function setPreviewFromUrl(url, btnElement) {
  const originalText = btnElement ? btnElement.textContent : "LOAD SAMPLE AUDIO";
  if (btnElement) {
    btnElement.textContent = "LOADING...";
    btnElement.disabled = true;
    btnElement.classList.remove("pulse-btn"); // Stop pulsing once clicked
  }
  
  try {
    audioPreview.src = url;
    const response = await fetch(url);
    const blob = await response.blob();
    const filename = url.split("/").pop() || "sample-audio";
    state.audioFile = new File([blob], filename, { type: blob.type || "audio/mpeg" });
    
    if (btnElement) {
      btnElement.textContent = "SAMPLE LOADED ✅";
      btnElement.style.borderColor = "var(--accent-gold)";
      btnElement.style.color = "var(--accent-gold)";
      status.textContent = "Sample audio loaded successfully. Click 'RUN PIPELINE' to process.";
    }
  } catch (error) {
    console.error("Failed to load sample:", error);
    if (btnElement) {
      btnElement.textContent = "FAILED TO LOAD";
      status.textContent = "Failed to load sample audio.";
    }
  } finally {
    if (btnElement) {
      setTimeout(() => {
        btnElement.textContent = originalText;
        btnElement.disabled = false;
        btnElement.style.borderColor = "";
        btnElement.style.color = "";
      }, 3000);
    }
  }
}

async function initSamples() {
  const res = await fetch("/api/samples");
  const data = await res.json();
  const sampleBtn = el("loadSample");
  const toneBtn = el("loadTone");
  sampleBtn.onclick = () => setPreviewFromUrl(data.recommended_audio, sampleBtn);
  toneBtn.onclick = () => setPreviewFromUrl(data.test_tone_audio, toneBtn);
}

audioInput.addEventListener("change", (e) => {
  const file = e.target.files?.[0];
  state.audioFile = file || null;
  audioPreview.src = file ? URL.createObjectURL(file) : "";
});
modeRealtime.onclick = () => setMode("realtime");
modeAccurate.onclick = () => setMode("accurate");
transcriptInput.addEventListener("input", debounceLive);
el("runPipeline").onclick = runPipeline;

transcriptInput.value =
  "Mary Jo, DOB January 1, 1980, lives at 60 Sloane Avenue, London. " +
  "Phone is 617-555-0199 and MRN is A1980-4471. She reports cough and wheezing for five days.";

initSamples().then(runLiveGuard);
