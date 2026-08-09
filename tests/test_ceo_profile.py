import unittest

from ceo_profile import dominant_ceo_pillar, evaluate_ceo_fit


class CEOProfileTests(unittest.TestCase):
    def test_policy_bioeconomy_is_high_fit(self):
        text = (
            "Request for proposals for a consulting firm to design an agrifood bioeconomy "
            "strategy, strengthen institutions and prepare a regional roadmap for Latin America."
        )
        score, reasons, hits = evaluate_ceo_fit(text)
        self.assertGreaterEqual(score, 12)
        self.assertTrue(hits["Políticas y estrategia institucional"])
        self.assertTrue(hits["Bioeconomía, CTI e innovación"])

    def test_trade_and_investment_is_classified(self):
        text = (
            "Consulting services for agricultural trade, market intelligence, regulatory analysis, "
            "econometric modelling and investment structuring in Latin America."
        )
        self.assertEqual(dominant_ceo_pillar(text), "Mercados, comercio e inversiones")
        score, _, _ = evaluate_ceo_fit(text)
        self.assertGreaterEqual(score, 10)

    def test_generic_health_assignment_is_low_fit(self):
        text = "Individual consultant for hospital public health epidemiology and clinical services."
        score, reasons, _ = evaluate_ceo_fit(text)
        self.assertLess(score, 8)
        self.assertTrue(any("baja" in reason.lower() for reason in reasons))

    def test_project_management_is_relevant(self):
        text = (
            "Technical assistance for project formulation, monitoring and evaluation, capacity building "
            "and financing strategy for sustainable food systems in the Caribbean."
        )
        self.assertEqual(dominant_ceo_pillar(text), "Diseño y gestión de proyectos")
        score, _, _ = evaluate_ceo_fit(text)
        self.assertGreaterEqual(score, 11)


if __name__ == "__main__":
    unittest.main()
