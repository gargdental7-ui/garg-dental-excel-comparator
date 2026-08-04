"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
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
  Sparkles,
  Menu,
  X,
} from "lucide-react";
import { clearCurrentUserCache, useCurrentUser } from "@/lib/useCurrentUser";
import type { Role } from "@/lib/types";

const LINKS: { href: string; label: string; icon: typeof GitCompare; roles: Role[] }[] = [
  { href: "/comparator", label: "Excel Comparator", icon: GitCompare, roles: ["super_admin", "staff"] },
  { href: "/collection", label: "Collection Analyzer", icon: Landmark, roles: ["super_admin", "staff"] },
  { href: "/inventory", label: "Inventory Analyzer", icon: PackageSearch, roles: ["super_admin", "staff"] },
  { href: "/quotation", label: "Smart Quotation Generator", icon: FileText, roles: ["super_admin", "staff"] },
  { href: "/quotation/history", label: "Quotation History", icon: History, roles: ["super_admin", "staff"] },
  { href: "/companies", label: "Companies", icon: Building2, roles: ["super_admin"] },
  { href: "/onboarding/new", label: "Onboard New Company", icon: Sparkles, roles: ["super_admin"] },
  { href: "/settings/master-excel", label: "Master Excel", icon: FileSpreadsheet, roles: ["super_admin"] },
  { href: "/settings/company-assets", label: "Company Assets", icon: Layers, roles: ["super_admin"] },
  { href: "/users", label: "Users", icon: UsersIcon, roles: ["super_admin"] },
  { href: "/activity", label: "Activity Logs", icon: Activity, roles: ["super_admin"] },
];

export function Sidebar() {
  const pathname = usePathname();
  const me = useCurrentUser();
  const [open, setOpen] = useState(false);

  // Close the drawer on every navigation - otherwise it's left covering the
  // newly-loaded page on phones, the most common off-canvas-drawer bug.
  // Adjusting state during render (React's documented pattern for "reset
  // state when a prop changes") instead of an effect - avoids an extra
  // render pass and the lint rule against synchronous setState in effects.
  const [lastPathname, setLastPathname] = useState(pathname);
  if (pathname !== lastPathname) {
    setLastPathname(pathname);
    setOpen(false);
  }

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    clearCurrentUserCache();
    // Full navigation, not router.push: see web/app/login/page.tsx's login
    // handler for why - router.push()+router.refresh() doesn't remount
    // client components, which previously left the PREVIOUS user's
    // role-gated UI showing after switching accounts in the same tab
    // (commit cc904db). Now that useCurrentUser() also caches across
    // mounts, a soft nav here would risk the same bug in a new form.
    window.location.href = "/login";
  }

  if (pathname === "/login") return null;

  // Before the current-user fetch resolves, show only the links every role
  // can see - never flash admin-only items (Users, Master Excel, Activity
  // Logs) to a staff account for the split second before `me` loads.
  const visibleLinks = LINKS.filter((link) => link.roles.includes(me ? me.role : "staff"));

  return (
    <>
      {/* Hamburger trigger: Sidebar is the only unconditionally-mounted
          component on every non-login route, so it owns this button. */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open menu"
        className="fixed top-3 left-3 z-50 flex h-10 w-10 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-700 shadow-sm md:hidden dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200 print:hidden"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Backdrop, mobile only, shown while the drawer is open */}
      {open && (
        <div
          onClick={() => setOpen(false)}
          aria-hidden="true"
          className="fixed inset-0 z-30 bg-slate-950/50 md:hidden print:hidden"
        />
      )}

      <aside
        className={
          "fixed inset-y-0 left-0 z-40 flex h-dvh w-64 shrink-0 flex-col border-r border-slate-200 bg-white transition-transform duration-200 ease-in-out md:relative md:z-auto md:translate-x-0 dark:border-slate-800 dark:bg-slate-900 print:hidden " +
          (open ? "translate-x-0" : "-translate-x-full")
        }
      >
        <div className="flex items-center justify-between px-5 py-5">
          <Link href="/" prefetch={false} className="flex items-center gap-2">
            <Image src="/brand/garg-dental-mark.png" alt="Garg Dental" width={28} height={28} priority unoptimized className="h-7 w-7" />
            <div className="leading-tight">
              <p className="text-sm font-bold text-slate-900 dark:text-slate-50">Garg Dental</p>
              <p className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Operations Toolkit</p>
            </div>
          </Link>
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label="Close menu"
            className="flex h-9 w-9 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 md:hidden dark:text-slate-400 dark:hover:bg-slate-800"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2">
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
    </>
  );
}
