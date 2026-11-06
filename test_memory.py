import concurrent.futures
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("memory.py")


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "RULES.md").write_text("默认中文，诚实报告。", encoding="utf-8")
        grants = {actor: ["read", "write", "export"] for actor in ["test", *[f"test_{n}" for n in range(24)]]}
        self.policy = {"version": 1, "default": "deny", "projects": {
            project: {"status": "approved", "grants": grants.copy(), "approval_source": "isolated-test-fixture"} for project in ("pilot", "other")}}
        self.save_policy()

    def save_policy(self):
        (self.root / "permissions.json").write_text(json.dumps(self.policy))

    def tearDown(self):
        self.temp.cleanup()

    def command(self, *args, body=None, check=True):
        args = list(args)
        if "--actor" not in args:
            args += ["--actor", "test"]
        if "--project" not in args:
            args += ["--project", "pilot"]
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), *args],
                              input=body, text=True, capture_output=True, check=check)

    def add(self, n, supersedes=""):
        return json.loads(self.command("add", "--actor", f"test_{n}", "--project", "pilot",
            "--task", "readwrite", "--kind", "progress", "--status", "active",
            "--source", "isolated-test", "--supersedes", supersedes,
            body=f"中文检索 并发记录 {n}").stdout)

    def test_concurrent_writes_are_complete(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            rows = list(pool.map(self.add, range(24)))
        self.assertEqual(len({r["id"] for r in rows}), 24)
        found = json.loads(self.command("search", "中文检索").stdout)
        self.assertEqual(len(found), 24)
        handoff = (self.root / "handoffs/pilot.md").read_text()
        for row in rows:
            self.assertTrue(row["handoff_updated"])
            self.assertIn(row["id"], handoff)

    def test_corrections_keep_history_and_concurrent_heads(self):
        old = self.add(1)
        a, b = self.add(2, old["id"]), self.add(3, old["id"])
        heads = json.loads(self.command("status").stdout)
        self.assertEqual({r["id"] for r in heads}, {a["id"], b["id"]})
        self.assertEqual(len(json.loads(self.command("search", "中文检索", "--all").stdout)), 3)
        self.assertEqual(len(json.loads(self.command("search", "中文检索").stdout)), 2)
        handoff = (self.root / "handoffs/pilot.md").read_text()
        self.assertNotIn(old["id"], handoff)
        self.assertIn(a["id"], handoff)
        self.assertIn(b["id"], handoff)

    def test_bad_reference_and_empty_payload_do_not_write(self):
        self.assertRaises(subprocess.CalledProcessError, self.add, 1, "missing")
        p = self.command("add", "--actor", "test", "--project", "pilot", "--task", "t",
            "--kind", "finding", "--status", "active", "--source", "test", body="", check=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(len(list(self.root.glob("records/*.md"))), 0)

    def test_export_is_scoped_and_excludes_obsolete_record(self):
        (self.root / "RULES.md").write_text("默认中文，诚实报告。", encoding="utf-8")
        old = self.add(1)
        new = self.add(2, old["id"])
        snapshot = self.command("export", "--project", "pilot").stdout
        self.assertIn(new["id"], snapshot)
        self.assertNotIn(old["id"], snapshot)
        self.assertIn("手工快照", snapshot)
        empty = self.command("export", "--project", "other").stdout
        self.assertNotIn(new["id"], empty)

    def test_handoff_failure_does_not_hide_successful_save(self):
        (self.root / "handoffs").write_text("blocked by test fixture")
        result = self.add(1)
        self.assertFalse(result["handoff_updated"])
        self.assertTrue((self.root / "records" / (result["id"] + ".md")).exists())

    def test_refresh_uses_latest_rules_without_new_record(self):
        row = self.add(1)
        (self.root / "RULES.md").write_text("新版本共同规则")
        result = json.loads(self.command("handoff", "--project", "pilot").stdout)
        self.assertTrue(result["handoff_updated"])
        content = (self.root / "handoffs/pilot.md").read_text()
        self.assertIn("新版本共同规则", content)
        self.assertIn(row["id"], content)
        self.assertEqual(len(list(self.root.glob("records/*.md"))), 1)
        self.assertNotEqual(self.command("handoff", "--project", "../outside", check=False).returncode, 0)

    def test_project_queries_filter_before_limit(self):
        old = self.add(1)
        new = self.add(2, old["id"])
        self.command("add", "--actor", "test", "--project", "other", "--task", "t",
            "--kind", "progress", "--status", "active", "--source", "isolated-test",
            body="中文检索 other project")
        for args in [("status",), ("search", "中文检索"), ("recent", "--limit", "1")]:
            rows = json.loads(self.command(*args, "--project", "pilot").stdout)
            self.assertEqual([r["id"] for r in rows], [new["id"]])
        history = json.loads(self.command("search", "中文检索", "--all", "--project", "pilot").stdout)
        self.assertEqual({r["id"] for r in history}, {old["id"], new["id"]})
        self.assertNotEqual(self.command("status", "--project", "unknown", check=False).returncode, 0)


    def test_pending_project_denies_all_and_keeps_existing_bytes(self):
        self.add(1)
        before = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file() and p.name != "permissions.json"}
        self.policy["projects"]["pilot"]["status"] = "pending"
        self.save_policy()
        for args in [("brief",), ("status",), ("recent",), ("search", "中文"), ("export",), ("handoff",)]:
            p = self.command(*args, check=False)
            self.assertNotEqual(p.returncode, 0)
            self.assertEqual(p.stdout, "")
        self.assertRaises(subprocess.CalledProcessError, self.add, 2)
        after = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file() and p.name != "permissions.json"}
        self.assertEqual(before, after)

    def test_actor_and_operation_are_separate(self):
        self.add(1)
        self.policy["projects"]["pilot"]["grants"]["test_2"] = ["read"]
        self.policy["projects"]["pilot"]["grants"]["test_3"] = ["write"]
        self.save_policy()
        self.assertEqual(self.command("status", "--actor", "test_2").returncode, 0)
        self.assertRaises(subprocess.CalledProcessError, self.add, 2)
        self.assertNotEqual(self.command("handoff", "--actor", "test_2", check=False).returncode, 0)
        self.assertNotEqual(self.command("status", "--actor", "unknown", check=False).returncode, 0)
        before = (self.root / "handoffs/pilot.md").read_bytes()
        saved = self.add(3)
        self.assertEqual(saved["handoff_skipped"], "export_not_authorized")
        self.assertEqual(saved["classification"], "unreviewed")
        self.assertEqual(before, (self.root / "handoffs/pilot.md").read_bytes())
        self.assertNotEqual(self.command("search", "中文", "--actor", "test_3", check=False).returncode, 0)

    def test_missing_invalid_policy_and_legacy_commands_fail_closed(self):
        for args in [("status",), ("recent",), ("brief",), ("search", "中文"), ("export", "--project", "pilot")]:
            p = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), *args],capture_output=True,text=True)
            self.assertNotEqual(p.returncode, 0)
            self.assertEqual(p.stdout, "")
        (self.root / "permissions.json").unlink()
        self.assertRaises(subprocess.CalledProcessError, self.add, 1)
        (self.root / "permissions.json").write_text("not json")
        self.assertNotEqual(self.command("status", check=False).returncode, 0)
        for invalid in [[], {"version": 1, "default": "deny", "projects": []}]:
            (self.root / "permissions.json").write_text(json.dumps(invalid))
            self.assertNotEqual(self.command("status", check=False).returncode, 0)
        self.policy["projects"]["pilot"]["grants"]["test"] = "readwrite"
        self.save_policy()
        self.assertNotEqual(self.command("status", check=False).returncode, 0)
        self.policy["projects"]["pilot"]["grants"]["test"] = ["read"]
        self.policy["projects"]["pilot"]["approval_source"] = None
        self.save_policy()
        self.assertNotEqual(self.command("status", check=False).returncode, 0)

    def test_brief_does_not_expose_other_project_map(self):
        (self.root / "PROJECTS.md").write_text("secret-other-project")
        p = self.command("brief")
        self.assertIn("默认中文", p.stdout)
        self.assertNotIn("secret-other-project", p.stdout)
        result = json.loads(self.command("permissions", "--project", "unknown").stdout)
        self.assertEqual(result["allowed"], [])

    def test_show_source_is_project_scoped(self):
        row = self.add(1)
        shown = json.loads(self.command("show", "--id", row["id"]).stdout)
        self.assertEqual(shown["source"], "isolated-test")
        self.assertEqual(shown["id"], row["id"])
        denied = self.command("show", "--id", row["id"], "--project", "other", check=False)
        self.assertNotEqual(denied.returncode, 0)
        self.assertNotIn("中文检索", denied.stdout)

    def test_activity_is_bounded_and_contains_no_content(self):
        self.policy["projects"]["pilot"]["grants"]["codex"] = ["read", "write"]
        self.save_policy()
        row = json.loads(self.command("add", "--actor", "codex", "--task", "t", "--kind", "progress", "--status", "done", "--source", "PRIVATE_SOURCE", body="PRIVATE_BODY").stdout)
        for _ in range(2):
            self.command("search", "PRIVATE_QUERY", "--actor", "codex")
        self.command("show", "--id", row["id"], "--actor", "minimax", check=False)
        events = list((self.root / "activity").glob("*.json"))
        self.assertEqual(len(events), 3)
        text = "".join(p.read_text() for p in events)+(self.root / "dashboard.html").read_text()
        for secret in ("PRIVATE_BODY", "PRIVATE_SOURCE", "PRIVATE_QUERY"):
            self.assertNotIn(secret, text)
        self.assertIn("denied", text)
        self.assertFalse((self.root / "handoffs").exists())


if __name__ == "__main__":
    unittest.main()
