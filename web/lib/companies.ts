// Frontend-only registry of companies the Smart Quotation Generator can
// serve. Mirrors app/quotation_companies.py's COMPANIES dict in spirit, but
// stays separate: only "garg_dental" has a working backend company profile
// (template, terms, VAT rate) today, so the others are listed purely as
// "Coming Soon" cards on the company-selection page - no API call needed
// to render them.
export interface CompanySummary {
  id: string;
  displayName: string;
  tagline: string;
  active: boolean;
}

export const COMPANIES: CompanySummary[] = [
  {
    id: "garg_dental",
    displayName: "Garg Dental Pvt. Ltd.",
    tagline: "Dental equipment proposals, fully wired to the branded quotation template.",
    active: true,
  },
  {
    id: "company_a",
    displayName: "Company A",
    tagline: "Coming soon.",
    active: false,
  },
  {
    id: "company_b",
    displayName: "Company B",
    tagline: "Coming soon.",
    active: false,
  },
  {
    id: "company_c",
    displayName: "Company C",
    tagline: "Coming soon.",
    active: false,
  },
  {
    id: "company_d",
    displayName: "Company D",
    tagline: "Coming soon.",
    active: false,
  },
];
