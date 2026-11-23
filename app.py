import os, re, shutil, subprocess, tempfile, requests
from flask import Flask, request, send_file, after_this_request

app = Flask(__name__)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15"})

HTML_UI = """<!DOCTYPE html>
<html lang="en">
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>1080p Video Downloader</title>
<style>
  body { font-family: sans-serif; background: #111; color: #fff; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 90vh; margin: 0; padding: 20px; }
  .box { width: 100%; max-width: 400px; background: #1e1e1e; padding: 20px; border-radius: 14px; box-sizing: border-box; text-align: center; }
  input { width: 100%; padding: 14px; border-radius: 8px; border: 1px solid #444; background: #2a2a2a; color: #fff; font-size: 16px; box-sizing: border-box; margin-bottom: 12px; }
  button { width: 100%; padding: 14px; border-radius: 8px; border: none; background: #00c853; color: #000; font-size: 16px; font-weight: bold; cursor: pointer; margin-bottom: 10px; }
  .paste-btn { background: #2979ff; color: #fff; }
</style>
</head>
<body>
  <div class="box">
    <h3>1080p HD Downloader</h3>
    <form id="dlForm" action="/api/get_video" method="get">
      <input type="text" id="urlInput" name="url" placeholder="Paste Douyin / Xigua link..." required>
      <button type="button" class="paste-btn" onclick="pasteAndGo()">Paste & Download</button>
      <button type="submit">Download Video</button>
    </form>
  </div>
  <script>
    async function pasteAndGo() {
      try {
        const text = await navigator.clipboard.readText();
        document.getElementById('urlInput').value = text;
        if (text) document.getElementById('dlForm').submit();
      } catch (e) {
        alert('Clipboard permission allow karein ya box mein paste karke Download dabayein.');
      }
    }
  </script>
</body>
</html>"""

def extract_url(text):
    m = re.search(r"https?://[^\s]+", text)
    return m.group(0) if m else text.strip()

def get_douyin_1080p(share_url):
    res = SESSION.get(share_url, allow_redirects=True, timeout=8)
    m = re.search(r"/video/(\d+)", res.url)
    if m:
        vid = m.group(1)
        for endpoint in (f"https://www.iesdouyin.com/share/video/{vid}/", f"https://www.iesdouyin.com/xg/video/{vid}/"):
            html = SESSION.get(endpoint, timeout=8).text
            uri = re.search(r'"uri":"([a-zA-Z0-9_-]+)"', html)
            if uri:
                return f"https://aweme.snssdk.com/aweme/v1/play/?video_id={uri.group(1)}&ratio=1080p&line=0"
    return None

@app.route("/")
def home():
    return HTML_UI

@app.route("/api/get_video")
def get_video():
    raw_url = request.args.get("url", "")
    if not raw_url:
        return "Missing url", 400
    url = extract_url(raw_url)
    tmp_dir = tempfile.mkdtemp()
    final_mp4 = os.path.join(tmp_dir, "fullhd.mp4")

    try:
        direct_url = get_douyin_1080p(url)
        downloaded = False
        if direct_url:
            r = SESSION.get(direct_url, stream=True, timeout=20)
            if r.status_code == 200:
                with open(final_mp4, "wb") as f:
                    for chunk in r.iter_content(1024 * 512):
                        f.write(chunk)
                downloaded = os.path.exists(final_mp4) and os.path.getsize(final_mp4) > 50000

        if not downloaded:
            subprocess.run([
                "yt-dlp", "-f", "best[height<=1080][ext=mp4]/bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
                "--merge-output-format", "mp4", "-o", final_mp4, url
            ], check=True)

        @after_this_request
        def cleanup(response):
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return response

        return send_file(final_mp4, mimetype="video/mp4", as_attachment=True, download_name="FullHD_1080p.mp4")

    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return str(e), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port)
    
