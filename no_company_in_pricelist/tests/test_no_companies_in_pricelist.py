# -*- encoding: utf-8 -*-
# (c) 2021 Praxya - Aitor Rosell Torralba <arosell@praxya.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import SavepointCase

class TestProductPricelistNoCompany(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_id = cls.env.ref('base.main_company')
        cls.pricelist_model = cls.env['product.pricelist']

    def create_pricelist(self, company_status="No Force"):
        """Create a PriceList."""
        if company_status == "No Force":
            return self.pricelist_model.create({
                'name': 'Test Pricelist'
            })
        elif company_status == "Force Company":
            return self.pricelist_model.create({
                'name': 'Test Pricelist with Forced Company',
                'company_id': self.company_id.id
            })
        elif company_status == "Force No Company":
            return self.pricelist_model.create({
                'name': 'Test Pricelist with Forced No Company',
                'company_id': False
            })
        else:
            return self.pricelist_model.create({
                'name': 'Test Pricelist'
            })

    def test_normal_creation_results_in_no_company(self):
        pricelist = self.create_pricelist(company_status="No Force")
        self.assertEqual(pricelist.company_id.id,False,'Company ID is not False')

    def test_forces_company_results_in_no_company(self):
        pricelist = self.create_pricelist(company_status="Force Company")
        self.assertEqual(pricelist.company_id.id,False,'Company ID is not False')

    def test_forced_no_company_results_in_no_company(self):
        pricelist = self.create_pricelist(company_status="Force No Company")
        self.assertEqual(pricelist.company_id.id,False,'Company ID is not False')

    def test_write_company_results_in_no_company(self):
        pricelist = self.create_pricelist(company_status="Force Company")
        pricelist.company_id = self.company_id.id
        pricelist.write({
            'company_id': self.company_id.id
        })
        self.assertEqual(pricelist.company_id.id,False,'Company ID is not False')

    def test_random_write_results_in_no_company(self):
        pricelist = self.create_pricelist(company_status="Force Company")
        pricelist.company_id = self.company_id.id
        pricelist.write({
            'name': "Modified Pricelist"
        })
        self.assertEqual(pricelist.company_id.id,False,'Company ID is not False')

    def test_no_company_write_results_in_no_company(self):
        pricelist = self.create_pricelist(company_status="Force Company")
        pricelist.company_id = self.company_id.id
        pricelist.write({
            'company_id': False
        })
        self.assertEqual(pricelist.company_id.id,False,'Company ID is not False')