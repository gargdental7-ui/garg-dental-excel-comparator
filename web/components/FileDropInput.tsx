"use client";

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
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
      <p className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{label}</p>
      <label className="inline-flex cursor-pointer items-center rounded-md bg-slate-800 dark:bg-slate-100 px-3 py-1.5 text-sm font-medium text-white dark:text-slate-900 hover:opacity-90">
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
