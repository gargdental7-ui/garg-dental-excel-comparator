"""Company profile registry for the Smart Quotation Generator.

Each company is one entry here plus one authored template .docx in
app/quotation_templates/ - adding a second company later means adding one
CompanyProfile and one template file, never touching the rendering engine,
validation, or totals math in quotation.py / quotation_docx.py.
"""
from dataclasses import dataclass, field
from pathlib import Path

from .exceptions import UnknownCompanyError

TEMPLATES_DIR = Path(__file__).parent / "quotation_templates"


@dataclass
class CompanyProfile:
    id: str
    display_name: str
    template_filename: str
    terms_and_conditions: list = field(default_factory=list)  # [(label, text), ...]
    default_currency: str = "NRs"
    default_vat_rate: float = 0.0
    default_validity: str = "30 days from the date of this quotation"

    @property
    def template_path(self) -> Path:
        return TEMPLATES_DIR / self.template_filename


COMPANIES = {
    "garg_dental": CompanyProfile(
        id="garg_dental",
        display_name="Garg Dental Pvt. Ltd",
        template_filename="equipment_proposal_garg_dental.docx",
        default_currency="NRs",
        default_vat_rate=0.0,
        terms_and_conditions=[
            ("Prices", "Prices are in NRs on door delivery basis."),
            ("Taxes", "VAT is Inclusive as applicable."),
            ("Payment", "50% advance & balance remaining against delivery."),
            ("Delivery", "After 6-8 weeks after your confirmed order subject to meet the payment terms."),
            (
                "Shipment From",
                "Our warehouse in Kathmandu or from the location/company if it's a direct shipment.",
            ),
            (
                "Purchase Order",
                "Must be in the name of Garg Dental Pvt. Ltd or in the name of the principal co.",
            ),
            (
                "Installation",
                "Installation of the equipment will be done by our engineers based in Kathmandu at no extra cost.",
            ),
            (
                "Warranty",
                "The equipment are warranted against manufacturing defects for a period of 24 months from "
                "the date of installation. All warranty replacement is subject to conditions.",
            ),
            (
                "Scope of Warranty",
                "Consumables, semi consumable, bulbs, probes, cables etc. are not covered under warranty. "
                "Reusable accessories are covered under limited warranty (Condition apply).",
            ),
        ],
    )
}


def get_company(company_id: str) -> CompanyProfile:
    company = COMPANIES.get(company_id)
    if company is None:
        raise UnknownCompanyError(company_id)
    return company


def list_companies():
    return list(COMPANIES.values())
