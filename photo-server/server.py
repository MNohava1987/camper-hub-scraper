#!/usr/bin/env python3
"""Camper Hub Photo Server — Cloud Run edition."""
import io
import os
import uuid

import qrcode
from flask import Flask, abort, request, send_file, Response
from werkzeug.middleware.proxy_fix import ProxyFix
from google.cloud import storage
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()

app = Flask(__name__)
# Trust X-Forwarded-Proto from Cloud Run so request.url_root uses https://
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

BUCKET_NAME = os.environ["GCS_PHOTOS_BUCKET"]
UPLOAD_TOKEN = os.environ["UPLOAD_TOKEN"]
PORT = int(os.environ.get("PORT", "3001"))

_client: storage.Client | None = None


def gcs() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client()
    return _client


def get_bucket() -> storage.Bucket:
    return gcs().bucket(BUCKET_NAME)


def check_token() -> None:
    token = request.headers.get("X-Upload-Token") or request.args.get("token", "")
    if token != UPLOAD_TOKEN:
        abort(401, "Unauthorized")


@app.route("/upload", methods=["POST"])
def upload():
    check_token()
    if "photo" not in request.files:
        abort(400, "No photo field")
    f = request.files["photo"]
    if not f.filename:
        abort(400, "Empty filename")

    raw = f.read()
    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")

    if max(img.size) > 3840:
        img.thumbnail((3840, 3840), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88, optimize=True)
    buf.seek(0)

    filename = f"{uuid.uuid4().hex}.jpg"
    blob = get_bucket().blob(filename)
    blob.upload_from_file(buf, content_type="image/jpeg")

    return {"ok": True, "filename": filename}, 201


@app.route("/photo/<filename>")
def serve_photo(filename: str):
    blob = get_bucket().blob(filename)
    if not blob.exists():
        abort(404)
    data = blob.download_as_bytes()
    return send_file(io.BytesIO(data), mimetype="image/jpeg")


@app.route("/photo/<filename>", methods=["DELETE"])
def delete_photo(filename: str):
    check_token()
    blob = get_bucket().blob(filename)
    if not blob.exists():
        abort(404)
    blob.delete()
    return {"ok": True}, 200


@app.route("/manage")
def manage():
    check_token()
    token = request.args.get("token", "")
    blobs = sorted(gcs().list_blobs(BUCKET_NAME), key=lambda b: b.name)

    items = "".join(
        f'<div class="item">'
        f'<img src="/photo/{b.name}" loading="lazy" alt="{b.name}">'
        f'<button onclick="del(\'{b.name}\')">Delete</button>'
        f"</div>"
        for b in blobs
    )

    html = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Camper Hub Photos</title>
<style>
body{{font-family:sans-serif;background:#111;color:#eee;padding:1rem;margin:0}}
h1{{margin-bottom:1rem}}
form{{margin-bottom:1.5rem;background:#222;padding:1rem;border-radius:6px}}
form label{{display:block;margin-bottom:.5rem}}
form input[type=file]{{margin-bottom:.8rem;display:block}}
form button{{padding:.5rem 1.2rem;background:#0a0;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:1rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1rem}}
.item img{{width:100%;border-radius:4px;display:block}}
.item button{{width:100%;margin-top:.4rem;padding:.4rem;background:#c00;color:#fff;border:none;border-radius:4px;cursor:pointer}}
</style></head>
<body>
<h1>Camper Hub Photos ({len(blobs)})</h1>
<form method="post" action="/upload?token={token}" enctype="multipart/form-data">
  <label>Add photo(s):</label>
  <input type="file" name="photo" accept="image/*" capture="environment" multiple>
  <button type="submit">Upload</button>
</form>
<div class="grid">{items}</div>
<script>
async function del(name) {{
  if (!confirm('Delete ' + name + '?')) return;
  const r = await fetch('/photo/' + name + '?token={token}', {{method:'DELETE'}});
  if (r.ok) location.reload();
  else alert('Delete failed: ' + r.status);
}}
</script>
</body></html>"""
    return Response(html, content_type="text/html")


@app.route("/qr.png")
def qr_code():
    service_url = os.environ.get("SERVICE_URL", request.url_root.rstrip("/"))
    upload_url = f"{service_url}/manage?token={UPLOAD_TOKEN}"
    img = qrcode.make(upload_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/healthz")
def health():
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
