// Mirrors app/quotation.py's find_duplicate_products - instant client-side
// feedback only; the server re-validates authoritatively at generate time.
import type { QuotationItem } from "./types";

export function findDuplicateProducts(items: QuotationItem[]): string[] {
  const seen = new Map<string, string>();
  const duplicates: string[] = [];
  for (const item of items) {
    const key = `${item.product_name.trim().toLowerCase()}|${item.code.trim().toLowerCase()}`;
    if (!item.product_name.trim()) continue;
    if (seen.has(key)) {
      const original = seen.get(key)!;
      if (!duplicates.includes(original)) duplicates.push(original);
    } else {
      seen.set(key, item.product_name);
    }
  }
  return duplicates;
}
