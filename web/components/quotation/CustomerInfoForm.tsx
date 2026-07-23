"use client";

import type { QuotationCustomer } from "@/lib/types";

const INPUT_CLASS =
  "w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-sm text-slate-900 dark:text-slate-100";
const LABEL_CLASS = "mb-1 block text-sm text-slate-700 dark:text-slate-300";

function Field({
  label,
  required,
  value,
  onChange,
  textarea,
}: {
  label: string;
  required?: boolean;
  value: string;
  onChange: (value: string) => void;
  textarea?: boolean;
}) {
  return (
    <div>
      <label className={LABEL_CLASS}>
        {label}
        {required ? " *" : ""}
      </label>
      {textarea ? (
        <textarea rows={2} value={value} onChange={(e) => onChange(e.target.value)} className={INPUT_CLASS} />
      ) : (
        <input type="text" value={value} onChange={(e) => onChange(e.target.value)} className={INPUT_CLASS} />
      )}
    </div>
  );
}

export function CustomerInfoForm({
  value,
  onChange,
}: {
  value: QuotationCustomer;
  onChange: (value: QuotationCustomer) => void;
}) {
  function set<K extends keyof QuotationCustomer>(key: K, v: QuotationCustomer[K]) {
    onChange({ ...value, [key]: v });
  }

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
      <p className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Customer Information</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Customer Name" required value={value.customer_name} onChange={(v) => set("customer_name", v)} />
        <Field label="Contact Person" value={value.contact_person} onChange={(v) => set("contact_person", v)} />
        <Field label="Designation" value={value.designation} onChange={(v) => set("designation", v)} />
        <Field label="Company / Hospital Name" value={value.company_name} onChange={(v) => set("company_name", v)} />
        <Field label="Phone" value={value.phone} onChange={(v) => set("phone", v)} />
        <Field label="Email" value={value.email} onChange={(v) => set("email", v)} />
        <Field label="Reference Number" value={value.reference_number} onChange={(v) => set("reference_number", v)} />
        <div className="sm:col-span-2">
          <Field label="Address" textarea value={value.address} onChange={(v) => set("address", v)} />
        </div>
        <div className="sm:col-span-2">
          <Field label="Notes" textarea value={value.notes} onChange={(v) => set("notes", v)} />
        </div>
      </div>
    </div>
  );
}
