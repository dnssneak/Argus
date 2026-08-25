import unittest
from services.change_detector import ChangeDetector


class TestChangeDetector(unittest.TestCase):

    def test_compare_asset_states_added_ports(self):
        prev_snapshot = {
            "id": 1,
            "name": "api.example.com",
            "ip_address": "203.0.113.10",
            "services": [
                {"port": 80, "protocol": "tcp", "service_name": "http", "version": "Nginx 1.24", "state": "open"},
                {"port": 443, "protocol": "tcp", "service_name": "https", "version": "Nginx 1.24", "state": "open"}
            ],
            "technologies": [{"name": "Nginx", "version": "1.24", "category": "Web"}],
            "endpoints": []
        }

        new_results = {
            "ports": {
                "ip": "203.0.113.10",
                "services": [
                    {"port": 80, "protocol": "tcp", "service": "http", "version": "Nginx 1.24", "state": "open"},
                    {"port": 443, "protocol": "tcp", "service": "https", "version": "Nginx 1.24", "state": "open"},
                    {"port": 8443, "protocol": "tcp", "service": "alt-https", "version": "Nginx 1.26", "state": "open"}
                ]
            },
            "web": {
                "technologies": [
                    {"name": "Nginx", "version": "1.26", "category": "Web"}
                ],
                "endpoints": [
                    {"path": "/api/admin", "method": "GET", "status_code": 200}
                ]
            }
        }

        res = ChangeDetector.compare_asset_states(prev_snapshot, new_results)

        self.assertTrue(res["has_changes"])
        self.assertGreaterEqual(len(res["added"]), 2)  # Port 8443 & Endpoint /api/admin
        self.assertGreaterEqual(len(res["changed"]), 1)  # Nginx version changed 1.24 -> 1.26
        self.assertIn("+", res["summary"])
        self.assertIn("~", res["summary"])

    def test_compare_scans(self):
        scan_a = {
            "id": 1,
            "results_parsed": {
                "ports": {"services": [{"port": 80, "protocol": "tcp", "service": "http"}]},
                "web": {"technologies": [{"name": "React", "version": "17.0"}]}
            }
        }
        scan_b = {
            "id": 2,
            "results_parsed": {
                "ports": {"services": [
                    {"port": 80, "protocol": "tcp", "service": "http"},
                    {"port": 8080, "protocol": "tcp", "service": "http-alt"}
                ]},
                "web": {"technologies": [{"name": "React", "version": "18.0"}]}
            }
        }

        diff = ChangeDetector.compare_scans(scan_a, scan_b)
        self.assertEqual(diff["scan_a_id"], 1)
        self.assertEqual(diff["scan_b_id"], 2)
        self.assertEqual(len(diff["ports_diff"]), 2)
        self.assertEqual(len(diff["tech_diff"]), 1)
        self.assertEqual(diff["tech_diff"][0]["status"], "CHANGED")


if __name__ == "__main__":
    unittest.main()
