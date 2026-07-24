"use client";

import { Upload } from "lucide-react";

export function FileDropInput({
  label,
  fileName,
  onChange,
}: {
  label: string;
  fileName: string | null;
  onChange: (file: File) => void;
}) {
  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 transition-colors hover:border-slate-300 dark:hover:border-slate-700">
      <p className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{label}</p>
      <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-md bg-brand-navy px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-brand-navy/90 dark:bg-brand-cyan dark:text-slate-950 dark:hover:bg-brand-cyan/90">
        <Upload className="h-3.5 w-3.5" />
        Choose File
        <input
          type="file"
          accept=".xlsx,.xlsm"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onChange(file);
          }}
        />
      </label>
      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{fileName ?? "No file selected"}</p>
    </div>
  );
}
