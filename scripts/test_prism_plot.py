"""Data/automation checks; these do not assert Prism rendering succeeds."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
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

    def test_published_project_preserves_full_file_and_existing_output(self):
        original = self.root / "project.pzfx"
        headers, rows = ["Control", "Treatment"], [["1", "2"], ["3", None]]
        prism.prepare(self.template(), original, headers, rows, "column", None)
        destination = self.root / "simulated-t-test.pzfx"
        digest = prism.publish_project(original, destination)
        self.assertEqual(original.read_bytes(), destination.read_bytes())
        self.assertEqual(len(digest), 64)
        prism.verify_project(destination, headers, rows, "column", 1)
        self.assertEqual(prism.parse_template(destination)[0].getroot().findtext(prism.tag("Template")), "opaque-test-payload")
        original.write_bytes(b"different content")
        preserved = destination.read_bytes()
        with self.assertRaises(FileExistsError):
            prism.publish_project(original, destination)
        self.assertEqual(destination.read_bytes(), preserved)

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
