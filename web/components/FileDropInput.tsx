"use client";

import { useId, useState, type DragEvent } from "react";
import { FileSpreadsheet, Upload, X } from "lucide-react";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileDropInput({
  label,
  fileName,
  fileSize,
  onChange,
  onClear,
  accept = ".xlsx,.xlsm",
}: {
  label: string;
  fileName: string | null;
  fileSize?: number;
  onChange: (file: File) => void;
  onClear?: () => void;
  accept?: string;
}) {
  const inputId = useId();
  const [dragging, setDragging] = useState(false);

  function handleDrop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) onChange(file);
  }

  if (fileName) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <p className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{label}</p>
        <div className="flex items-center gap-3 rounded-md border border-brand-cyan/30 bg-brand-cyan/5 px-3 py-2.5 dark:bg-brand-cyan/10">
          <FileSpreadsheet className="h-8 w-8 shrink-0 text-brand-navy dark:text-brand-cyan" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">{fileName}</p>
            {fileSize !== undefined && (
              <p className="text-xs text-slate-500 dark:text-slate-400">{formatFileSize(fileSize)}</p>
            )}
          </div>
          {onClear && (
            <button
              type="button"
              onClick={onClear}
              aria-label={`Remove ${fileName}`}
              className="shrink-0 rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-200/70 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <p className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{label}</p>
      <label
        htmlFor={inputId}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed px-4 py-8 text-center transition-colors " +
          (dragging
            ? "border-brand-cyan bg-brand-cyan/5 dark:bg-brand-cyan/10"
            : "border-slate-300 hover:border-brand-cyan/50 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800/50")
        }
      >
        <Upload className={"h-6 w-6 " + (dragging ? "text-brand-cyan" : "text-slate-400")} />
        <p className="text-sm text-slate-600 dark:text-slate-300">
          <span className="font-semibold text-brand-navy dark:text-brand-cyan">Click to upload</span> or drag and
          drop
        </p>
        <p className="text-xs text-slate-400 dark:text-slate-500">Excel files ({accept.split(",").join(", ")})</p>
        <input
          id={inputId}
          type="file"
          accept={accept}
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onChange(file);
          }}
        />
      </label>
    </div>
  );
}
