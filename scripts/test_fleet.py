import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
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

    def test_cleanup_removes_read_only_go_module_directories(self):
        module = self.root / "caches/go/example.com/module@v1.0.0"
        nested = module / "source"
        nested.mkdir(parents=True)
        source = nested / "module.go"
        source.write_text("read-only module")
        source.chmod(0o444)
        nested.chmod(0o555)
        module.chmod(0o555)
        self.assertTrue(fleet.maintain_host(self.config)["ok"])
        self.assertEqual(list((self.root / "caches").iterdir()), [])
        self.assertEqual((self.root / "evidence/report.json").read_text(), "private proof")

    def test_read_only_cache_cleanup_does_not_chmod_symlink_target(self):
        evidence = self.root / "evidence"
        evidence.chmod(0o555)
        self.addCleanup(evidence.chmod, 0o755)
        (self.root / "caches/go/report-link").symlink_to(evidence, target_is_directory=True)
        (self.root / "caches/go").chmod(0o555)
        fleet.clear_caches(self.config, self.root)
        self.assertEqual(evidence.stat().st_mode & 0o777, 0o555)
        self.assertEqual((evidence / "report.json").read_text(), "private proof")

    def test_rejects_root_parent_and_symlink_escape(self):
        (self.root / "escape").symlink_to(self.root.parent, target_is_directory=True)
        for path in [".", "../outside", "escape", "escape/child", str(self.root / "caches")]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                fleet.owned(self.root, path)

    def test_symlink_in_cache_is_removed_without_touching_target(self):
        (self.root / "caches/proof-link").symlink_to(self.root / "evidence", target_is_directory=True)
        fleet.clear_caches(self.config, self.root)
        self.assertEqual((self.root / "evidence/report.json").read_text(), "private proof")

    def test_cleanup_rejects_installed_tools_including_parent_work_directory(self):
        tool = self.root / "native/example/_work/_tool/go/1.27.3/x64/bin/go"
        tool.parent.mkdir(parents=True)
        tool.write_text("installed compiler")
        self.config["native"] = [{"directory": "native/example"}]
        for relative in ["native/example/_work", "native/example/_work/_tool", "native/example/_work/*"]:
            with self.subTest(relative=relative):
                self.config["cache_paths"] = [relative]
                result = fleet.maintain_host(self.config)
                self.assertFalse(result["ok"])
                self.assertIn("installed software", result["error"])
                self.assertEqual(tool.read_text(), "installed compiler")

    def test_cleanup_preserves_tools_while_removing_job_data(self):
        tool = self.root / "tools/actions/go/1.27.3/x64/bin/go"
        tool.parent.mkdir(parents=True)
        tool.write_text("installed compiler")
        self.assertTrue(fleet.maintain_host(self.config)["ok"])
        self.assertEqual(tool.read_text(), "installed compiler")
        self.config["cache_paths"] = ["tools/*"]
        self.assertFalse(fleet.maintain_host(self.config)["ok"])

    def test_cleanup_preserves_runner_update_links_and_their_targets(self):
        native = self.root / "native/example"
        for name in ["bin", "externals"]:
            target = native / (name + ".2.338.2")
            target.mkdir(parents=True)
            (target / "installed").write_text("runner software")
            (native / name).symlink_to(target, target_is_directory=True)
        self.config["native"] = [{"directory": "native/example"}]
        fleet.clear_caches(self.config, self.root)
        self.assertEqual(list((self.root / "caches").iterdir()), [])
        for name in ["bin", "externals"]:
            link = native / name
            self.assertTrue(link.is_symlink())
            self.assertEqual((link / "installed").read_text(), "runner software")
            self.config["cache_paths"] = ["native/example/" + name + ".2.338.2"]
            with self.assertRaisesRegex(ValueError, "installed software"):
                fleet.clear_caches(self.config, self.root)
            self.config["cache_paths"] = ["native/example/" + name]
            with self.assertRaisesRegex(ValueError, "unsafe owned path"):
                fleet.clear_caches(self.config, self.root)

    def test_protected_runner_link_cannot_escape_ci_root(self):
        native = self.root / "native/example"
        native.mkdir(parents=True)
        (native / "bin").symlink_to(self.root.parent, target_is_directory=True)
        self.config["native"] = [{"directory": "native/example"}]
        with self.assertRaisesRegex(ValueError, "unsafe owned path"):
            fleet.clear_caches(self.config, self.root)
        self.assertEqual((self.root / "caches/go/object").read_text(), "rebuildable")

    def test_image_retention_keeps_configured_worker_and_cleanup_images(self):
        self.config.update(image_retention=[{"repository_prefix": "runner-", "days": 1}],
                           cleanup_image="runner-current:local")
        with patch.object(fleet, "run", return_value=SimpleNamespace(stdout='{"Repository":"runner-current","Tag":"local"}\n')) as command:
            self.assertEqual(fleet.prune_owned_images(self.config), [])
            self.assertEqual(command.call_count, 1)

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

    def test_image_retention_removes_only_expired_owned_tag(self):
        self.config["image_retention"] = [{"repository_prefix": "application-check-", "days": 14}]
        calls = []

        def docker(args, **kwargs):
            calls.append(args)
            if args[2] == "ls":
                return SimpleNamespace(stdout='{"Repository":"unrelated","Tag":"latest"}\n{"Repository":"application-check-old","Tag":"latest"}\n{"Repository":"application-check-new","Tag":"latest"}\n')
            if args[2] == "inspect":
                return SimpleNamespace(stdout="2010-01-01T00:00:00Z" if "-old:" in args[3] else "2100-01-01T00:00:00Z")
            return SimpleNamespace(stdout="")

        with patch.object(fleet, "run", side_effect=docker):
            self.assertEqual(fleet.prune_owned_images(self.config), ["application-check-old:latest"])
        self.assertEqual([x for x in calls if x[2] == "rm"], [["docker", "image", "rm", "application-check-old:latest"]])

    def test_waits_for_github_assignment_even_before_manager_reports_busy(self):
        (self.root / "manager.toml").write_text('[[scaleset]]\nurl="https://github.com/owner/repo"\n')
        self.config.update(manager_config="manager.toml", quiet_seconds=0)
        with patch.object(fleet, "gh", side_effect=[{"workflow_runs": [{"id": 1}]}, {"jobs": [{"status": "in_progress"}]}, {"workflow_runs": []}]) as api, patch.object(fleet.time, "sleep") as sleep:
            fleet.wait_manager_idle(self.config, self.root)
        self.assertEqual(api.call_count, 3)
        sleep.assert_called_once_with(5)


if __name__ == "__main__":
    unittest.main()
