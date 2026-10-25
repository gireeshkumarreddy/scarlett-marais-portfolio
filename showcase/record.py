"""Record the launch film: plays showcase/stage.html frame by frame in headless Chrome and encodes an MP4.

Usage:
  python showcase/record.py                          # full 40 s film, 1920x1080 at 60 fps
  python showcase/record.py --stills 6,20,42         # no video, just JPEG stills at those seconds
  python showcase/record.py --start 20 --end 30      # render only part of the film

Needs: pip install playwright, Google Chrome, ffmpeg on PATH.
"""
import argparse
import base64
import functools
import http.server
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent

ap = argparse.ArgumentParser()
ap.add_argument("--fps", type=int, default=60)
ap.add_argument("--out", default=str(ROOT / "video" / "scarlett-marais-launch.mp4"))
ap.add_argument("--start", type=float, default=0)
ap.add_argument("--end", type=float, default=None)
ap.add_argument("--stills", default="", help="comma-separated seconds; renders stills only")
ap.add_argument("--crf", type=int, default=16)
args = ap.parse_args()


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT)))
port = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def poll(frame, expr, timeout=60):
    # the page clock is frozen, so poll from Python instead of wait_for_function
    end = time.time() + timeout
    while time.time() < end:
        if frame.evaluate(expr):
            return
        time.sleep(0.15)
    raise TimeoutError(expr)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True, args=["--hide-scrollbars", "--font-render-hinting=none"])
    ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    ctx.add_init_script(path=str(ROOT / "showcase" / "vclock.js"))
    page = ctx.new_page()
    page.on("pageerror", lambda e: print("page error:", e, file=sys.stderr))
    page.goto(f"http://127.0.0.1:{port}/showcase/stage.html", wait_until="load")
    site = next(f for f in page.frames if "/index.html" in f.url)

    site.evaluate("document.querySelectorAll('img[loading=lazy]').forEach(i => { i.loading = 'eager'; })")
    for u in ["1676576844102-89be768745bb", "1728857442002-5fdf4bcebde2", "1579752515149-489d8d711342", "1686668571985-8fd9e7cae040"]:
        site.evaluate(f"new Image().src = 'https://images.unsplash.com/photo-{u}?auto=format&fit=crop&w=1000&q=80'")
    poll(site, "window.__lenis !== undefined && document.fonts.status === 'loaded' && [...document.images].every(i => i.complete)")
    poll(page, "document.fonts.status === 'loaded' && typeof window.__init === 'function'")
    time.sleep(1.0)
    page.evaluate("__init()")

    fps = args.fps
    duration = page.evaluate("__meta.duration")
    total = int(round(duration * fps))
    first = int(round(args.start * fps))
    last = min(total, int(round(args.end * fps))) if args.end else total
    stills = {int(round(float(s) * fps)): float(s) for s in args.stills.split(",") if s.strip()}
    if stills:
        last = min(total, max(stills) + 1)
    cdp = ctx.new_cdp_session(page)

    enc = None
    if not stills:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        enc = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "mjpeg", "-i", "-",
             "-c:v", "libx264", "-preset", "slow", "-crf", str(args.crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", args.out],
            stdin=subprocess.PIPE)
    still_dir = ROOT / "video" / "stills"
    if stills:
        still_dir.mkdir(parents=True, exist_ok=True)

    dt = 1000.0 / fps
    pos, down, t0 = None, False, time.time()
    for f in range(last):
        st = page.evaluate("__frame()")
        xy = (round(st["x"], 1), round(st["y"], 1))
        if xy != pos:
            page.mouse.move(*xy)
            pos = xy
        if st["down"] != down:
            (page.mouse.down if st["down"] else page.mouse.up)()
            down = st["down"]
        for k in st["keys"]:
            page.keyboard.type(k)
        page.evaluate(f"__advance({dt})")
        if st["siteRun"]:
            site.evaluate(f"__advance({dt * st.get('siteSpeed', 1)})")

        if (enc and f >= first) or f in stills:
            shot = cdp.send("Page.captureScreenshot", {"format": "jpeg", "quality": 94, "optimizeForSpeed": True})
            data = base64.b64decode(shot["data"])
            if enc and f >= first:
                enc.stdin.write(data)
            if f in stills:
                (still_dir / f"t{stills[f]:06.2f}.jpg").write_bytes(data)
        if f % (fps * 5) == 0:
            el = time.time() - t0
            print(f"{f / fps:5.1f}s / {last / fps:.0f}s   elapsed {el:5.0f}s", flush=True)

    if enc:
        enc.stdin.close()
        enc.wait()
        print("wrote", args.out)
    browser.close()
httpd.shutdown()
