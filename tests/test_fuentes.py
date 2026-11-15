import unittest
from datetime import date

import buscar_consultorias as b
from opportunity_engine import parse_date

UNDP_SAMPLE = """
<a href="view_negotiation.cfm?nego_id=1" class="vacanciesTableLink" data-region="region_RLA">
 <div class="vacanciesTable__cell"><div class="vacanciesTable__cell__label">Title</div><span>Consultoría para estrategia agroalimentaria</span></div>
 <div class="vacanciesTable__cell"><div class="vacanciesTable__cell__label">Ref No</div><span>UNDP-ARG-00123</span></div>
 <div class="vacanciesTable__cell"><div class="vacanciesTable__cell__label">UNDP Office/Country</div><span>UNDP-ARG/ARGENTINA</span></div>
 <div class="vacanciesTable__cell"><div class="vacanciesTable__cell__label">Process</div><span>RFP - Request for proposal</span></div>
 <div class="vacanciesTable__cell"><div class="vacanciesTable__cell__label">Deadline</div><span><nobr>29-Nov-26<br>06:30 AM (New York time)</nobr></span></div>
</a>
<a href="view_negotiation.cfm?nego_id=2" class="vacanciesTableLink" data-region="region_RLA">
 <div class="vacanciesTable__cell"><div class="vacanciesTable__cell__label">Title</div><span>Suministro de mobiliario</span></div>
 <div class="vacanciesTable__cell"><div class="vacanciesTable__cell__label">Process</div><span>RFQ - Request for quotation</span></div>
</a>
<a href="view_negotiation.cfm?nego_id=3" class="vacanciesTableLink" data-region="region_RAS">
 <div class="vacanciesTable__cell"><div class="vacanciesTable__cell__label">Title</div><span>Consultancy in Asia</span></div>
 <div class="vacanciesTable__cell"><div class="vacanciesTable__cell__label">Process</div><span>IC - Individual contractor</span></div>
</a>
"""


class FuentesTests(unittest.TestCase):
    def test_undp_short_year_deadline(self):
        self.assertEqual(parse_date("29-Nov-26 06:30 AM (New York time)"), date(2026, 11, 29))

    def test_undp_keeps_only_alc_consulting(self):
        rows = b.parse_undp_html(UNDP_SAMPLE)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].notice_type, "RFP - Request for proposal")
        self.assertEqual(parse_date(rows[0].deadline), date(2026, 11, 29))

    def test_world_bank_skips_contract_awards(self):
        award = {"id": "OP1", "bid_description": "X", "notice_type": "Contract Award", "project_ctry_name": "Argentina"}
        self.assertIsNone(b.parse_world_bank_notice(award))

    def test_world_bank_reoi_is_parsed(self):
        item = {"id": "OP2", "bid_description": "Estudio de cadenas agroindustriales",
                "notice_type": "Request for Expression of Interest", "project_ctry_name": "Argentina",
                "submission_deadline_date": "2026-12-01T00:00:00Z", "project_id": "P123"}
        opp = b.parse_world_bank_notice(item)
        self.assertEqual(opp.deadline, "2026-12-01")
        self.assertIn("procurement-detail/OP2", opp.url)

    def test_reliefweb_without_appname_is_skipped(self):
        import os
        os.environ.pop("RELIEFWEB_APPNAME", None)
        self.assertEqual(b.scrape_reliefweb(None), [])


if __name__ == "__main__":
    unittest.main()
