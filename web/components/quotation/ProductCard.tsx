"use client";

import type { QuotationItem } from "@/lib/types";
import { computeItemTotal } from "@/lib/quotationTotals";

function fmt(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function ProductCard({
  item,
  onEdit,
  onDuplicate,
  onDelete,
}: {
  item: QuotationItem;
  onEdit: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
}) {
  const total = computeItemTotal(item);
  const discountLabel = item.discount_amount ? fmt(item.discount_amount) : item.discount_percent ? `${item.discount_percent}%` : "-";

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-3">
      <div className="flex min-w-0 items-center gap-3">
        {item.image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={item.image}
            alt={item.product_name}
            className="h-10 w-10 shrink-0 rounded-md border border-slate-200 dark:border-slate-700 object-cover"
          />
        ) : (
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-dashed border-slate-300 dark:border-slate-700 text-[10px] text-slate-400">
            No image
          </div>
        )}
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-slate-900 dark:text-slate-50">{item.product_name}</p>
          <p className="truncate text-xs text-slate-500 dark:text-slate-400">
            {[item.brand, item.model].filter(Boolean).join(" · ") || " "}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-4 text-sm text-slate-700 dark:text-slate-300">
        <span>Qty: {item.quantity}</span>
        <span>Price: {fmt(item.price)}</span>
        <span>Discount: {discountLabel}</span>
        <span className="font-semibold text-slate-900 dark:text-slate-50">Total: {fmt(total.line_total)}</span>
      </div>
      <div className="flex shrink-0 gap-2">
        <button
          type="button"
          onClick={onEdit}
          className="rounded-md border border-slate-300 dark:border-slate-700 px-3 py-1 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
        >
          Edit
        </button>
        <button
          type="button"
          onClick={onDuplicate}
          className="rounded-md border border-slate-300 dark:border-slate-700 px-3 py-1 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
        >
          Duplicate
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="rounded-md border border-slate-300 dark:border-slate-700 px-3 py-1 text-sm text-slate-700 dark:text-slate-200 hover:bg-red-50 hover:text-red-700 dark:hover:bg-red-950 dark:hover:text-red-300"
        >
          Delete
        </button>
      </div>
    </div>
  );
}
