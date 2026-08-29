import csv
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AppResetAndThemeTests(unittest.TestCase):
    def test_operational_csv_files_keep_schema_and_start_empty(self):
        expected_columns = {
            "oportunidades_consultoria.csv": {"Título", "Organización", "Estado", "Enlace"},
            "candidatos_revision.csv": {"ID canónico", "Título", "Estado revisión", "Puntaje"},
        }
        for filename, required in expected_columns.items():
            with self.subTest(filename=filename):
                with (ROOT / filename).open(encoding="utf-8", newline="") as handle:
                    rows = list(csv.reader(handle))
                self.assertEqual(len(rows), 1)
                self.assertTrue(required.issubset(set(rows[0])))

    def test_manual_palette_and_fonts_are_present(self):
        source = (ROOT / "ceo_theme.py").read_text(encoding="utf-8")
        for token in ("#0D3B2E", "#6DB16A", "#F4FAF6", "#1A1A1A", "#555555", "#DDDDDD"):
            self.assertIn(token, source)
        self.assertIn("Montserrat", source)
        self.assertIn("Source Sans 3", source)

    def test_navigation_is_reduced_to_four_operational_destinations(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        match = re.search(r"options=\[\s*(.*?)\s*\],\s*label_visibility", source, re.S)
        self.assertIsNotNone(match)
        options = re.findall(r'"([^"]+)"', match.group(1))
        self.assertEqual(len(options), 4)
        self.assertNotIn("📋  Oportunidades", options)


if __name__ == "__main__":
    unittest.main()
