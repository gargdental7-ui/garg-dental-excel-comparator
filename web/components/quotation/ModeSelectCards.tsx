"use client";

export type QuotationMode = "excel" | "manual";

function Card({
  title,
  description,
  active,
  onClick,
}: {
  title: string;
  description: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        "flex-1 rounded-lg border p-4 text-left transition " +
        (active
          ? "border-slate-800 dark:border-slate-100 bg-slate-50 dark:bg-slate-800"
          : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-400 dark:hover:border-slate-600")
      }
    >
      <p className="text-sm font-semibold text-slate-900 dark:text-slate-50">{title}</p>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{description}</p>
    </button>
  );
}

export function ModeSelectCards({
  mode,
  onChange,
}: {
  mode: QuotationMode | null;
  onChange: (mode: QuotationMode) => void;
}) {
  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
      <p className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">How do you want to build this quotation?</p>
      <div className="flex flex-col gap-3 sm:flex-row">
        <Card
          title="Excel Assisted"
          description="Upload a product Excel and automatically fill quotation information."
          active={mode === "excel"}
          onClick={() => onChange("excel")}
        />
        <Card
          title="Manual Product"
          description="Create a quotation manually without importing any product Excel."
          active={mode === "manual"}
          onClick={() => onChange("manual")}
        />
      </div>
    </div>
  );
}
