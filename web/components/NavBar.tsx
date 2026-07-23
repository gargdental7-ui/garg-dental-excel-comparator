"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

const LINKS = [
  { href: "/comparator", label: "Excel Comparator" },
  { href: "/collection", label: "Collection Analyzer" },
  { href: "/inventory", label: "Inventory Analyzer" },
  { href: "/quotation", label: "Smart Quotation Generator" },
];

export function NavBar() {
  const pathname = usePathname();
  const router = useRouter();

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  if (pathname === "/login") return null;

  return (
    <nav className="bg-[#1f2933] text-white">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-6 py-3">
        <Link href="/" className="text-sm font-bold tracking-wide">
          GARG DENTAL <span className="font-normal text-slate-400">Operations Toolkit</span>
        </Link>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 sm:gap-x-5">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={
                pathname === link.href
                  ? "text-sm font-semibold text-white"
                  : "text-sm text-slate-400 hover:text-white"
              }
            >
              {link.label}
            </Link>
          ))}
          <button onClick={handleLogout} className="text-sm text-slate-400 hover:text-white">
            Sign Out
          </button>
        </div>
      </div>
    </nav>
  );
}
