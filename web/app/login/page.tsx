"use client";

import { Suspense, useState } from "react";
import Image from "next/image";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/Button";

function LoginForm() {
  const searchParams = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setError(body?.detail?.message ?? "Incorrect username or password.");
        return;
      }
      const next = searchParams.get("next") || "/";
      // Full navigation, not router.push: Sidebar/useCurrentUser() fetch
      // the logged-in user once per mount (useEffect with an empty dep
      // array). router.push()+router.refresh() re-fetches server data but
      // never remounts client components, so switching users in the same
      // tab (sign out, sign back in as someone else) left every
      // role-gated client component - the sidebar's nav links included -
      // showing the PREVIOUS user's role until a manual hard reload. A
      // full navigation remounts the whole app, guaranteeing every
      // component re-resolves the new session.
      window.location.href = next;
    } catch {
      setError("Could not reach the server. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 dark:bg-slate-950 px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-8 shadow-sm"
      >
        <Image
          src="/brand/garg-dental-logo.png"
          alt="Garg Dental"
          width={140}
          height={103}
          priority
          unoptimized
          className="mx-auto mb-4 h-20 w-auto"
        />
        <h1 className="text-center text-lg font-bold text-slate-900 dark:text-slate-50">Garg Dental</h1>
        <p className="mb-6 text-center text-sm text-slate-500 dark:text-slate-400">Operations Toolkit</p>

        <label htmlFor="username" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
          Username
        </label>
        <input
          id="username"
          type="text"
          autoFocus
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="mb-4 w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-500"
        />

        <label htmlFor="password" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
          Password
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mb-4 w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-500"
        />

        {error && <p className="mb-4 text-sm text-red-600 dark:text-red-400">{error}</p>}

        <Button type="submit" disabled={submitting || !username || !password} className="w-full">
          {submitting ? "Signing in..." : "Sign In"}
        </Button>
      </form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
