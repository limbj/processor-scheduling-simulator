"""Resource loading must work without changing a caller's working directory."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HAS_QT = importlib.util.find_spec("PyQt5") is not None
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(HAS_QT, "Install requirements.txt to run the GUI resource tests.")
class ResourcePathTests(unittest.TestCase):
    def run_probe(self, script, directory):
        environment = os.environ.copy()
        environment["QT_QPA_PLATFORM"] = "offscreen"
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"
        completed = subprocess.run(
            [sys.executable, "-B", "-c", script, str(PROJECT_ROOT)],
            cwd=directory,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        self.assertEqual(
            completed.returncode,
            0,
            "External-directory probe failed:\n%s\n%s"
            % (completed.stdout, completed.stderr),
        )
        reports = [
            line[len("RESOURCE_PROBE:"):]
            for line in completed.stdout.splitlines()
            if line.startswith("RESOURCE_PROBE:")
        ]
        self.assertEqual(len(reports), 1, completed.stdout)
        return json.loads(reports[0])

    def test_import_from_an_external_directory_preserves_cwd(self):
        script = """
import json
from pathlib import Path
import sys
project = Path(sys.argv[1]).resolve()
before = Path.cwd()
sys.path.insert(0, str(project))
import ui
report = {
    "before": str(before),
    "after_import": str(Path.cwd()),
    "assets": str(ui.ASSETS_DIR.resolve()),
    "form_loaded": hasattr(ui.form_class, "setupUi"),
}
print("RESOURCE_PROBE:" + json.dumps(report))
"""
        with tempfile.TemporaryDirectory(prefix="scheduler resources ") as directory:
            report = self.run_probe(script, directory)
            self.assertEqual(Path(report["before"]), Path(directory).resolve())
            self.assertEqual(Path(report["after_import"]), Path(directory).resolve())
            self.assertEqual(Path(report["assets"]), PROJECT_ROOT / "assets")
            self.assertTrue(report["form_loaded"])

    def test_window_loads_styles_and_icon_from_assets_without_changing_cwd(self):
        script = """
import json
from pathlib import Path
import sys
project = Path(sys.argv[1]).resolve()
before = Path.cwd()
sys.path.insert(0, str(project))
import ui
after_import = Path.cwd()
from PyQt5.QtWidgets import QApplication
app = QApplication([])
window = ui.OS_Scheduler()
pixmap = window.windowIcon().pixmap(32, 32)
expected_stylesheet = (project / "assets" / "styles.qss").read_text(encoding="utf-8")
report = {
    "before": str(before),
    "after_import": str(after_import),
    "after_window": str(Path.cwd()),
    "platform": app.platformName(),
    "stylesheet_matches": window.styleSheet() == expected_stylesheet,
    "stylesheet_nonempty": bool(window.styleSheet().strip()),
    "icon_loaded": not pixmap.isNull(),
    "icon_size": [pixmap.width(), pixmap.height()],
    "controls_loaded": all(hasattr(window, name) for name in (
        "cb_algorithm", "tw_process", "tw_gantt", "tw_result",
    )),
}
window.close()
print("RESOURCE_PROBE:" + json.dumps(report))
"""
        with tempfile.TemporaryDirectory(prefix="scheduler resources ") as directory:
            report = self.run_probe(script, directory)
            for stage in ("before", "after_import", "after_window"):
                with self.subTest(stage=stage):
                    self.assertEqual(Path(report[stage]), Path(directory).resolve())
            self.assertEqual(report["platform"], "offscreen")
            self.assertTrue(report["stylesheet_matches"])
            self.assertTrue(report["stylesheet_nonempty"])
            self.assertTrue(report["icon_loaded"])
            self.assertGreater(report["icon_size"][0], 0)
            self.assertGreater(report["icon_size"][1], 0)
            self.assertTrue(report["controls_loaded"])


if __name__ == "__main__":
    unittest.main()
