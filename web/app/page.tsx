import Link from "next/link";
import Image from "next/image";
import { GitCompare, Landmark, PackageSearch, FileText, ArrowRight, ShieldCheck, WifiOff, Database } from "lucide-react";

const TOOLS = [
  {
    href: "/comparator",
    title: "Excel Comparator",
    description: "Compare two stock reports by product Code - every changed field, with old and new values.",
    icon: GitCompare,
  },
  {
    href: "/collection",
    title: "Collection Priority Analyzer",
    description: "Find out which customers to follow up with first, from an outstanding/receivables report.",
    icon: Landmark,
  },
  {
    href: "/inventory",
    title: "Inventory Movement Analyzer",
    description: "Classify fast/slow/dead stock for the uploaded period from a stock movement report.",
    icon: PackageSearch,
  },
  {
    href: "/quotation",
    title: "Smart Quotation Generator",
    description: "Build a branded proposal from an Excel product list or manually, ready to send in minutes.",
    icon: FileText,
  },
];

const PRINCIPLES = [
  { icon: WifiOff, text: "Fully offline-capable analysis - no AI, no cloud processing" },
  { icon: Database, text: "Nothing you upload is stored - read, analyzed, discarded" },
  { icon: ShieldCheck, text: "Password-gated access to every tool" },
];

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export default function HomePage() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-12 sm:py-16">
      <div className="flex items-center gap-4">
        <Image src="/brand/garg-dental-mark.png" alt="Garg Dental" width={48} height={48} priority unoptimized className="h-12 w-12" />
        <div>
          <p className="text-sm font-medium text-brand-cyan">{greeting()}</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">
            Garg Dental Operations Toolkit
          </h1>
        </div>
      </div>
      <p className="mt-4 max-w-2xl text-slate-600 dark:text-slate-400">
        Upload an Excel report, review the results, and export an actionable Excel file or a branded quotation.
        Pick a tool below to get started.
      </p>

      <div className="mt-10 grid gap-4 sm:grid-cols-2">
        {TOOLS.map((tool) => {
          const Icon = tool.icon;
          return (
            <Link
              key={tool.href}
              href={tool.href}
              prefetch={false}
              className="group relative overflow-hidden rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-all hover:-translate-y-0.5 hover:border-brand-cyan/40 hover:shadow-lg dark:border-slate-800 dark:bg-slate-900"
            >
              <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-brand-navy/10 text-brand-navy transition-colors group-hover:bg-brand-navy group-hover:text-white dark:bg-brand-cyan/10 dark:text-brand-cyan dark:group-hover:bg-brand-cyan dark:group-hover:text-slate-950">
                <Icon className="h-5 w-5" />
              </div>
              <h2 className="mt-4 text-lg font-semibold text-slate-900 dark:text-slate-50">{tool.title}</h2>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{tool.description}</p>
              <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-brand-navy dark:text-brand-cyan">
                Open
                <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
              </span>
            </Link>
          );
        })}
      </div>

      <div className="mt-12 flex flex-col gap-4 rounded-xl border border-slate-200 bg-slate-50 p-6 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800 dark:bg-slate-900/50">
        {PRINCIPLES.map(({ icon: Icon, text }) => (
          <div key={text} className="flex items-center gap-2.5 text-sm text-slate-600 dark:text-slate-400">
            <Icon className="h-4 w-4 shrink-0 text-brand-cyan" />
            {text}
          </div>
        ))}
      </div>
    </div>
  );
}
