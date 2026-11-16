"""Local HTTP API for AssetScope snapshot comparisons."""

from __future__ import annotations

import argparse
import json
import tempfile
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .asset_scope import AssetScopeInputError, compare_csv_snapshots


MAX_REQUEST_BYTES = 2 * 1024 * 1024
COMPARE_PATH = "/api/assetscope/compare"
HEALTH_PATH = "/api/assetscope/health"


class AssetScopeAPIHandler(BaseHTTPRequestHandler):
    """Accept normalized snapshot CSV contents and return a comparison report."""

    def do_GET(self) -> None:
        if self.path != HEALTH_PATH:
            self._send_json(404, {"error": "Not found"})
            return
        self._send_json(200, {"status": "ok"})

    def do_POST(self) -> None:
        if self.path != COMPARE_PATH:
            self._send_json(404, {"error": "Not found"})
            return
        if self.headers.get_content_type() != "application/json":
            self._send_json(415, {"error": "Content-Type must be application/json"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._send_json(400, {"error": "A valid Content-Length header is required"})
            return
        if content_length < 0:
            self._send_json(400, {"error": "Content-Length must be non-negative"})
            return
        if content_length > MAX_REQUEST_BYTES:
            self._send_json(413, {"error": "Request exceeds the 2 MiB limit"})
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            report = self._compare(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, AssetScopeInputError, OSError) as error:
            self._send_json(400, {"error": str(error)})
            return

        self._send_json(200, report)

    def _compare(self, payload: Any) -> dict[str, object]:
        if not isinstance(payload, dict):
            raise AssetScopeInputError("Request body must be a JSON object")

        asset_code = self._required_string(payload, "asset_code")
        asset_issuer = self._required_string(payload, "asset_issuer", allow_empty=True)
        csv_values = {
            key: self._required_string(payload, key)
            for key in ("onchain_csv", "ledger_csv", "reserves_csv")
        }

        raw_tolerance = payload.get("tolerance", "0")
        if not isinstance(raw_tolerance, str):
            raise AssetScopeInputError("tolerance must be a decimal string")
        try:
            tolerance = Decimal(raw_tolerance)
        except InvalidOperation as error:
            raise AssetScopeInputError("tolerance must be a decimal string") from error
        if not tolerance.is_finite() or tolerance < 0:
            raise AssetScopeInputError("tolerance must be finite and non-negative")

        with tempfile.TemporaryDirectory(prefix="assetscope-") as directory:
            paths = {}
            for name, csv_content in csv_values.items():
                path = Path(directory) / f"{name.removesuffix('_csv')}.csv"
                path.write_text(csv_content, encoding="utf-8")
                paths[name] = path

            report = compare_csv_snapshots(
                asset_code=asset_code,
                asset_issuer=asset_issuer,
                onchain_path=paths["onchain_csv"],
                ledger_path=paths["ledger_csv"],
                reserves_path=paths["reserves_csv"],
                tolerance=tolerance,
            )
        return report.to_dict()

    @staticmethod
    def _required_string(payload: dict[str, Any], key: str, *, allow_empty: bool = False) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or (not allow_empty and not value.strip()):
            raise AssetScopeInputError(f"{key} must be a non-empty string")
        return value

    def _send_json(self, status: int, body: dict[str, object]) -> None:
        encoded = json.dumps(body, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the local AssetScope API")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8091, help="Port (default: 8091)")
    args = parser.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), AssetScopeAPIHandler)
    print(f"AssetScope API listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
