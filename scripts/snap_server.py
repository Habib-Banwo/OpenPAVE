#!/usr/bin/env python3
"""Serve USB-camera JPEGs using the demo's validated OpenCV capture sequence."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import signal
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--device", default="/dev/video0",
        help="USB-camera device path (default: /dev/video0; e.g. /dev/video2)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="HTTP bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8090, help="HTTP port (default: 8090)")
    args = parser.parse_args()

    cap = None

    def stop(_signum, _frame) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    try:
        import cv2

        class SnapshotHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                try:
                    for _ in range(2):
                        cap.read()
                    ok, frame = cap.read()
                    if not ok or frame is None:
                        raise RuntimeError("failed to capture a frame")
                    ok, jpg = cv2.imencode(
                        ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85]
                    )
                    if not ok or jpg is None:
                        raise RuntimeError("failed to encode a JPEG")
                    data = jpg.tobytes()
                except Exception as exc:
                    print(
                        f"snapshot capture failed for {args.device}: {exc}",
                        file=sys.stderr, flush=True,
                    )
                    self.send_response(503)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *_args) -> None:
                pass

        # Bind before opening the camera: a duplicate server must not take the device.
        with HTTPServer((args.host, args.port), SnapshotHandler) as server:
            cap = cv2.VideoCapture(args.device, cv2.CAP_V4L2)
            if not cap.isOpened():
                raise RuntimeError(f"cannot open camera device {args.device}")
            print(
                f"snapshot server ready: {args.device} -> {args.host}:{args.port}",
                flush=True,
            )
            server.serve_forever()
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"snapshot server failed: {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        if cap is not None:
            cap.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
