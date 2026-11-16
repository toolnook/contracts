import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ledgerlite.asset_scope_api import AssetScopeAPIHandler


CSV_HEADER = "asset_code,asset_issuer,amount_in_issued_asset_units,as_of,source_ref\n"


class AssetScopeAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), AssetScopeAPIHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_compare_returns_report_for_three_csv_snapshots(self):
        payload = {
            "asset_code": "USD",
            "asset_issuer": "GISSUER",
            "onchain_csv": CSV_HEADER + "USD,GISSUER,100,2026-11-01,onchain-1\n",
            "ledger_csv": CSV_HEADER + "USD,GISSUER,100,2026-11-01,ledger-1\n",
            "reserves_csv": CSV_HEADER + "USD,GISSUER,101,2026-11-01,reserve-1\n",
        }
        response = self._post(payload)

        self.assertEqual(response.status, 200)
        report = json.loads(response.read())
        self.assertEqual(report["status"], "reconciled")
        self.assertEqual(report["sources"]["onchain"]["amount"], "100")

    def test_invalid_csv_returns_a_client_error(self):
        payload = {
            "asset_code": "USD",
            "asset_issuer": "GISSUER",
            "onchain_csv": "not,a,valid,snapshot\n",
            "ledger_csv": CSV_HEADER + "USD,GISSUER,100,2026-11-01,ledger-1\n",
            "reserves_csv": CSV_HEADER + "USD,GISSUER,101,2026-11-01,reserve-1\n",
        }

        with self.assertRaises(HTTPError) as raised:
            self._post(payload)

        self.assertEqual(raised.exception.code, 400)
        self.assertIn("missing required columns", raised.exception.read().decode())

    def _post(self, payload):
        request = Request(
            self.base_url + "/api/assetscope/compare",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return urlopen(request, timeout=5)


if __name__ == "__main__":
    unittest.main()
