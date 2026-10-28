// aiClient.js file
// Node.js client for the Python AI service (ai_service.py).
// requires Node 18+ (built-in fetch, FormData, Blob).

const fs = require("fs");
const path = require("path");

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || "http://localhost:8000";
const TIMEOUT_MS = Number(process.env.AI_TIMEOUT_MS || 15000);
const TRANSCRIBE_TIMEOUT_MS = Number(process.env.AI_TRANSCRIBE_TIMEOUT_MS || 120000);

async function request(urlPath, options = {}, timeoutMs = TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  // for file uploads (FormData) the browser/Node sets the Content-Type itself
  const isForm = options.body instanceof FormData;
  const headers = isForm
    ? { ...(options.headers || {}) }
    : { "Content-Type": "application/json", ...(options.headers || {}) };

  try {
    const res = await fetch(`${AI_SERVICE_URL}${urlPath}`, {
      ...options,
      headers,
      signal: controller.signal,
    });

    if (!res.ok) {
      const body = await res.text();
      throw new Error(`AI service error ${res.status}: ${body}`);
    }
    return await res.json();
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error(`AI service timed out after ${timeoutMs}ms`);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

// Classify a single text -> { label, score }
function classifyText(text) {
  return request("/classify", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

// Classify many texts in one request -> [{ label, score }, ...]
async function classifyBatch(texts) {
  const data = await request("/classify-batch", {
    method: "POST",
    body: JSON.stringify({ texts }),
  });
  return data.results;
}

// Transcribe Quran recitation audio -> { text }
// `audio` can be a file path (string) or a Buffer (e.g. from multer memoryStorage).
// For a Buffer, pass a filename with its extension, e.g. "recitation.wav".
async function transcribeAudio(audio, filename) {
  let buffer;
  let name = filename;

  if (typeof audio === "string") {
    buffer = await fs.promises.readFile(audio);
    name = name || path.basename(audio);
  } else {
    buffer = audio;
    name = name || "audio.wav";
  }

  const form = new FormData();
  form.append("file", new Blob([buffer]), name);

  return request("/transcribe", { method: "POST", body: form }, TRANSCRIBE_TIMEOUT_MS);
}


// Check a recitation of one ayah -> { ayah, words, summary, transcription }
// `audio` = file path or Buffer (same as transcribeAudio); ayah e.g. "1:1"
async function checkRecitation(audio, ayah, filename, { lenientTashkeel = true } = {}) {
  let buffer;
  let name = filename;

  if (typeof audio === "string") {
    buffer = await fs.promises.readFile(audio);
    name = name || path.basename(audio);
  } else {
    buffer = audio;
    name = name || "audio.wav";
  }

  const form = new FormData();
  form.append("file", new Blob([buffer]), name);
  form.append("ayah", ayah);
  form.append("lenient_tashkeel", String(lenientTashkeel));

  return request("/quran/check", { method: "POST", body: form }, TRANSCRIBE_TIMEOUT_MS);
}


// Check that the AI service is up
async function isHealthy() {
  try {
    const data = await request("/health");
    return data.status === "ok";
  } catch {
    return false;
  }
}


module.exports = { classifyText, classifyBatch, transcribeAudio, checkRecitation, isHealthy };








/* ---------- Example usage in Express (with multer for uploads) ----------

const express = require("express");
const multer = require("multer");
const { classifyText, transcribeAudio } = require("./aiClient");

const app = express();
const upload = multer({ storage: multer.memoryStorage() });
app.use(express.json());

app.post("/api/analyze", async (req, res) => {
  try {
    const { text } = req.body;
    if (!text) return res.status(400).json({ error: "text is required" });
    res.json(await classifyText(text));
  } catch (e) {
    res.status(502).json({ error: e.message });
  }
});

app.post("/api/transcribe", upload.single("audio"), async (req, res) => {
  try {
    if (!req.file) return res.status(400).json({ error: "audio file is required" });
    res.json(await transcribeAudio(req.file.buffer, req.file.originalname));
  } catch (e) {
    res.status(502).json({ error: e.message });
  }
});

app.listen(3000);
*/



// // aiClient.js
// // Node.js client for the Python AI service (ai_service.py).
// // Requires Node 18+ (built-in fetch).

// const AI_SERVICE_URL = process.env.AI_SERVICE_URL || "http://localhost:8000";
// const TIMEOUT_MS = Number(process.env.AI_TIMEOUT_MS || 15000);

// async function request(path, options = {}) {
//   const controller = new AbortController();
//   const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

//   try {
//     const res = await fetch(`${AI_SERVICE_URL}${path}`, {
//       ...options,
//       headers: { "Content-Type": "application/json", ...(options.headers || {}) },
//       signal: controller.signal,
//     });

//     if (!res.ok) {
//       const body = await res.text();
//       throw new Error(`AI service error ${res.status}: ${body}`);
//     }
//     return await res.json();
//   } catch (err) {
//     if (err.name === "AbortError") {
//       throw new Error(`AI service timed out after ${TIMEOUT_MS}ms`);
//     }
//     throw err;
//   } finally {
//     clearTimeout(timer);
//   }
// }

// // Classify a single text -> { label, score }
// function classifyText(text) {
//   return request("/classify", {
//     method: "POST",
//     body: JSON.stringify({ text }),
//   });
// }

// // Classify many texts in one request -> [{ label, score }, ...]
// async function classifyBatch(texts) {
//   const data = await request("/classify-batch", {
//     method: "POST",
//     body: JSON.stringify({ texts }),
//   });
//   return data.results;
// }

// // Check that the AI service is up
// async function isHealthy() {
//   try {
//     const data = await request("/health");
//     return data.status === "ok";
//   } catch {
//     return false;
//   }
// }

// module.exports = { classifyText, classifyBatch, isHealthy };



