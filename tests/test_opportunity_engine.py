import unittest
from datetime import date

from opportunity_engine import Opportunity, assess, canonical_url, identify_country, likely_duplicate


class OpportunityEngineTests(unittest.TestCase):
    def test_chilengedwe_is_not_chile(self):
        opp = Opportunity(
            title="Climate-smart agriculture in Ulimi ndi Chilengedwe Malawi",
            organization="UNDP Malawi", url="https://example.org/1", source="UNDP",
            country="Malawi", deadline="2030-01-01", notice_type="Request for proposal",
            summary="consulting services for agriculture",
        )
        self.assertEqual(identify_country(opp), "Malawi")
        self.assertEqual(assess(opp, today=date(2026, 8, 8)).decision, "reject")

    def test_alc_consultancy_is_accepted(self):
        opp = Opportunity(
            title="Consultoría para evaluación de políticas agrícolas",
            organization="UNDP – Guatemala", url="https://procurement-notices.undp.org/view_negotiation.cfm?nego_id=999",
            source="UNDP", country="Guatemala", country_code="GTM", deadline="2030-01-01",
            reference="UNDP-GTM-00999", notice_type="Individual consultant",
            summary="Términos de referencia para agricultura y desarrollo rural",
        )
        result = assess(opp, today=date(2026, 8, 8))
        self.assertEqual(result.decision, "accept")
        self.assertGreaterEqual(result.score, 75)

    def test_publication_is_rejected(self):
        opp = Opportunity(
            title="Annual report on food security", organization="FAO",
            url="https://fao.org/publications/report", source="FAO", country="Regional/Global",
            deadline="2030-01-01", notice_type="Report", summary="Annual report publication agriculture",
        )
        self.assertEqual(assess(opp, today=date(2026, 8, 8)).decision, "reject")

    def test_expired_is_rejected(self):
        opp = Opportunity(
            title="Request for proposal agriculture consultancy", organization="BID",
            url="https://iadb.org/opportunity/1", source="BID", country="Perú",
            deadline="2020-01-01", notice_type="RFP", summary="consulting services rural development",
        )
        self.assertEqual(assess(opp, today=date(2026, 8, 8)).decision, "reject")

    def test_exploratory_is_staged(self):
        opp = Opportunity(
            title="Consultancy food systems Latin America", organization="CAF",
            url="https://caf.com/consultoria/1", source="Tavily – Bancos", source_mode="exploratory",
            country="Regional/Global", deadline="2030-01-01", reference="RFP-1",
            notice_type="Request for proposal", summary="agriculture consulting services",
            source_score=0.9,
        )
        self.assertEqual(assess(opp, today=date(2026, 8, 8)).decision, "stage")

    def test_canonical_url_removes_tracking(self):
        a = canonical_url("https://www.example.org/a/?utm_source=x&id=7#top")
        b = canonical_url("https://example.org/a?id=7")
        self.assertEqual(a, b)

    def test_fuzzy_duplicate(self):
        opp = Opportunity(
            title="Consultoría para evaluación de política agrícola",
            organization="UNDP", url="", source="UNDP", country="Guatemala",
            deadline="2030-01-01", reference="",
        )
        rows = [{
            "Título": "Consultoria para la evaluacion de politica agricola",
            "Organización": "UNDP", "Fecha límite": "2030-01-01", "Enlace": "",
        }]
        self.assertTrue(likely_duplicate(opp, rows))


if __name__ == "__main__":
    unittest.main()
