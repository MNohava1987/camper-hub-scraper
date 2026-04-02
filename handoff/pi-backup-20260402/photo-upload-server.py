#!/usr/bin/env python3
"""Simple photo upload server for the campfire mirror."""
import os
import io
import uuid
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler

UPLOAD_DIR = "/home/mnohava/MagicMirror/modules/MMM-ImageSlideshow/photos"
PORT = 3001
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/heic", "image/heif"}
MAX_LONG_EDGE = 3840  # cap at 4K — phones send up to 16K grid HEIC tiles

try:
    import pillow_heif
    from PIL import Image as PILImage, ImageOps
    pillow_heif.register_heif_opener()
    PILImage.MAX_IMAGE_PIXELS = None  # disable bomb check; uploads are from trusted phones
    HEIC_SUPPORT = True
except ImportError:
    try:
        from PIL import Image as PILImage, ImageOps
        PILImage.MAX_IMAGE_PIXELS = None
    except ImportError:
        PILImage = None
    HEIC_SUPPORT = False

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>Camper Hub Photos</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #111;
    color: #eee;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 24px;
    text-align: center;
  }
  .logo { font-size: 3em; margin-bottom: 8px; }
  h1 { font-size: 1.5em; font-weight: 700; margin-bottom: 6px; }
  .sub { color: #888; font-size: 0.95em; margin-bottom: 36px; line-height: 1.5; }
  .upload-btn {
    display: inline-block;
    background: #2a7d4f;
    color: white;
    font-size: 1.1em;
    font-weight: 600;
    padding: 16px 40px;
    border-radius: 50px;
    cursor: pointer;
    border: none;
    width: 100%;
    max-width: 320px;
    transition: background 0.2s;
  }
  .upload-btn:active { background: #1e5e3a; }
  input[type=file] { display: none; }
  .preview-wrap { margin-top: 20px; display: none; }
  .preview-wrap img { max-width: 280px; max-height: 280px; border-radius: 12px; }
  .status {
    margin-top: 20px;
    font-size: 1em;
    min-height: 28px;
    color: #aaa;
  }
  .status.success { color: #4caf50; font-weight: 600; }
  .status.error { color: #f44336; }
  .progress {
    width: 100%;
    max-width: 320px;
    height: 4px;
    background: #333;
    border-radius: 4px;
    margin-top: 16px;
    display: none;
  }
  .progress-bar {
    height: 100%;
    background: #2a7d4f;
    border-radius: 4px;
    width: 0%;
    transition: width 0.3s;
  }
</style>
</head>
<body>
<div class="logo">&#127869;&#127956;</div>
<h1>Camper Hub</h1>
<p class="sub">Add a photo to the big screen!<br>Everyone at camp will see it.</p>

<label class="upload-btn" for="fileInput">&#128247; Choose Photos</label>
<input type="file" id="fileInput" accept="image/*" multiple>

<div class="preview-wrap" id="previewWrap">
  <img id="preview" src="" alt="preview">
</div>
<div class="progress" id="progressWrap">
  <div class="progress-bar" id="progressBar"></div>
</div>
<div class="status" id="status"></div>

<script>
const fileInput = document.getElementById('fileInput');
const preview = document.getElementById('preview');
const previewWrap = document.getElementById('previewWrap');
const status = document.getElementById('status');
const progressWrap = document.getElementById('progressWrap');
const progressBar = document.getElementById('progressBar');

fileInput.addEventListener('change', async () => {
  const files = Array.from(fileInput.files);
  if (!files.length) return;

  const reader = new FileReader();
  reader.onload = e => {
    preview.src = e.target.result;
    previewWrap.style.display = 'block';
  };
  reader.readAsDataURL(files[0]);

  progressWrap.style.display = 'block';
  progressBar.style.width = '0%';

  let done = 0;
  let failed = 0;

  for (const file of files) {
    status.textContent = `Uploading ${done + 1} of ${files.length}...`;
    status.className = 'status';

    try {
      await new Promise((resolve, reject) => {
        const form = new FormData();
        form.append('photo', file);
        const xhr = new XMLHttpRequest();
        xhr.upload.addEventListener('progress', e => {
          if (e.lengthComputable) {
            const overall = (done / files.length + e.loaded / e.total / files.length) * 100;
            progressBar.style.width = overall + '%';
          }
        });
        xhr.addEventListener('load', () => xhr.status === 200 ? resolve() : reject());
        xhr.addEventListener('error', reject);
        xhr.open('POST', '/upload');
        xhr.send(form);
      });
      done++;
    } catch {
      failed++;
    }
    progressBar.style.width = ((done + failed) / files.length * 100) + '%';
  }

  fileInput.value = '';
  if (failed === 0) {
    status.textContent = `\u2705 ${done} photo${done > 1 ? 's' : ''} added to the big screen!`;
    status.className = 'status success';
  } else {
    status.textContent = `${done} uploaded, ${failed} failed.`;
    status.className = 'status error';
  }
});
</script>
</body>
</html>
"""


MANAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manage Photos</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #111;
    color: #eee;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    padding: 24px;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
  }
  h1 { font-size: 1.3em; font-weight: 700; }
  .count { color: #888; font-size: 0.9em; }
  .empty { text-align: center; color: #555; padding: 60px 0; font-size: 1.1em; }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 10px;
  }
  .photo-item {
    position: relative;
    border-radius: 8px;
    overflow: hidden;
    background: #222;
    aspect-ratio: 4/3;
  }
  .photo-item img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
  .del-btn {
    position: absolute;
    top: 6px;
    right: 6px;
    background: rgba(0,0,0,0.65);
    border: none;
    border-radius: 50%;
    width: 32px;
    height: 32px;
    font-size: 15px;
    cursor: pointer;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s;
  }
  .del-btn:active { background: rgba(200,50,50,0.85); }
  .photo-item.deleting { opacity: 0.3; pointer-events: none; }
  #toast {
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    background: #333;
    color: #eee;
    padding: 10px 20px;
    border-radius: 20px;
    font-size: 0.9em;
    opacity: 0;
    transition: opacity 0.3s;
    pointer-events: none;
  }
  #toast.show { opacity: 1; }
</style>
</head>
<body>
<header>
  <h1>&#128247; Manage Photos</h1>
  <span class="count" id="countLabel">__PHOTO_COUNT__ photos</span>
</header>
<div id="grid" class="grid">__PHOTO_ITEMS__</div>
<div class="empty" id="empty" style="display:none">No photos on the big screen.</div>
<div id="toast"></div>
<script>
let count = parseInt(document.getElementById('countLabel').textContent);

function updateCount(n) {
  document.getElementById('countLabel').textContent = n + ' photo' + (n !== 1 ? 's' : '');
  document.getElementById('empty').style.display = n === 0 ? 'block' : 'none';
}

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2000);
}

async function deletePhoto(filename, idx) {
  const item = document.getElementById('item-' + idx);
  item.classList.add('deleting');
  try {
    const r = await fetch('/photo/' + filename, { method: 'DELETE' });
    if (r.ok) {
      item.remove();
      count--;
      updateCount(count);
      toast('Deleted');
    } else {
      item.classList.remove('deleting');
      toast('Delete failed');
    }
  } catch {
    item.classList.remove('deleting');
    toast('Error');
  }
}

updateCount(__PHOTO_COUNT__);
</script>
</body>
</html>
"""


def parse_multipart(content_type, body):
    """Extract file bytes and mime type from a multipart/form-data body."""
    boundary = None
    for part in content_type.split(";"):
        part = part.strip()
        if part.startswith("boundary="):
            boundary = part[9:].strip('"')
            break
    if not boundary:
        return None, None

    boundary_bytes = ("--" + boundary).encode()
    parts = body.split(boundary_bytes)

    for part in parts[1:]:
        if part in (b"--\r\n", b"--"):
            continue
        if b"\r\n\r\n" not in part:
            continue
        headers_raw, file_body = part.split(b"\r\n\r\n", 1)
        if file_body.endswith(b"\r\n"):
            file_body = file_body[:-2]

        headers_text = headers_raw.decode("utf-8", errors="replace")
        if "filename=" not in headers_text:
            continue

        mime = "image/jpeg"
        for line in headers_text.splitlines():
            if line.lower().startswith("content-type:"):
                mime = line.split(":", 1)[1].strip()
                break

        return file_body, mime

    return None, None


def save_image(file_bytes, mime, dest_jpg):
    """Open image via PIL, resize if over 4K on long edge, save as JPEG."""
    img = PILImage.open(io.BytesIO(file_bytes))
    img = ImageOps.exif_transpose(img)  # apply EXIF rotation before resize
    # Flatten HEIC grid tiles and any alpha channel
    img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_LONG_EDGE:
        img.thumbnail((MAX_LONG_EDGE, MAX_LONG_EDGE), PILImage.LANCZOS)
        print(f"Resized {w}x{h} → {img.size[0]}x{img.size[1]}")
    img.save(dest_jpg, "JPEG", quality=85)
    print(f"Saved {os.path.basename(dest_jpg)} ({os.path.getsize(dest_jpg)} bytes)")


class UploadHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(fmt % args)

    def do_GET(self):
        if self.path in ("/qr.png", "/qr"):
            self._serve_qr()
            return
        if self.path in ("/manage-qr.png", "/manage-qr"):
            self._serve_qr(path="/manage")
            return
        if self.path == "/manage":
            self._serve_manage()
            return
        if self.path.startswith("/photo/"):
            self._serve_photo()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode())

    def _get_local_ip(self):
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "localhost"

    def _serve_qr(self, path=""):
        import qrcode
        url = f"http://{self._get_local_ip()}:{PORT}{path}"
        buf = io.BytesIO()
        qr = qrcode.QRCode(box_size=8, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        qr.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
        png = buf.getvalue()
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(png)
        print(f"QR served for {url}")

    def _serve_photo(self):
        filename = os.path.basename(self.path[len("/photo/"):])
        filepath = os.path.join(UPLOAD_DIR, filename)
        if not os.path.isfile(filepath):
            self._respond(404, "Not found")
            return
        with open(filepath, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Cache-Control", "max-age=60")
        self.end_headers()
        self.wfile.write(data)

    def _serve_manage(self):
        files = sorted(
            [f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))],
            key=lambda f: os.path.getmtime(os.path.join(UPLOAD_DIR, f)),
            reverse=True
        ) if os.path.isdir(UPLOAD_DIR) else []
        html = MANAGE_HTML.replace("__PHOTO_COUNT__", str(len(files)))
        photo_items = "".join(
            f'<div class="photo-item" id="item-{i}">'
            f'<img src="/photo/{f}" loading="lazy">'
            f'<button class="del-btn" onclick="deletePhoto(\'{f}\', {i})">&#128465;</button>'
            f'</div>'
            for i, f in enumerate(files)
        )
        html = html.replace("__PHOTO_ITEMS__", photo_items)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def do_DELETE(self):
        if self.path.startswith("/photo/"):
            filename = os.path.basename(self.path[len("/photo/"):])
            filepath = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(filepath):
                os.remove(filepath)
                print(f"Deleted {filename}")
                self._respond(200, "Deleted")
            else:
                self._respond(404, "Not found")
        else:
            self._respond(404, "Not found")

    def do_POST(self):
        if self.path != "/upload":
            self.send_response(404)
            self.end_headers()
            return

        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        file_bytes, mime = parse_multipart(content_type, body)

        if not file_bytes:
            self._respond(400, "No file found")
            return

        if mime not in ALLOWED_TYPES:
            self._respond(400, f"Unsupported type: {mime}")
            return

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        filename = str(uuid.uuid4())
        dest = os.path.join(UPLOAD_DIR, filename + ".jpg")

        if PILImage and mime != "image/gif":
            # Process all non-GIF images through PIL: normalise size, strip metadata, save as JPEG
            try:
                save_image(file_bytes, mime, dest)
            except Exception as e:
                print(f"Image processing failed: {e}")
                self._respond(500, f"Image processing failed: {e}")
                return
        else:
            # GIF: save raw to preserve animation; other formats if PIL not available
            ext = ".gif" if mime == "image/gif" else (mimetypes.guess_extension(mime) or ".jpg")
            dest = os.path.join(UPLOAD_DIR, filename + ext)
            with open(dest, "wb") as f:
                f.write(file_bytes)
            print(f"Saved raw {os.path.basename(dest)} ({len(file_bytes)} bytes)")

        self._respond(200, "OK")

    def _respond(self, code, msg):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(msg.encode())


if __name__ == "__main__":
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    server = HTTPServer(("0.0.0.0", PORT), UploadHandler)
    print(f"Photo upload server running on port {PORT}")
    print(f"Saving photos to: {UPLOAD_DIR}")
    print(f"Max image dimension: {MAX_LONG_EDGE}px")
    server.serve_forever()
