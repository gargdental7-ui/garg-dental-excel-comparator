import type { QuotationCustomer, QuotationImportedProduct, QuotationItem, QuotationProposal } from "./types";

export function emptyQuotationCustomer(): QuotationCustomer {
  return {
    customer_name: "",
    contact_person: "",
    designation: "",
    company_name: "",
    address: "",
    phone: "",
    email: "",
    reference_number: "",
    notes: "",
  };
}

export function defaultQuotationProposal(): QuotationProposal {
  return {
    title: "",
    subject: "",
    quotation_date: new Date().toISOString().slice(0, 10),
    validity: "30 days from the date of this quotation",
    prepared_by: "",
    currency: "NRs",
  };
}

function newItemId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `item-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function blankQuotationItem(): QuotationItem {
  return {
    id: newItemId(),
    product_name: "",
    price: 0,
    quantity: 1,
    code: "",
    description: "",
    brand: "",
    model: "",
    origin: "",
    category: "",
    warranty: "",
    discount_percent: 0,
    discount_amount: 0,
    image: null,
    features: [],
    specifications: [],
    installation_notes: "",
    additional_notes: "",
    accessories: [],
    brochure_note: "",
  };
}

export function quotationItemFromImportedProduct(product: QuotationImportedProduct): QuotationItem {
  return {
    ...blankQuotationItem(),
    product_name: product.product_name,
    price: product.price,
    code: product.code,
    description: product.description,
    brand: product.brand,
    model: product.model,
    origin: product.origin,
    category: product.category,
    warranty: product.warranty,
  };
}
