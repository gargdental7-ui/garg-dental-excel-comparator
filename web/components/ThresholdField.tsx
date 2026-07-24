"use client";

export function ThresholdField({
  label,
  value,
  onChange,
  suffix,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  suffix?: string;
}) {
  return (
    <div className="flex items-center gap-3 py-1">
      <label className="w-56 shrink-0 text-sm text-slate-700 dark:text-slate-300">{label}</label>
      <div className="flex items-center gap-1">
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-32 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-sm text-slate-900 dark:text-slate-100"
        />
        {suffix && <span className="text-sm text-slate-500 dark:text-slate-400">{suffix}</span>}
      </div>
    </div>
  );
}
