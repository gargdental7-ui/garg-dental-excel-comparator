import Link from "next/link";
import { ArrowLeft, type LucideIcon } from "lucide-react";

export function PageHeader({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
}) {
  return (
    <div className="mb-6 print:hidden">
      <Link
        href="/"
        prefetch={false}
        className="mb-3 inline-flex items-center gap-1 text-sm font-medium text-slate-500 transition-colors hover:text-brand-navy dark:text-slate-400 dark:hover:text-brand-cyan"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Dashboard
      </Link>
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-navy/10 text-brand-navy dark:bg-brand-cyan/10 dark:text-brand-cyan">
          <Icon className="h-5 w-5" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">{title}</h1>
      </div>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{description}</p>
    </div>
  );
}
