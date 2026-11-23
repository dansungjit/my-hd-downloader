import os, re, shutil, subprocess, tempfile, requests
from flask import Flask, request, send_file, after_this_request

app = Flask(__name__)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15"})

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
    return "Online 1080p Full HD Video API Running!"

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
    
