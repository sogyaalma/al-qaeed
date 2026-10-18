#!/usr/bin/env python3
"""Local production-package preview with _headers and custom 404 responses.

Not Cloudflare's routing emulator and not a production server.
  python3 tools/serve.py --port 8000
"""
import argparse
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # This project has one /* rule; fail in main if that contract changes.
        for line in (ROOT / "dist/_headers").read_text(encoding="utf-8").splitlines():
            if line.startswith("  ") and ":" in line:
                name, value = line.strip().split(":", 1)
                # Allow the Arena preview to embed this LOCAL preview, not production.
                if name.lower() == "x-frame-options":
                    continue
                if name.lower() == "content-security-policy":
                    value = value.replace("frame-ancestors 'none'", "frame-ancestors *")
                self.send_header(name, value.strip())
        super().end_headers()

    def send_error(self, code, message=None, explain=None):
        if code != HTTPStatus.NOT_FOUND:
            return super().send_error(code, message, explain)
        body = (ROOT / "dist/404.html").read_bytes()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def list_directory(self, path):
        self.send_error(HTTPStatus.NOT_FOUND)
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not (ROOT / "dist/404.html").is_file():
        raise SystemExit("Run tools/build.py and tools/package.py first")
    rules = [line for line in (ROOT / "dist/_headers").read_text().splitlines()
             if line and not line.startswith(" ")]
    if rules != ["/*"]:
        raise SystemExit("Preview only supports the project's single /* headers rule")
    server = ThreadingHTTPServer(("0.0.0.0", args.port), partial(Handler, directory=str(ROOT / "dist")))
    print(f"Previewing dist/ on port {args.port}; local framing exception only", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
