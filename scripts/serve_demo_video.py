"""Loopback-only preview server with byte ranges for MP4 chapter seeking."""

import argparse
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parents[1] / ".local/video-one/export"


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def send_head(self):
        self.remaining = None
        path = Path(self.translate_path(self.path))
        requested = self.headers.get("Range")
        if not requested or not path.is_file():
            return super().send_head()
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested)
        size = path.stat().st_size
        if not match or not any(match.groups()) or size == 0:
            self.send_error(416, "Unsupported range")
            return None
        first, last = match.groups()
        start = int(first) if first else max(0, size - int(last))
        end = min(int(last), size - 1) if first and last else size - 1
        if start >= size or start > end:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return None
        stream = path.open("rb")
        stream.seek(start)
        self.remaining = end - start + 1
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Content-Length", str(self.remaining))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        return stream

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def copyfile(self, source, outputfile):
        if self.remaining is None:
            return super().copyfile(source, outputfile)
        while self.remaining:
            chunk = source.read(min(64 * 1024, self.remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            self.remaining -= len(chunk)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", choices=("one", "two"), default="one")
    args = parser.parse_args()
    port = 18082 if args.video == "one" else 18083
    DIRECTORY = Path(__file__).resolve().parents[1] / f".local/video-{args.video}/export"
    print(f"Video preview: http://127.0.0.1:{port}/", flush=True)
    with ThreadingHTTPServer(("127.0.0.1", port), PreviewHandler) as server:
        server.serve_forever()
