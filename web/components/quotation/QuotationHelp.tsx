"use client";

import { useState } from "react";

export function QuotationHelp() {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between text-left text-sm font-semibold text-slate-700 dark:text-slate-200"
      >
        <span>Help: How the Smart Quotation Generator works</span>
        <span className="text-slate-400">{open ? "Hide" : "Show"}</span>
      </button>
      {open && (
        <div className="mt-3 space-y-3 text-sm text-slate-600 dark:text-slate-400">
          <div>
            <p className="font-medium text-slate-700 dark:text-slate-300">What this tool does</p>
            <p>
              Builds a professional Garg Dental equipment proposal (Word document) from customer details and a list
              of products, then dramatically cuts manual typing by auto-filling product information from an uploaded
              Excel sheet.
            </p>
          </div>
          <div>
            <p className="font-medium text-slate-700 dark:text-slate-300">When to use Excel Assisted mode</p>
            <p>
              Use this when you have a price list or product catalog in Excel. Upload it, map its columns once, then
              search and select products - name, brand, model, origin, price, etc. fill in automatically.
            </p>
          </div>
          <div>
            <p className="font-medium text-slate-700 dark:text-slate-300">When to use Manual mode</p>
            <p>
              Use this for one-off products that aren&apos;t in any Excel file, or click &quot;New Manual Product&quot;
              at any time (even inside Excel Assisted mode) to add something the sheet doesn&apos;t have.
            </p>
          </div>
          <div>
            <p className="font-medium text-slate-700 dark:text-slate-300">Required inputs</p>
            <p>Customer Name and at least one product with a Product Name and a Price greater than 0.</p>
          </div>
          <div>
            <p className="font-medium text-slate-700 dark:text-slate-300">Step-by-step workflow</p>
            <p>Customer Info → Proposal Info → choose a mode → (upload Excel, if used) → select or add products → review the live totals → Generate.</p>
          </div>
          <div>
            <p className="font-medium text-slate-700 dark:text-slate-300">Generated outputs</p>
            <p>A Word document matching the Garg Dental proposal format, plus a print/PDF-ready on-screen preview.</p>
          </div>
        </div>
      )}
    </div>
  );
}
