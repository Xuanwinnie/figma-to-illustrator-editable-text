"""以匿名合成資料驗證唯讀檢查與安全邊界。"""

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "inspect_export.py"
spec = importlib.util.spec_from_file_location("inspect_export", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class InspectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.svg = self.root / "sample.svg"

    def source(self, body):
        self.svg.write_text('<svg xmlns="http://www.w3.org/2000/svg">' + body + '</svg>')
        return self.svg

    def codes(self, report):
        return {f["code"]: f["count"] for f in report["findings"]}

    def test_font_metadata_filters_and_gradients(self):
        self.source('<defs><filter id="fx"/><linearGradient id="blue"/></defs>'
                    '<g id="FRAME__demo"><g id="f0_TID_1_2" filter="url(#fx)">'
                    '<text font-family="Arial" fill="url(#blue)"><tspan>A</tspan></text>'
                    '</g></g>')
        jsx = self.root / "meta.jsx"
        jsx.write_text('var BAKED_FIGMA_META = ' + json.dumps([
            {"k": "f0_TID_1_2", "ff": "Example Font", "fs": "Bold", "chars": "A"}]) + ';')
        report = module.inspect(self.svg, jsx)
        self.assertEqual(report["summary"]["frame_markers"], 1)
        self.assertEqual(report["summary"]["mapped_metadata_keys"], 1)
        self.assertEqual(self.codes(report)["text_filter_risk"], 1)
        self.assertEqual(self.codes(report)["text_gradient_risk"], 1)
        self.assertEqual(self.codes(report)["placeholder_font_suspected"], 1)

    def test_images_do_not_probe_outside_or_network(self):
        (self.root / "image.png").write_bytes(b"synthetic")
        self.source('<image href="image.png"/><image href="missing.png"/>'
                    '<image href="https://example.test/private.png"/>'
                    '<image href="../secret.png"/>'
                    '<image href="data:image/png;base64,YQ=="/>'
                    '<image href="data:image/png;base64,INVALID!"/>')
        states = module.inspect(self.svg)["summary"]["image_states"]
        self.assertEqual(states["linked_file_exists"], 1)
        self.assertEqual(states["linked_file_missing"], 1)
        self.assertEqual(states["external_not_checked"], 1)
        self.assertEqual(states["outside_export_not_checked"], 1)
        self.assertEqual(states["embedded_unverified_pixels"], 1)
        self.assertEqual(states["invalid_embedded"], 1)

    def test_blank_is_not_unmapped(self):
        self.source('<text>  </text><text>B</text>')
        jsx = self.root / "meta.jsx"
        jsx.write_text('var BAKED_FIGMA_META = [{"k":"unrelated"}];')
        report = module.inspect(self.svg, jsx)
        self.assertEqual(report["summary"]["blank_text_elements"], 1)
        self.assertEqual(self.codes(report)["unmapped_text_metadata"], 1)

    def test_inline_style_inheritance_and_css_disclosure(self):
        self.source('<style>.x {fill:none}</style><g style="font-family:Demo;filter:url(#fx)">'
                    '<text style="fill:none">C</text></g><filter id="fx"/>')
        report = module.inspect(self.svg)
        self.assertIn("Demo", report["svg_fonts"])
        self.assertIn("css_styles_not_resolved", self.codes(report))
        self.assertIn("explicitly_hidden_text", self.codes(report))

    def test_duplicate_ids_and_broken_references(self):
        self.source('<g id="same"/><g id="same"/><text fill="url(#absent)">D</text>')
        codes = self.codes(module.inspect(self.svg))
        self.assertEqual(codes["duplicate_svg_ids"], 1)
        self.assertEqual(codes["missing_url_targets"], 1)

    def test_metadata_is_never_executed(self):
        self.source('<text>E</text>')
        jsx = self.root / "meta.jsx"
        jsx.write_text('var BAKED_FIGMA_META = runDangerousCode();')
        self.assertIn("metadata_unreadable", self.codes(module.inspect(self.svg, jsx)))

    def test_reject_dtd(self):
        self.svg.write_text('<!DOCTYPE svg [<!ENTITY x "test">]><svg/>')
        with self.assertRaises(ValueError):
            module.inspect(self.svg)

    def test_reject_non_utf8_xml(self):
        self.svg.write_bytes('<!DOCTYPE svg [<!ENTITY x "test">]><svg/>'.encode("utf-16"))
        with self.assertRaises(ValueError):
            module.inspect(self.svg)

    def test_repeated_analysis_is_identical(self):
        self.source('<filter id="fx"/><g filter="url(#fx)"><text>H</text></g>')
        self.assertEqual(module.inspect(self.svg), module.inspect(self.svg))

    def test_metadata_failure_does_not_expose_paths(self):
        self.source('<text>I</text>')
        serialized = json.dumps(module.inspect(self.svg, self.root / "missing.jsx"))
        self.assertNotIn(str(self.root), serialized)

    def test_duplicate_metadata_is_not_used(self):
        self.source('<text id="f0_TID_1_2">J</text>')
        jsx = self.root / "meta.jsx"
        jsx.write_text('var BAKED_FIGMA_META = [{"k":"f0_TID_1_2"},'
                       '{"k":"f0_TID_1_2"}];')
        report = module.inspect(self.svg, jsx)
        self.assertEqual(report["summary"]["mapped_metadata_keys"], 0)
        self.assertEqual(self.codes(report)["duplicate_metadata_keys"], 1)

    def test_multiple_svg_requires_explicit_selection(self):
        self.source('<text>F</text>')
        (self.root / "other.svg").write_text('<svg/>')
        with redirect_stderr(io.StringIO()):
            self.assertEqual(module.main([str(self.root)]), 1)

    def test_no_overwrite_and_source_unchanged(self):
        self.source('<text>G</text>')
        before = hashlib.sha256(self.svg.read_bytes()).hexdigest()
        report = self.root / "report.json"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(module.main([str(self.svg), "--output", str(report)]), 0)
        saved = report.read_bytes()
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(module.main([str(self.svg), "--output", str(report)]), 1)
            self.assertEqual(module.main([str(self.svg), "--output", str(self.svg)]), 1)
        self.assertEqual(saved, report.read_bytes())
        self.assertEqual(before, hashlib.sha256(self.svg.read_bytes()).hexdigest())

    def test_report_omits_text_and_absolute_input_path(self):
        self.source('<text>Private client headline</text>')
        serialized = json.dumps(module.inspect(self.svg))
        self.assertNotIn("Private client headline", serialized)
        self.assertNotIn(str(self.root), serialized)


if __name__ == "__main__":
    unittest.main()
