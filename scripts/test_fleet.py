import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fleet


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "caches/go").mkdir(parents=True)
        (self.root / "caches/go/object").write_text("rebuildable")
        (self.root / "evidence").mkdir()
        (self.root / "evidence/report.json").write_text("private proof")
        self.config = {"root": str(self.root), "cache_paths": ["caches"], "native": [], "services": []}

    def test_cache_reset_preserves_evidence_and_directory(self):
        self.assertTrue(fleet.maintain_host(self.config)["ok"])
        self.assertEqual(list((self.root / "caches").iterdir()), [])
        self.assertEqual((self.root / "evidence/report.json").read_text(), "private proof")

    def test_rejects_root_parent_and_symlink_escape(self):
        (self.root / "escape").symlink_to(self.root.parent, target_is_directory=True)
        for path in [".", "../outside", "escape", "escape/child", str(self.root / "caches")]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                fleet.owned(self.root, path)

    def test_symlink_in_cache_is_removed_without_touching_target(self):
        (self.root / "caches/proof-link").symlink_to(self.root / "evidence", target_is_directory=True)
        fleet.clear_caches(self.config, self.root)
        self.assertEqual((self.root / "evidence/report.json").read_text(), "private proof")

    def test_drain_and_resume_routing_even_when_cleanup_fails(self):
        directory = self.root / "native/example"
        directory.mkdir(parents=True)
        (directory / ".runner").write_text(json.dumps({"gitHubUrl": "https://github.com/owner/repo", "agentId": 4}))
        svc = {"kind": "systemd", "unit": "example.service"}
        self.config["native"] = [{"name": "example", "directory": "native/example", "repository": "owner/repo", "service": svc}]
        calls = []

        def api(endpoint, method="GET", body=None):
            calls.append((endpoint, method, body))
            if endpoint.endswith("/labels") and method == "GET":
                return {"labels": [{"name": "self-hosted", "type": "read-only"}, {"name": "example", "type": "custom"}]}
            return {"busy": False}

        with patch.object(fleet, "gh", side_effect=api), patch.object(fleet, "active", return_value=True), patch.object(fleet, "service") as service, patch.object(fleet, "clear_caches", side_effect=OSError("disk failure")):
            result = fleet.maintain_host(self.config)
        self.assertFalse(result["ok"])
        self.assertEqual([c.args[1] for c in service.call_args_list], ["stop", "start"])
        self.assertTrue(any(method == "DELETE" for _, method, _ in calls))
        self.assertEqual(calls[-1][1:], ("POST", {"labels": ["example"]}))
        self.assertEqual((self.root / "evidence/report.json").read_text(), "private proof")


if __name__ == "__main__":
    unittest.main()
