"""Serve the prebuilt V3 frontend locally; no Node or Docker is needed to run it."""

from argparse import ArgumentParser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main():
    parser = ArgumentParser()
    parser.add_argument("--port", type=int, default=5500)
    args = parser.parse_args()
    directory = Path(__file__).resolve().parents[1] / "frontend/dist"
    if not (directory / "index.html").exists():
        parser.error(
            "Missing frontend/dist build. Restore it from the handoff ZIP, or run npm ci and npm run build in frontend."
        )
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"DMS V3 frontend: http://127.0.0.1:{args.port} (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
