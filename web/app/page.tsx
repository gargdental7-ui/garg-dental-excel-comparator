import Link from "next/link";

const TOOLS = [
  {
    href: "/comparator",
    title: "Excel Comparator",
    description: "Compare two stock reports by product Code - every changed field, with old and new values.",
  },
  {
    href: "/collection",
    title: "Collection Priority Analyzer",
    description: "Find out which customers to follow up with first, from an outstanding/receivables report.",
  },
  {
    href: "/inventory",
    title: "Inventory Movement Analyzer",
    description: "Classify fast/slow/dead stock for the uploaded period from a stock movement report.",
  },
];

export default function HomePage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">Garg Dental Operations Toolkit</h1>
      <p className="mt-3 text-slate-600 dark:text-slate-400">
        Upload an Excel report, review the results, and export an actionable Excel file. Each upload is processed
        for this analysis only - files are read, analyzed, and discarded; nothing is stored on the server.
      </p>

      <div className="mt-10 space-y-4">
        {TOOLS.map((tool) => (
          <Link
            key={tool.href}
            href={tool.href}
            className="block rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 hover:border-slate-400 dark:hover:border-slate-600"
          >
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">{tool.title}</h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{tool.description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
