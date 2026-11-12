"""Interfaz web local para reconocimiento con un modelo de Teachable Machine."""

from __future__ import annotations

import json
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse


HOST = "127.0.0.1"
PORT = 8000
MODEL_ARCHIVE = Path(__file__).with_name("tm-my-image-model.zip")
MODEL_FILES = {
    "/model/model.json": ("model.json", "application/json"),
    "/model/metadata.json": ("metadata.json", "application/json"),
    "/model/weights.bin": ("weights.bin", "application/octet-stream"),
}

PAGE = r"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#10131b">
  <title>Vision — Reconocimiento de objetos</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #10131b;
      --panel: #181c27;
      --panel-soft: #1d2230;
      --border: #2a3040;
      --text: #f2f4f8;
      --muted: #9aa3b5;
      --accent: #a7f36b;
      --accent-dark: #23351d;
      --blue: #8daeff;
      --danger: #ff8585;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(ellipse at 12% -10%, #273249 0, transparent 38%),
        var(--bg);
      color: var(--text);
      font: 15px/1.5 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    button { font: inherit; }
    .shell { max-width: 1240px; margin: 0 auto; padding: 34px 28px 48px; }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      margin-bottom: 30px;
    }
    .brand { display: flex; align-items: center; gap: 13px; }
    .brand-mark {
      display: grid;
      place-items: center;
      width: 43px;
      height: 43px;
      border: 1px solid #536447;
      border-radius: 14px;
      background: var(--accent-dark);
      color: var(--accent);
      font-size: 21px;
    }
    h1, h2, p { margin: 0; }
    h1 { font-size: 20px; letter-spacing: -.4px; }
    .eyebrow, .subtle { color: var(--muted); }
    .eyebrow { font-size: 12px; letter-spacing: 1.4px; text-transform: uppercase; }
    .subtle { font-size: 13px; }
    .status {
      display: inline-flex;
      align-items: center;
      gap: 9px;
      padding: 8px 12px;
      border: 1px solid var(--border);
      border-radius: 999px;
      background: #171b25;
      color: #c9cfda;
      font-size: 12px;
      white-space: nowrap;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #6d7482;
    }
    .status.connected .status-dot { background: var(--accent); box-shadow: 0 0 12px #a7f36b99; }
    .status.error .status-dot { background: var(--danger); }
    .intro { margin-bottom: 22px; }
    .intro h2 { margin-bottom: 6px; font-size: 27px; letter-spacing: -.7px; }
    .intro p { color: var(--muted); }
    .grid { display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(300px, .85fr); gap: 20px; }
    .panel {
      overflow: hidden;
      border: 1px solid var(--border);
      border-radius: 17px;
      background: color-mix(in srgb, var(--panel) 95%, transparent);
      box-shadow: 0 18px 48px #00000018;
    }
    .panel-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 17px 19px;
      border-bottom: 1px solid var(--border);
    }
    .panel-head h2 { font-size: 15px; font-weight: 600; }
    .camera-frame {
      position: relative;
      display: grid;
      min-height: 340px;
      aspect-ratio: 16 / 9;
      place-items: center;
      overflow: hidden;
      background:
        linear-gradient(#ffffff08 1px, transparent 1px),
        linear-gradient(90deg, #ffffff08 1px, transparent 1px),
        radial-gradient(ellipse at center, #202a3a, #11151e 75%);
      background-size: 32px 32px, 32px 32px, auto;
    }
    video { display: none; width: 100%; height: 100%; object-fit: cover; }
    .camera-frame.live video { display: block; }
    .camera-placeholder { max-width: 300px; padding: 28px; text-align: center; }
    .camera-frame.live .camera-placeholder { display: none; }
    .camera-icon { margin-bottom: 12px; color: #8290a8; font-size: 34px; }
    .camera-placeholder strong { display: block; margin-bottom: 5px; font-size: 15px; }
    .camera-placeholder p { color: var(--muted); font-size: 13px; }
    .camera-label {
      position: absolute;
      top: 14px;
      left: 14px;
      display: flex;
      align-items: center;
      gap: 7px;
      padding: 6px 9px;
      border: 1px solid #ffffff20;
      border-radius: 7px;
      background: #10131bc9;
      color: #e7eaf0;
      font-size: 11px;
      backdrop-filter: blur(8px);
    }
    .camera-label span { width: 6px; height: 6px; border-radius: 50%; background: #737b89; }
    .live .camera-label span { background: var(--danger); }
    .camera-controls { display: flex; flex-wrap: wrap; gap: 9px; padding: 15px 18px; }
    .button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      min-height: 38px;
      padding: 8px 13px;
      border: 1px solid var(--border);
      border-radius: 9px;
      background: var(--panel-soft);
      color: var(--text);
      cursor: pointer;
      transition: border-color .15s, background .15s, transform .15s;
    }
    .button:hover { border-color: #505a70; background: #252b3a; }
    .button:active { transform: translateY(1px); }
    .button.primary { border-color: #b6f783; background: var(--accent); color: #17220f; font-weight: 650; }
    .button.primary:hover { background: #b9fb81; }
    .button:disabled { cursor: not-allowed; opacity: .5; }
    .camera-note { align-self: center; margin-left: auto; color: var(--muted); font-size: 12px; }
    .side { display: flex; flex-direction: column; gap: 20px; }
    .summary { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 16px; }
    .stat {
      min-height: 91px;
      padding: 14px;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--panel-soft);
    }
    .stat-label { color: var(--muted); font-size: 12px; }
    .stat-value { display: block; margin-top: 5px; font-size: 25px; font-weight: 650; letter-spacing: -.5px; }
    .detections { min-height: 120px; padding: 14px 16px 16px; }
    .detection-list { display: grid; gap: 9px; }
    .detection-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 10px 11px;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: var(--panel-soft);
    }
    .object-name { display: flex; align-items: center; gap: 9px; font-weight: 550; }
    .object-marker { width: 8px; height: 8px; border-radius: 3px; background: var(--accent); }
    .confidence { color: var(--blue); font-size: 12px; }
    .empty { padding: 19px 8px; color: var(--muted); text-align: center; font-size: 13px; }
    .counts { padding: 8px 16px 16px; }
    .count-row {
      display: grid;
      grid-template-columns: 1fr auto;
      align-items: center;
      gap: 10px;
      padding: 10px 0;
      border-bottom: 1px solid #2a304080;
    }
    .count-row:last-child { border-bottom: 0; }
    .count-value { min-width: 36px; padding: 2px 9px; border-radius: 7px; background: var(--accent-dark); color: var(--accent); text-align: center; font-weight: 650; }
    .counts-empty { padding: 20px 0; color: var(--muted); text-align: center; font-size: 13px; }
    .footer-note {
      margin-top: 20px;
      padding: 13px 15px;
      border: 1px solid #3c4656;
      border-radius: 11px;
      background: #171d28;
      color: #b7c0d0;
      font-size: 12px;
    }
    .footer-note strong { color: var(--text); }
    @media (max-width: 820px) {
      .grid { grid-template-columns: 1fr; }
      .side { display: grid; grid-template-columns: 1fr 1fr; align-items: start; }
    }
    @media (max-width: 560px) {
      .shell { padding: 22px 15px 34px; }
      header { align-items: flex-start; }
      .status { max-width: 145px; white-space: normal; }
      .intro h2 { font-size: 23px; }
      .camera-frame { min-height: 235px; }
      .side { display: flex; }
      .camera-note { width: 100%; margin-left: 0; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <div class="brand">
        <div class="brand-mark" aria-hidden="true">⌁</div>
        <div>
          <div class="eyebrow">Vision / Panel</div>
          <h1>Reconocimiento de objetos</h1>
        </div>
      </div>
      <div id="status" class="status" role="status">
        <span class="status-dot"></span>
        <span id="statusText">Esperando al modelo</span>
      </div>
    </header>

    <section class="intro">
      <h2>Vista en tiempo real</h2>
      <p>Visualiza la cámara y consulta las detecciones y apariciones acumuladas.</p>
    </section>

    <div class="grid">
      <section class="panel" aria-labelledby="cameraTitle">
        <div class="panel-head">
          <h2 id="cameraTitle">Cámara</h2>
          <span class="subtle">Vista previa local</span>
        </div>
        <div id="cameraFrame" class="camera-frame">
          <video id="video" autoplay muted playsinline></video>
          <div class="camera-placeholder">
            <div class="camera-icon" aria-hidden="true">◉</div>
            <strong>La cámara está en pausa</strong>
            <p>Activa la cámara para ver la imagen aquí. La detección se conectará al integrar tu modelo.</p>
          </div>
          <div class="camera-label"><span></span><span id="cameraLabel">CÁMARA INACTIVA</span></div>
        </div>
        <div class="camera-controls">
          <button id="cameraButton" class="button primary" type="button">Activar cámara</button>
          <button id="resetButton" class="button" type="button">Reiniciar conteo</button>
          <span class="camera-note">La cámara se usa solo en este navegador.</span>
        </div>
      </section>

      <div class="side">
        <section class="panel" aria-labelledby="summaryTitle">
          <div class="panel-head">
            <h2 id="summaryTitle">Resumen</h2>
          </div>
          <div class="summary">
            <div class="stat">
              <span class="stat-label">Apariciones</span>
              <strong id="totalCount" class="stat-value">0</strong>
            </div>
            <div class="stat">
              <span class="stat-label">Tipos de objeto</span>
              <strong id="typeCount" class="stat-value">0</strong>
            </div>
          </div>
        </section>

        <section class="panel" aria-labelledby="detectedTitle">
          <div class="panel-head">
            <h2 id="detectedTitle">Detectado ahora</h2>
            <span id="detectedCount" class="subtle">0 objetos</span>
          </div>
          <div class="detections">
            <div id="detectionList" class="detection-list">
              <div class="empty">Todavía no hay detecciones.</div>
            </div>
          </div>
        </section>

        <section class="panel" aria-labelledby="countsTitle">
          <div class="panel-head">
            <h2 id="countsTitle">Conteo por objeto</h2>
            <span class="subtle">Acumulado</span>
          </div>
          <div id="countsList" class="counts">
            <div class="counts-empty">El conteo aparecerá cuando el modelo detecte objetos.</div>
          </div>
        </section>
      </div>
    </div>

    <p class="footer-note">
      <strong>Modelo conectado:</strong> Libros, Lentes y Extintores.
      La clasificación se procesa en este navegador; se cuenta una aparición cuando la clase
      supera el 80% de confianza y vuelve a aparecer tras dejar de detectarse.
      Este modelo clasifica la imagen completa, no dibuja recuadros ni distingue varias unidades
      de la misma clase al mismo tiempo.
    </p>
  </main>

  <script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@1.7.4/dist/tf.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@teachablemachine/image@0.8/dist/teachablemachine-image.min.js"></script>
  <script>
    const status = document.getElementById("status");
    const statusText = document.getElementById("statusText");
    const video = document.getElementById("video");
    const cameraFrame = document.getElementById("cameraFrame");
    const cameraButton = document.getElementById("cameraButton");
    let cameraStream = null;
    let model = null;
    let isDetecting = false;
    let activeLabel = null;
    let missedFrames = 0;
    let appearanceSequence = 0;
    let receivedDetections = false;
    const CONFIDENCE_THRESHOLD = 0.8;
    const RELEASE_AFTER_MISSES = 4;

    function setStatus(kind, text) {
      status.className = "status" + (kind ? " " + kind : "");
      statusText.textContent = text;
    }

    function renderState(state) {
      document.getElementById("totalCount").textContent = state.total;
      document.getElementById("typeCount").textContent = Object.keys(state.counts).length;

      const detections = state.current || [];
      document.getElementById("detectedCount").textContent =
        detections.length + (detections.length === 1 ? " objeto" : " objetos");
      const detectionList = document.getElementById("detectionList");
      if (detections.length === 0) {
        detectionList.innerHTML = '<div class="empty">Todavía no hay detecciones.</div>';
      } else {
        detectionList.replaceChildren(...detections.map((item) => {
          const row = document.createElement("div");
          row.className = "detection-row";
          const name = document.createElement("span");
          name.className = "object-name";
          const marker = document.createElement("span");
          marker.className = "object-marker";
          const label = document.createElement("span");
          label.textContent = item.label;
          name.append(marker, label);
          row.append(name);
          if (typeof item.confidence === "number") {
            const confidence = document.createElement("span");
            confidence.className = "confidence";
            confidence.textContent = Math.round(item.confidence * 100) + "%";
            row.append(confidence);
          }
          return row;
        }));
      }

      const countsList = document.getElementById("countsList");
      const entries = Object.entries(state.counts).sort((a, b) => b[1] - a[1]);
      if (entries.length === 0) {
        countsList.innerHTML = '<div class="counts-empty">El conteo aparecerá cuando el modelo detecte objetos.</div>';
      } else {
        countsList.replaceChildren(...entries.map(([label, count]) => {
          const row = document.createElement("div");
          row.className = "count-row";
          const name = document.createElement("span");
          name.textContent = label;
          const value = document.createElement("span");
          value.className = "count-value";
          value.textContent = count;
          row.append(name, value);
          return row;
        }));
      }
    }

    async function refreshState() {
      try {
        const response = await fetch("/api/state", { cache: "no-store" });
        if (!response.ok) throw new Error("No se pudo consultar el estado.");
        const state = await response.json();
        renderState(state);
        if (state.total > 0) receivedDetections = true;
        if (receivedDetections) setStatus("connected", "Recibiendo detecciones");
      } catch (error) {
        setStatus("error", "Sin conexión con el servidor");
      }
    }

    async function reportDetections(objects) {
      const response = await fetch("/api/detections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ objects }),
      });
      if (!response.ok) throw new Error("No se pudieron guardar las detecciones.");
      const state = await response.json();
      renderState(state);
      if (state.total > 0) receivedDetections = true;
    }

    async function recognitionLoop() {
      isDetecting = true;
      setStatus("connected", "Modelo listo · reconociendo");
      try {
        while (isDetecting && cameraStream) {
          const predictions = await model.predict(video);
          if (!isDetecting || !cameraStream) break;
          const best = predictions.reduce((highest, prediction) =>
            prediction.probability > highest.probability ? prediction : highest
          );
          let objects = [];
          if (best.probability >= CONFIDENCE_THRESHOLD) {
            missedFrames = 0;
            if (best.className !== activeLabel) {
              activeLabel = best.className;
              appearanceSequence += 1;
            }
            objects = [{
              label: best.className,
              confidence: best.probability,
              id: `appearance-${appearanceSequence}`,
            }];
          } else {
            missedFrames += 1;
            if (missedFrames >= RELEASE_AFTER_MISSES) activeLabel = null;
          }
          await reportDetections(objects);
          await new Promise((resolve) => window.setTimeout(resolve, 250));
        }
      } catch (error) {
        isDetecting = false;
        setStatus("error", "Falló la detección del modelo");
        console.error("Error durante la detección:", error);
      }
    }

    async function stopCamera() {
      isDetecting = false;
      if (cameraStream) cameraStream.getTracks().forEach((track) => track.stop());
      cameraStream = null;
      video.srcObject = null;
      cameraFrame.classList.remove("live");
      document.getElementById("cameraLabel").textContent = "CÁMARA INACTIVA";
      cameraButton.textContent = "Activar cámara";
      await reportDetections([]);
    }

    cameraButton.addEventListener("click", async () => {
      if (cameraStream) {
        try {
          await stopCamera();
          setStatus("", "Esperando al modelo");
        } catch (error) {
          setStatus("error", "No se pudo detener la cámara");
        }
        return;
      }
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setStatus("error", "Cámara no disponible");
        return;
      }
      try {
        cameraButton.disabled = true;
        setStatus("", "Cargando modelo");
        if (!window.tmImage) {
          throw new Error("No se cargó TensorFlow.js desde la CDN.");
        }
        if (!model) {
          model = await window.tmImage.load("/model/model.json", "/model/metadata.json");
        }
        cameraStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        video.srcObject = cameraStream;
        await video.play();
        cameraFrame.classList.add("live");
        document.getElementById("cameraLabel").textContent = "VISTA PREVIA";
        cameraButton.textContent = "Pausar cámara";
        missedFrames = 0;
        activeLabel = null;
        recognitionLoop();
      } catch (error) {
        if (cameraStream) {
          cameraStream.getTracks().forEach((track) => track.stop());
          cameraStream = null;
        }
        cameraFrame.classList.remove("live");
        video.srcObject = null;
        cameraButton.textContent = "Activar cámara";
        setStatus("error", "No se pudo iniciar cámara o modelo");
        console.error("Error al iniciar cámara o modelo:", error);
      } finally {
        cameraButton.disabled = false;
      }
    });

    document.getElementById("resetButton").addEventListener("click", async () => {
      try {
        const response = await fetch("/api/reset", { method: "POST" });
        if (!response.ok) throw new Error("No se pudo reiniciar el conteo.");
        receivedDetections = false;
        activeLabel = null;
        missedFrames = 0;
        renderState(await response.json());
        setStatus(cameraStream ? "connected" : "", cameraStream ? "Modelo listo · reconociendo" : "Esperando al modelo");
      } catch (error) {
        setStatus("error", "No se pudo reiniciar el conteo");
      }
    });

    refreshState();
    window.setInterval(refreshState, 1000);
  </script>
</body>
</html>
"""

STATE_LOCK = Lock()
COUNTS: dict[str, int] = {}
CURRENT: list[dict[str, object]] = []
SEEN_IDS: set[str] = set()


def get_state() -> dict[str, object]:
    with STATE_LOCK:
        counts = dict(COUNTS)
        return {
            "counts": counts,
            "total": sum(counts.values()),
            "current": [dict(item) for item in CURRENT],
        }


class RecognitionHandler(BaseHTTPRequestHandler):
    server_version = "ObjectRecognitionUI/1.0"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/state":
            self._send_json(200, get_state())
        elif path in MODEL_FILES:
            member, content_type = MODEL_FILES[path]
            if not MODEL_ARCHIVE.is_file():
                self._send_json(503, {"error": "No se encontró el archivo ZIP del modelo."})
                return
            try:
                with zipfile.ZipFile(MODEL_ARCHIVE) as archive:
                    body = archive.read(member)
            except (OSError, zipfile.BadZipFile, KeyError):
                self._send_json(500, {"error": f"No se pudo leer {member} del ZIP del modelo."})
                return
            self._send_bytes(200, body, content_type)
        else:
            self._send_json(404, {"error": "Ruta no encontrada."})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/reset":
            global CURRENT
            with STATE_LOCK:
                COUNTS.clear()
                CURRENT = []
                SEEN_IDS.clear()
            self._send_json(200, get_state())
            return

        if path != "/api/detections":
            self._send_json(404, {"error": "Ruta no encontrada."})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "Content-Length no válido."})
            return
        if content_length <= 0 or content_length > 1_000_000:
            self._send_json(400, {"error": "El cuerpo debe tener entre 1 byte y 1 MB."})
            return

        try:
            payload = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "El cuerpo debe ser JSON válido."})
            return
        if not isinstance(payload, dict) or not isinstance(payload.get("objects"), list):
            self._send_json(400, {"error": "Se esperaba un objeto JSON con una lista 'objects'."})
            return

        cleaned: list[dict[str, object]] = []
        for item in payload["objects"]:
            if not isinstance(item, dict):
                self._send_json(400, {"error": "Cada elemento de 'objects' debe ser un objeto."})
                return
            label = item.get("label")
            if not isinstance(label, str) or not label.strip() or len(label.strip()) > 100:
                self._send_json(400, {"error": "Cada detección necesita una etiqueta de 1 a 100 caracteres."})
                return
            detection: dict[str, object] = {"label": label.strip()}
            confidence = item.get("confidence")
            if confidence is not None:
                if (
                    isinstance(confidence, bool)
                    or not isinstance(confidence, (int, float))
                    or not 0 <= confidence <= 1
                ):
                    self._send_json(400, {"error": "'confidence' debe ser un número entre 0 y 1."})
                    return
                detection["confidence"] = float(confidence)
            object_id = item.get("id")
            if object_id is not None:
                if not isinstance(object_id, (str, int)) or isinstance(object_id, bool):
                    self._send_json(400, {"error": "'id' debe ser texto o un entero."})
                    return
                detection["id"] = str(object_id)
            cleaned.append(detection)

        with STATE_LOCK:
            CURRENT = [{"label": item["label"], **(
                {"confidence": item["confidence"]} if "confidence" in item else {}
            )} for item in cleaned]
            for item in cleaned:
                label = str(item["label"])
                object_id = item.get("id")
                if object_id is not None:
                    unique_id = str(object_id)
                    if unique_id in SEEN_IDS:
                        continue
                    SEEN_IDS.add(unique_id)
                COUNTS[label] = COUNTS.get(label, 0) + 1

        self._send_json(200, get_state())

    def _send_json(self, status_code: int, data: dict[str, object]) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._send_bytes(status_code, body, "application/json; charset=utf-8")

    def _send_bytes(self, status_code: int, body: bytes, content_type: str) -> None:
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"[web] {self.address_string()} - {format_string % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), RecognitionHandler)
    print(f"Interfaz lista: http://{HOST}:{PORT}")
    print("Pulsa Ctrl+C para detener el servidor.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()