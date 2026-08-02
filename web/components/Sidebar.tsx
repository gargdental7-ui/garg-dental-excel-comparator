"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  GitCompare,
  Landmark,
  PackageSearch,
  FileText,
  LogOut,
  History,
  FileSpreadsheet,
  Users as UsersIcon,
  Activity,
  Building2,
  Layers,
} from "lucide-react";
import { useCurrentUser } from "@/lib/useCurrentUser";
import type { Role } from "@/lib/types";

const LINKS: { href: string; label: string; icon: typeof GitCompare; roles: Role[] }[] = [
  { href: "/comparator", label: "Excel Comparator", icon: GitCompare, roles: ["super_admin", "staff"] },
  { href: "/collection", label: "Collection Analyzer", icon: Landmark, roles: ["super_admin", "staff"] },
  { href: "/inventory", label: "Inventory Analyzer", icon: PackageSearch, roles: ["super_admin", "staff"] },
  { href: "/quotation", label: "Smart Quotation Generator", icon: FileText, roles: ["super_admin", "staff"] },
  { href: "/quotation/history", label: "Quotation History", icon: History, roles: ["super_admin", "staff"] },
  { href: "/companies", label: "Companies", icon: Building2, roles: ["super_admin"] },
  { href: "/settings/master-excel", label: "Master Excel", icon: FileSpreadsheet, roles: ["super_admin"] },
  { href: "/settings/company-assets", label: "Company Assets", icon: Layers, roles: ["super_admin"] },
  { href: "/users", label: "Users", icon: UsersIcon, roles: ["super_admin"] },
  { href: "/activity", label: "Activity Logs", icon: Activity, roles: ["super_admin"] },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const me = useCurrentUser();

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  if (pathname === "/login") return null;

  // Before the current-user fetch resolves, show only the links every role
  // can see - never flash admin-only items (Users, Master Excel, Activity
  // Logs) to a staff account for the split second before `me` loads.
  const visibleLinks = LINKS.filter((link) => link.roles.includes(me ? me.role : "staff"));

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 print:hidden">
      <Link href="/" prefetch={false} className="flex items-center gap-2 px-5 py-5">
        <Image src="/brand/garg-dental-mark.png" alt="Garg Dental" width={28} height={28} priority unoptimized className="h-7 w-7" />
        <div className="leading-tight">
          <p className="text-sm font-bold text-slate-900 dark:text-slate-50">Garg Dental</p>
          <p className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Operations Toolkit</p>
        </div>
      </Link>

      <nav className="flex-1 space-y-1 px-3 py-2">
        {visibleLinks.map((link) => {
          const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
          const Icon = link.icon;
          return (
            <Link
              key={link.href}
              href={link.href}
              prefetch={false}
              className={
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors " +
                (active
                  ? "bg-brand-navy/10 text-brand-navy dark:bg-brand-cyan/10 dark:text-brand-cyan"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100")
              }
            >
              <Icon className="h-4 w-4" />
              {link.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-slate-200 px-3 py-3 dark:border-slate-800">
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
        >
          <LogOut className="h-4 w-4" />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
