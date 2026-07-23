"use client";

import type { QuotationProposal } from "@/lib/types";

const INPUT_CLASS =
  "w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-sm text-slate-900 dark:text-slate-100";
const LABEL_CLASS = "mb-1 block text-sm text-slate-700 dark:text-slate-300";

function Field({
  label,
  value,
  onChange,
  textarea,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  textarea?: boolean;
}) {
  return (
    <div>
      <label className={LABEL_CLASS}>{label}</label>
      {textarea ? (
        <textarea rows={2} value={value} onChange={(e) => onChange(e.target.value)} className={INPUT_CLASS} />
      ) : (
        <input type="text" value={value} onChange={(e) => onChange(e.target.value)} className={INPUT_CLASS} />
      )}
    </div>
  );
}

export function ProposalInfoForm({
  value,
  onChange,
}: {
  value: QuotationProposal;
  onChange: (value: QuotationProposal) => void;
}) {
  function set<K extends keyof QuotationProposal>(key: K, v: QuotationProposal[K]) {
    onChange({ ...value, [key]: v });
  }

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
      <p className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Proposal Information</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <Field label="Proposal Title" value={value.title} onChange={(v) => set("title", v)} />
        </div>
        <div className="sm:col-span-2">
          <Field label="Subject" value={value.subject} onChange={(v) => set("subject", v)} />
        </div>
        <Field label="Quotation Date" value={value.quotation_date} onChange={(v) => set("quotation_date", v)} />
        <Field label="Validity" value={value.validity} onChange={(v) => set("validity", v)} />
        <Field label="Prepared By" value={value.prepared_by} onChange={(v) => set("prepared_by", v)} />
        <Field label="Currency" value={value.currency} onChange={(v) => set("currency", v)} />
      </div>
    </div>
  );
}
