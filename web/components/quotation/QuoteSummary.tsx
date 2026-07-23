"use client";

import type { QuotationTotals } from "@/lib/types";

function fmt(n: number) {
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function QuoteSummary({
  totals,
  currency,
  itemCount,
}: {
  totals: QuotationTotals;
  currency: string;
  itemCount: number;
}) {
  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 lg:sticky lg:top-4">
      <p className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Live Quote Summary</p>
      <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
        {itemCount} product{itemCount === 1 ? "" : "s"} selected
      </p>
      <dl className="space-y-2 text-sm">
        <div className="flex justify-between">
          <dt className="text-slate-600 dark:text-slate-400">Subtotal</dt>
          <dd className="text-slate-900 dark:text-slate-50">
            {currency} {fmt(totals.subtotal)}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-slate-600 dark:text-slate-400">Discount</dt>
          <dd className="text-slate-900 dark:text-slate-50">
            {currency} {fmt(totals.discount)}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-slate-600 dark:text-slate-400">VAT</dt>
          <dd className="text-slate-900 dark:text-slate-50">
            {currency} {fmt(totals.vat)}
          </dd>
        </div>
        <div className="flex justify-between border-t border-slate-200 dark:border-slate-800 pt-2 text-base font-semibold">
          <dt className="text-slate-900 dark:text-slate-50">Grand Total</dt>
          <dd className="text-slate-900 dark:text-slate-50">
            {currency} {fmt(totals.grand_total)}
          </dd>
        </div>
      </dl>
    </div>
  );
}
