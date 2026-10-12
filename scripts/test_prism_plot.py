"""Data/automation checks; these do not assert Prism rendering succeeds."""
import importlib.util
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import re
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

SPEC = importlib.util.spec_from_file_location("prism_plot", Path(__file__).with_name("prism_plot.py"))
prism = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prism)


class PrismDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def analysis_arguments(self, **overrides):
        values = dict(analysis="welch-t", error_bars=None, layout=None, template=None,
                      preset=None, table_index=None, graph_index=None, results_index=None,
                      title=None, x_title=None)
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_analysis_selection_defaults_sem_and_routes_sd(self):
        headers, rows = ["A", "B"], [["1", "2"], ["3", "4"]]
        for error_bars, filename in ((None, "welch-mean-sem.pzfx"), ("sd", "welch-mean-sd.pzfx")):
            args = self.analysis_arguments(error_bars=error_bars)
            profile = prism.select_analysis(args, headers, rows)
            self.assertEqual(Path(args.template).name, filename)
            self.assertEqual((args.table_index, args.graph_index, args.results_index), (1, 1, 1))
            self.assertEqual(args.layout, "column")
            self.assertEqual(args.title, "A vs B")
            self.assertEqual(args.x_title, "")
            self.assertEqual(profile["experimental_design"], "WELCH_T_TEST")

    def test_analysis_rejects_unsupported_methods_and_conflicting_settings(self):
        headers, rows = ["A", "B"], [["1", "2"], ["3", "4"]]
        for settings in ({"analysis": "unsupported-test"}, {"error_bars": "ci95"}):
            with self.subTest(settings=settings), self.assertRaisesRegex(ValueError, "尚无已验证"):
                prism.select_analysis(self.analysis_arguments(**settings), headers, rows)
        for settings in ({"template": "user.prism"}, {"graph_index": 1}, {"preset": "column-scatter"}):
            with self.subTest(settings=settings), self.assertRaisesRegex(ValueError, "不能同时指定"):
                prism.select_analysis(self.analysis_arguments(**settings), headers, rows)
        with self.assertRaisesRegex(ValueError, "需同时指定"):
            prism.select_analysis(self.analysis_arguments(analysis=None, error_bars="sd"), headers, rows)

    def test_analysis_checks_groups_and_observation_counts(self):
        with self.assertRaisesRegex(ValueError, "要求 2 组"):
            prism.select_analysis(self.analysis_arguments(), ["A", "B", "C"], [["1", "2", "3"]])
        with self.assertRaisesRegex(ValueError, "至少需要 2"):
            prism.select_analysis(self.analysis_arguments(), ["A", "B"], [["1", "2"], [None, "3"]])
        with self.assertRaisesRegex(ValueError, "要求 --layout column"):
            prism.select_analysis(self.analysis_arguments(layout="xy"), ["A", "B"], [["1", "2"], ["3", "4"]])

    def test_catalog_detects_template_drift(self):
        assets = self.root / "assets"
        assets.mkdir()
        (assets / "template.prism").write_bytes(b"changed-template")
        (assets / "analysis-profiles.json").write_text(json.dumps({"version": 1, "profiles": [
            {"analysis": "welch-t", "error_bars": "sem", "template": "template.prism", "sha256": "wrong"}
        ]}), encoding="utf-8")
        with patch.object(prism, "ASSETS", assets), self.assertRaisesRegex(ValueError, "已改变"):
            prism.analysis_profiles()

    def test_paired_methods_reject_asymmetric_missing_observations(self):
        for analysis in ("paired-t", "wilcoxon"):
            with self.subTest(analysis=analysis), self.assertRaisesRegex(ValueError, "单边缺测"):
                prism.select_analysis(self.analysis_arguments(analysis=analysis), ["Before", "After"],
                                      [["1", "2"], ["3", "4"], [None, "5"]])
            args = self.analysis_arguments(analysis=analysis)
            profile = prism.select_analysis(args, ["Before", "After"], [["1", "2"], ["3", "4"]])
            self.assertEqual(profile["pairing"], "paired")

    def test_anova_and_graph_catalog_bind_correct_data_shapes(self):
        args = self.analysis_arguments(analysis="anova-tukey")
        profile = prism.select_analysis(args, ["A", "B", "C"], [["1", "2", "3"], ["2", "3", "4"]])
        self.assertEqual(profile["post_test"], "TUKEY")
        with self.assertRaisesRegex(ValueError, "要求 3 组"):
            prism.select_analysis(self.analysis_arguments(analysis="anova-tukey"), ["A", "B"], [["1", "2"], ["3", "4"]])
        graph = self.analysis_arguments(analysis=None, graph="paired-lines")
        with self.assertRaisesRegex(ValueError, "完整配对"):
            prism.select_graph(graph, ["A", "B"], [["1", "2"], ["3", None]])
        graph = self.analysis_arguments(analysis=None, graph="xy-line")
        profile = prism.select_graph(graph, ["Time", "Y"], [["0", "3"], ["1", "4"]])
        self.assertEqual(graph.layout, "xy")
        self.assertEqual(profile["error_bars"], None)

    def template(self, layout="column", count=3):
        root = ET.Element(prism.tag("GraphPadPrismFile"), PrismXMLVersion="5.00")
        seq = ET.SubElement(root, prism.tag("TableSequence"))
        ET.SubElement(seq, prism.tag("Ref"), ID="Table1")
        table = ET.SubElement(root, prism.tag("Table"), ID="Table1",
                              TableType="OneWay" if layout == "column" else "XY",
                              XFormat="none" if layout == "column" else "numbers", YFormat="replicates")
        ET.SubElement(table, prism.tag("Title")).text = "Demo"
        if layout == "xy":
            x = ET.SubElement(table, prism.tag("XColumn"))
            ET.SubElement(x, prism.tag("Title")).text = "Old X"
            ET.SubElement(x, prism.tag("Subcolumn"))
        for index in range(count):
            col = ET.SubElement(table, prism.tag("YColumn"), Subcolumns="1", Width="70")
            ET.SubElement(col, prism.tag("Title")).text = f"Old {index}"
            sub = ET.SubElement(col, prism.tag("Subcolumn"))
            ET.SubElement(sub, prism.tag("d")).text = "999"
        ET.SubElement(root, prism.tag("Template")).text = "opaque-test-payload"
        path = self.root / "template.pzfx"
        ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
        return path

    def test_column_missing_values_labels_and_opaque_preserved(self):
        template = self.template()
        dest = self.root / "result.pzfx"
        headers = ["对照 & 未处理", "Treatment"]
        rows = [["1.25", "2"], [None, "3"], ["4", None]]
        prism.prepare(template, dest, headers, rows, "column", None)
        prism.verify_project(dest, headers, rows, "column", 1)
        tree, tables = prism.parse_template(dest)
        self.assertEqual(tree.getroot().findtext(prism.tag("Template")), "opaque-test-payload")
        self.assertEqual(len(tables[0].findall(prism.tag("YColumn"))[-1].find(prism.tag("Subcolumn"))), 0)
        self.assertEqual(prism.inspect_template(template)[0]["title"], "Demo")

    def test_xy_data_and_numeric_x(self):
        dest = self.root / "result.pzfx"
        headers, rows = ["Time", "Signal"], [["0", "1"], ["2.5", None], ["4", "3.8"]]
        prism.prepare(self.template("xy"), dest, headers, rows, "xy", None)
        prism.verify_project(dest, headers, rows, "xy", 1)
        with self.assertRaisesRegex(ValueError, "X 列不能空"):
            prism.prepare(self.template("xy"), dest, headers, [[None, "1"]], "xy", None)

    def test_xy_advanced_column_cannot_restore_old_demo_x(self):
        template = self.template("xy", count=1)
        tree, tables = prism.parse_template(template)
        advanced = ET.SubElement(tables[0], prism.tag("XAdvancedColumn"), Version="1", Subcolumns="1")
        ET.SubElement(advanced, prism.tag("Title"))
        sub = ET.SubElement(advanced, prism.tag("Subcolumn"))
        ET.SubElement(sub, prism.tag("d")).text = "999"
        tree.write(template, encoding="utf-8")
        dest = self.root / "result.pzfx"
        prism.prepare(template, dest, ["Time", "Signal"], [["0", "1"], ["5", "2"]], "xy", 1)
        _, tables = prism.parse_template(dest)
        column = tables[0].find(prism.tag("XAdvancedColumn"))
        self.assertEqual(column.findtext(prism.tag("Title")), "Time")
        self.assertEqual([cell.text for cell in column.find(prism.tag("Subcolumn"))], ["0", "5"])

    def test_no_silent_dataset_loss_or_layout_coercion(self):
        template = self.template(count=1)
        with self.assertRaisesRegex(ValueError, "模板容量"):
            prism.prepare(template, self.root / "out.pzfx", ["A", "B"], [["1", "2"]], "column", None)
        with self.assertRaisesRegex(ValueError, "需要 XY"):
            prism.prepare(template, self.root / "out.pzfx", ["X", "Y"], [["1", "2"]], "xy", None)

    def test_input_validation_and_integer_precision(self):
        path = self.root / "data.csv"
        path.write_text("A,B\n9007199254740993,2\n,3\n", encoding="utf-8")
        headers, rows = prism.load_data(path, None)
        self.assertEqual(rows[0][0], "9007199254740993")
        self.assertIsNone(rows[1][0])
        path.write_text("A,A\n1,2\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "表头"):
            prism.load_data(path, None)
        path.write_text("A,B\n1,NaN\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "NaN/Inf"):
            prism.load_data(path, None)

    def test_output_numeric_mismatch_detected(self):
        dest = self.root / "result.pzfx"
        prism.prepare(self.template(), dest, ["A"], [["1"]], "column", None)
        with self.assertRaisesRegex(RuntimeError, "数据与输入不符"):
            prism.verify_project(dest, ["A"], [["2"]], "column", 1)
        prism.prepare(self.template(), dest, ["A"], [["9007199254740993"]], "column", None)
        with self.assertRaisesRegex(RuntimeError, "数据与输入不符"):
            prism.verify_project(dest, ["A"], [["9007199254740992"]], "column", 1)

    def test_prepare_only_cli_records_no_render_success(self):
        source = self.root / "data.csv"
        source.write_text("A,B\n1,2\n3,\n", encoding="utf-8")
        result = subprocess.run([
            sys.executable, "-X", "utf8", str(Path(prism.__file__)), "plot",
            "--input", str(source), "--layout", "column", "--template", str(self.template()),
            "--output", str(self.root / "output"), "--prepare-only", "--title", "响应 50%",
            "--results-index", "3",
            "--color-scheme", "Floral", "--y-interval", "20",
        ], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(result.stdout)
        self.assertEqual(manifest["status"], "prepared_only")
        self.assertNotIn("deliverable_project", manifest)
        self.assertTrue(Path(manifest["prepared_project"]).is_file())
        self.assertFalse(any(Path(path).exists() for path in manifest["exports"]))
        self.assertEqual(manifest["results_index"], 3)
        self.assertFalse(Path(manifest["results_export"]).exists())
        commands = Path(manifest["script"]).read_text(encoding="utf-8").splitlines()
        self.assertEqual(commands[2:4], ["RecalcAll", "GoTo R 3"])
        self.assertTrue(commands[4].startswith('ExportTable "'))
        self.assertEqual(commands[5], "GoTo G 1")
        self.assertEqual(commands[6], 'ApplyColorScheme "Floral"')
        self.assertIn("SetAxisLimits Y Interval 20", commands)
        self.assertEqual(manifest["project_format"], "prism")
        self.assertEqual(Path(manifest["project"]).suffix, ".prism")
        self.assertIn('Save "' + manifest["project"] + '"', commands)
        self.assertIn('Save "' + manifest["verification_project"] + '"', commands)
        self.assertIn('"响应 50%%"', Path(manifest["script"]).read_text(encoding="utf-8-sig"))
        self.assertTrue(Path(manifest["script"]).read_bytes().startswith(b"CreateLog\r\n"))
        run = Path(manifest["run_directory"])
        work = run / "_work"
        self.assertEqual(Path(manifest["work_directory"]), work)
        self.assertEqual(Path(manifest["prepared_project"]).parent, work)
        self.assertEqual(Path(manifest["verification_project"]).parent, work)
        self.assertEqual(Path(manifest["script"]).parent, work)
        self.assertEqual(Path(manifest["project"]), run / "data.prism")
        self.assertTrue(all(Path(path).parent == run for path in manifest["exports"]))
        self.assertEqual(list(run.parent.iterdir()), [run])

    def simulated_execution(self, executable, script, marker, timeout):
        """Exercise artifact routing without claiming a real Prism render."""
        prepared = None
        for line in script.read_text(encoding="utf-8").splitlines():
            match = re.match(r'^(Open|Save|ExportPDF|ExportPNG|ExportTable) "([^"]+)"', line)
            if not match:
                continue
            command, filename = match.groups()
            path = Path(filename)
            if command == "Open":
                prepared = path
            elif command == "Save" and path.suffix == ".pzfx":
                path.write_bytes(prepared.read_bytes())
            elif command == "Save":
                with zipfile.ZipFile(path, "w") as archive:
                    archive.writestr("document.json", json.dumps({"sheets": {
                        "data": ["data-uid"], "graphs": ["graph-uid"], "analyses": []}}))
                    archive.writestr("data/sheets/data-uid/sheet.json", "{}")
                    archive.writestr("graphs/graph-uid/sheet.json", "{}")
                    archive.writestr("graphs/graph-uid/data.bin", b"test-native-payload")
            elif command == "ExportPDF":
                path.write_bytes(b"%PDF-1.7\n")
            elif command == "ExportPNG":
                path.write_bytes(b"\x89PNG\r\n\x1a\n")
            elif command == "ExportTable":
                path.write_text("Test result\t1\n", encoding="utf-8")
        marker.write_text("done", encoding="utf-8")
        return {"pid": 0, "seconds": 0}

    def test_success_keeps_one_project_and_preserves_prior_run(self):
        source = self.root / "data.csv"
        source.write_text("A,B\n1,2\n3,4\n", encoding="utf-8")
        template = self.template()
        output = self.root / "output"
        for fmt in ("prism", "pzfx"):
            with self.subTest(project_format=fmt):
                args = ["prism_plot.py", "plot", "--input", str(source), "--layout", "column",
                        "--template", str(template), "--output", str(output),
                        "--project-format", fmt, "--results-index", "1"]
                previous = {path: path.read_bytes() for path in output.rglob("*") if path.is_file()} if output.exists() else {}
                captured = io.StringIO()
                with patch.object(sys, "argv", args), patch.object(prism, "find_prism", return_value=self.root / "prism.exe"), \
                        patch.object(prism, "execute", side_effect=self.simulated_execution), redirect_stdout(captured):
                    self.assertEqual(prism.main(), 0)
                manifest = json.loads(captured.getvalue())
                run = Path(manifest["run_directory"])
                project = run / f"data.{fmt}"
                self.assertEqual(Path(manifest["project"]), project)
                self.assertEqual(Path(manifest["deliverable_project"]), project)
                self.assertEqual(list(run.rglob(f"*.{fmt}")), [project] if fmt == "prism" else
                                 [project, run / "_work" / "prepared.pzfx"])
                self.assertEqual({path.name for path in run.iterdir()},
                                 {f"data.{fmt}", "data.pdf", "data.png", "statistics.txt", "manifest.json", "_work"})
                self.assertTrue(all(path.is_dir() for path in output.iterdir()))
                self.assertEqual(len(manifest["deliverable_project_sha256"]), 64)
                for path, content in previous.items():
                    self.assertEqual(path.read_bytes(), content)

    def test_failed_execution_preserves_diagnostics_without_success_project(self):
        source = self.root / "data.csv"
        source.write_text("A\n1\n", encoding="utf-8")
        args = ["prism_plot.py", "plot", "--input", str(source), "--layout", "column",
                "--template", str(self.template()), "--output", str(self.root / "output")]
        with patch.object(sys, "argv", args), patch.object(prism, "find_prism", return_value=self.root / "prism.exe"), \
                patch.object(prism, "execute", side_effect=RuntimeError("test execution failed")), \
                redirect_stdout(io.StringIO()), patch.object(sys, "stderr", io.StringIO()):
            self.assertEqual(prism.main(), 1)
        run = next((self.root / "output").iterdir())
        manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "failed")
        self.assertNotIn("deliverable_project", manifest)
        self.assertTrue((run / "_work" / "plot.pzc").is_file())
        self.assertTrue((run / "_work" / "prepared.pzfx").is_file())
        self.assertFalse(any(run.rglob("*.prism")))

    def test_script_literal_safety_and_format_signature(self):
        self.assertEqual(prism.quoted("响应 %"), '"响应 %%"')
        with self.assertRaises(ValueError):
            prism.quoted('title"\nClose')
        path = self.root / "fake.png"
        path.write_bytes(b"not-a-png")
        with self.assertRaisesRegex(RuntimeError, "格式签名"):
            prism.validate_export(path, "png")

    def test_modern_project_rejects_renamed_xml_and_missing_native_graph(self):
        path = self.root / "project.prism"
        path.write_bytes(b"<?xml version='1.0'?><GraphPadPrismFile/>")
        with self.assertRaisesRegex(RuntimeError, "不是有效"):
            prism.validate_prism_project(path)
        document = {"sheets": {"data": ["data-uid"], "graphs": ["graph-uid"], "analyses": ["analysis-uid"]}}
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("document.json", json.dumps(document))
            archive.writestr("data/sheets/data-uid/sheet.json", "{}")
            archive.writestr("graphs/graph-uid/sheet.json", "{}")
            archive.writestr("analyses/analysis-uid/parameters.json", "{}")
            archive.writestr("analyses/analysis-uid/results.json", '{"p": 0.01}')
        with self.assertRaisesRegex(RuntimeError, "缺少完整"):
            prism.validate_prism_project(path)
        with zipfile.ZipFile(path, "a") as archive:
            archive.writestr("graphs/graph-uid/data.bin", b"preserved-native-graph-payload")
        prism.validate_prism_project(path)

    def test_xlsx_sheet_selection_and_uncached_formula(self):
        try:
            from openpyxl import Workbook
        except ImportError:
            self.skipTest("openpyxl not installed")
        book = Workbook()
        sheet = book.active
        sheet.title = "Data"
        sheet.append(["Control", "Treatment"])
        sheet.append([1, 2])
        book.create_sheet("Empty")
        path = self.root / "data.xlsx"
        book.save(path)
        self.assertEqual(prism.load_data(path, None)[1], [["1", "2"]])
        sheet["A2"] = "=1+1"
        book.save(path)
        with self.assertRaisesRegex(ValueError, "没有缓存结果"):
            prism.load_data(path, "Data")


if __name__ == "__main__":
    unittest.main()
