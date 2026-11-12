import os
import base64
import requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024

REPLICATE_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "")
MODEL = "owner/model-name"
VIDEO_FIELD = "video"
PROMPT_FIELD = "prompt"

API = "https://api.replicate.com/v1"
HEADERS = {"Authorization": f"Bearer {REPLICATE_TOKEN}", "Content-Type": "application/json"}

PAGE = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Video to Video</title>
<link rel="manifest" href="/manifest.json">
<link rel="icon" href="/icon.svg">
<meta name="theme-color" content="#2563eb">
<style>
  body{font-family:sans-serif;max-width:480px;margin:0 auto;padding:20px;background:#111;color:#eee}
  h1{font-size:22px}
  input,textarea,button{width:100%;box-sizing:border-box;margin:8px 0;padding:12px;border-radius:8px;border:1px solid #444;background:#222;color:#eee;font-size:16px}
  button{background:#2563eb;border:none;font-weight:bold}
  button:disabled{opacity:.5}
  video{width:100%;margin-top:12px;border-radius:8px}
  #status{margin-top:10px;color:#9ca3af}
</style>
</head>
<body>
<h1>🎬 AI Video to Video</h1>
<input type="file" id="video" accept="video/*">
<textarea id="prompt" rows="3" placeholder="Mital: bddlha l style anime"></textarea>
<button id="go">Bda</button>
<div id="status"></div>
<video id="out" controls style="display:none"></video>
<script>
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js");
const $ = id => document.getElementById(id);
$("go").onclick = async () => {
  const file = $("video").files[0];
  if (!file) return alert("Khtar vidéo");
  $("go").disabled = true;
  $("out").style.display = "none";
  $("status").textContent = "Kanrfa3 l-vidéo...";
  const fd = new FormData();
  fd.append("video", file);
  fd.append("prompt", $("prompt").value);
  try {
    const r = await fetch("/start", {method: "POST", body: fd});
    const d = await r.json();
    if (d.error) throw new Error(d.error);
    poll(d.id);
  } catch (e) {
    $("status").textContent = "Khata2: " + e.message;
    $("go").disabled = false;
  }
};
async function poll(id) {
  const r = await fetch("/status/" + id);
  const d = await r.json();
  if (d.status === "succeeded") {
    $("status").textContent = "Wejdat ✅";
    $("out").src = d.output;
    $("out").style.display = "block";
    $("go").disabled = false;
  } else if (d.status === "failed" || d.status === "canceled" || d.error) {
    $("status").textContent = "Khata2: " + (d.error || d.status);
    $("go").disabled = false;
  } else {
    $("status").textContent = "Kayt3ala7... (" + d.status + ")";
    setTimeout(() => poll(id), 4000);
  }
}
</script>
</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(PAGE)


@app.route("/manifest.json")
def manifest():
    return jsonify(
        name="AI Video to Video", short_name="AI Video",
        start_url="/", display="standalone",
        background_color="#111111", theme_color="#2563eb",
        icons=[{"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}],
    )


@app.route("/icon.svg")
def icon():
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
           '<rect width="512" height="512" fill="#2563eb"/>'
           '<rect x="110" y="150" width="292" height="212" rx="40" fill="none" stroke="#fff" stroke-width="22"/>'
           '<polygon points="215,200 215,312 315,256" fill="#fff"/></svg>')
    return svg, 200, {"Content-Type": "image/svg+xml"}


@app.route("/sw.js")
def sw():
    js = "self.addEventListener('fetch', e => {});"
    return js, 200, {"Content-Type": "application/javascript"}


@app.route("/start", methods=["POST"])
def start():
    f = request.files.get("video")
    prompt = request.form.get("prompt", "")
    if not f:
        return jsonify(error="Ma kayn hta vidéo"), 400
    mime = f.mimetype or "video/mp4"
    b64 = base64.b64encode(f.read()).decode()
    data_uri = f"data:{mime};base64,{b64}"
    payload = {"input": {VIDEO_FIELD: data_uri, PROMPT_FIELD: prompt}}
    try:
        r = requests.post(f"{API}/models/{MODEL}/predictions",
                          headers=HEADERS, json=payload, timeout=120)
        data = r.json()
    except Exception as e:
        return jsonify(error=str(e)), 500
    if r.status_code >= 400:
        return jsonify(error=data.get("detail", "API error")), 500
    return jsonify(id=data["id"])


@app.route("/status/<pred_id>")
def status(pred_id):
    try:
        r = requests.get(f"{API}/predictions/{pred_id}", headers=HEADERS, timeout=30)
        data = r.json()
    except Exception as e:
        return jsonify(error=str(e)), 500
    output = data.get("output")
    if isinstance(output, list) and output:
        output = output[0]
    return jsonify(status=data.get("status"), output=output, error=data.get("error"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
