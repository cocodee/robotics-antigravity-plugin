"""Packaging checks; no simulator or robot hardware required."""
import tempfile
from pathlib import Path
import unittest

from export_skills import PLUGIN, export


class ExportTests(unittest.TestCase):
    def test_bundle_preserves_code_and_localizes_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "bundle"
            names = {p.parent.name for p in (PLUGIN / "skills").glob("*/SKILL.md")}
            self.assertEqual(export(target), len(names))
            self.assertTrue((target / "LICENSE").is_file())
            for name in names:
                skill = target / name
                text = (skill / "SKILL.md").read_text()
                self.assertIn("references/shared-rules/agent_runtime.md", text)
                self.assertNotIn("../../rules/", text)
                rules = skill / "references/shared-rules"
                self.assertTrue((rules / "agent_runtime.md").is_file())
                # Rules can still resolve their links to sibling skills.
                self.assertTrue((rules / "../../../blender-creation/SKILL.md").is_file())
                for source in (PLUGIN / "skills" / name).rglob("*.py"):
                    self.assertEqual(source.read_bytes(),
                                     (skill / source.relative_to(PLUGIN / "skills" / name)).read_bytes())
            with self.assertRaises(ValueError):
                export(target)

    def test_refuses_source_overlap(self):
        with self.assertRaises(ValueError):
            export(PLUGIN / "must-not-create")
        self.assertFalse((PLUGIN / "must-not-create").exists())


if __name__ == "__main__":
    unittest.main()
