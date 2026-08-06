"use client";

import type { QuotationCustomer, QuotationItem, QuotationProposal, QuotationTotals } from "@/lib/types";
import { computeItemTotal } from "@/lib/quotationTotals";

function fmt(n: number) {
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const TERMS: [string, string][] = [
  ["Prices", "Prices are in NRs on door delivery basis."],
  ["Taxes", "VAT is Inclusive as applicable."],
  ["Payment", "50% advance & balance remaining against delivery."],
  ["Delivery", "After 6-8 weeks after your confirmed order subject to meet the payment terms."],
  ["Warranty", "24 months from the date of installation, subject to conditions."],
];

export function QuotationPreview({
  customer,
  proposal,
  items,
  totals,
}: {
  customer: QuotationCustomer;
  proposal: QuotationProposal;
  items: QuotationItem[];
  totals: QuotationTotals;
}) {
  return (
    <div
      className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white p-8 text-slate-900"
      style={{ fontFamily: "Calibri, 'Segoe UI', Candara, Arial, sans-serif", lineHeight: 1.35 }}
    >
      <div className="text-center">
        <p className="text-lg font-bold italic text-[#1f3864]">{proposal.title || "Proposal"}</p>
        <p className="text-sm">Authorized Distributor - Garg Dental Pvt. Ltd</p>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-6 text-sm">
        <div className="text-center">
          <p className="font-semibold text-[#1f3864]">Submitted to:</p>
          <p>{customer.designation}</p>
          <p className="font-semibold">{customer.company_name || customer.customer_name}</p>
          <p>{customer.address}</p>
        </div>
        <div className="text-center">
          <p className="font-semibold text-[#1f3864]">Submitted by:</p>
          <p className="font-semibold">Garg Dental Pvt Ltd</p>
          <p>127, Gairidhara, Kathmandu, Bagmati, Nepal</p>
          <p>Tel: +977-1-4436544</p>
        </div>
      </div>

      <div className="mt-4 text-sm">
        {customer.reference_number && <p>Ref No: {customer.reference_number}</p>}
        <p>Date: {proposal.quotation_date}</p>
        <p className="mt-3 text-center font-semibold">Subject: {proposal.subject}</p>
      </div>

      <table className="mt-4 w-full border-collapse text-sm">
        <thead>
          <tr className="bg-[#c5e0b3]">
            <th className="border border-slate-400 p-2 text-left">S N</th>
            <th className="border border-slate-400 p-2 text-left">Description</th>
            <th className="border border-slate-400 p-2 text-right">Rate ({proposal.currency})</th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 && (
            <tr>
              <td colSpan={3} className="border border-slate-400 p-3 text-center text-slate-500">
                No products added yet.
              </td>
            </tr>
          )}
          {items.map((item, i) => {
            const total = computeItemTotal(item);
            return (
              <tr key={item.id}>
                <td className="border border-slate-400 p-2 align-top">{i + 1}.</td>
                <td className="border border-slate-400 p-2 align-top">
                  <p className="font-semibold">{item.product_name}</p>
                  {item.model && <p>MODEL : {item.model}</p>}
                  {item.brand && <p>BRAND: {item.brand}</p>}
                  {item.origin && <p>ORIGIN: {item.origin}</p>}
                  {item.image && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={item.image} alt={item.product_name} className="mt-1 h-20 w-20 object-cover" />
                  )}
                  {item.features.length > 0 && (
                    <>
                      <p className="mt-1 font-semibold">Key Features :</p>
                      {item.features.map((f, fi) => (
                        <p key={fi}>{f}</p>
                      ))}
                    </>
                  )}
                  {item.mrp > 0 && <p>MRP: {fmt(item.mrp)}</p>}
                  {item.warranty && <p>Warranty: {item.warranty}</p>}
                </td>
                <td className="border border-slate-400 p-2 text-right align-top">{fmt(total.line_total)}</td>
              </tr>
            );
          })}
          <tr>
            <td className="border border-slate-400 p-2" />
            <td className="border border-slate-400 p-2">Subtotal</td>
            <td className="border border-slate-400 p-2 text-right">{fmt(totals.subtotal)}</td>
          </tr>
          <tr>
            <td className="border border-slate-400 p-2" />
            <td className="border border-slate-400 p-2">Discount</td>
            <td className="border border-slate-400 p-2 text-right">{fmt(totals.discount)}</td>
          </tr>
          <tr>
            <td className="border border-slate-400 p-2" />
            <td className="border border-slate-400 p-2">VAT</td>
            <td className="border border-slate-400 p-2 text-right">{fmt(totals.vat)}</td>
          </tr>
          <tr className="font-semibold">
            <td className="border border-slate-400 p-2" />
            <td className="border border-slate-400 p-2">Grand Total</td>
            <td className="border border-slate-400 p-2 text-right">{fmt(totals.grand_total)}</td>
          </tr>
        </tbody>
      </table>

      <div className="mt-6 text-sm">
        <p className="mb-1 font-semibold underline">TERMS &amp; CONDITION</p>
        {TERMS.map(([label, text]) => (
          <p key={label}>
            {label}: {text}
          </p>
        ))}
      </div>

      <div className="mt-8 text-sm">
        <p>For &amp; on behalf of</p>
        <p className="mt-6">………………………………………</p>
        <p className="font-semibold">Garg Dental Pvt. Ltd</p>
        <p>Gairidhara, Kathmandu</p>
      </div>
    </div>
  );
}
