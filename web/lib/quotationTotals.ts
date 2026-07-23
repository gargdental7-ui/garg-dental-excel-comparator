// Mirrors app/quotation.py's compute_item_total/compute_totals - used only
// for instant on-screen feedback. The server recomputes authoritatively
// from the same formula when generating the document.
import type { QuotationItem, QuotationTotals } from "./types";

export interface ItemTotal {
  line_subtotal: number;
  discount: number;
  line_total: number;
}

export function computeItemTotal(item: QuotationItem): ItemTotal {
  const line_subtotal = item.price * item.quantity;
  const discount = item.discount_amount ? item.discount_amount : (line_subtotal * item.discount_percent) / 100;
  return { line_subtotal, discount, line_total: line_subtotal - discount };
}

export function computeTotals(items: QuotationItem[], vatRate: number): QuotationTotals {
  let subtotal = 0;
  let discount = 0;
  for (const item of items) {
    const t = computeItemTotal(item);
    subtotal += t.line_subtotal;
    discount += t.discount;
  }
  const taxable = subtotal - discount;
  const vat = (taxable * vatRate) / 100;
  return { subtotal, discount, vat, grand_total: taxable + vat };
}
