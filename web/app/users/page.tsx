"use client";

import { useEffect, useState } from "react";
import { Users as UsersIcon, KeyRound, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Button } from "@/components/Button";
import { Table, type TableColumn } from "@/components/ui/Table";
import { Modal } from "@/components/ui/Modal";
import { Badge } from "@/components/ui/Badge";
import { CompanySelector } from "@/components/CompanySelector";
import { useCurrentUser } from "@/lib/useCurrentUser";
import { api } from "@/lib/apiClient";
import { ApiError } from "@/lib/types";
import type { ManagedUser } from "@/lib/types";

function CreateUserModal({
  companyId,
  onClose,
  onCreated,
}: {
  companyId: string;
  onClose: () => void;
  onCreated: (user: ManagedUser) => void;
}) {
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const user = await api.users.create({ company_id: companyId, username, full_name: fullName, password });
      onCreated(user);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not create the user.");
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "mb-3 w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-500";

  return (
    <Modal title="Add User" onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Full Name</label>
        <input required value={fullName} onChange={(e) => setFullName(e.target.value)} className={inputClass} />

        <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Username</label>
        <input required value={username} onChange={(e) => setUsername(e.target.value)} className={inputClass} />

        <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Password</label>
        <input
          required
          type="password"
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={inputClass}
        />

        {error && <ErrorBanner message={error} />}

        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Creating..." : "Create User"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function CreateSuperAdminModal({ onClose, onCreated }: { onClose: () => void; onCreated: (user: ManagedUser) => void }) {
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const user = await api.users.createSuperAdmin({ username, full_name: fullName, password });
      onCreated(user);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not create the Super Admin.");
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "mb-3 w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-500";

  return (
    <Modal title="Add Super Admin" onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Full Name</label>
        <input required value={fullName} onChange={(e) => setFullName(e.target.value)} className={inputClass} />

        <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Username</label>
        <input required value={username} onChange={(e) => setUsername(e.target.value)} className={inputClass} />

        <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Password</label>
        <input
          required
          type="password"
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={inputClass}
        />

        {error && <ErrorBanner message={error} />}

        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Creating..." : "Create Super Admin"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ResetSuperAdminPasswordModal({ user, onClose }: { user: ManagedUser; onClose: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.users.resetSuperAdminPassword(user.id, password);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not reset the password.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title={`Reset Password — ${user.fullName}`} onClose={onClose}>
      {success ? (
        <p className="text-sm text-slate-700 dark:text-slate-300">Password updated.</p>
      ) : (
        <form onSubmit={handleSubmit}>
          <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">New Password</label>
          <input
            required
            type="password"
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mb-3 w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-500"
          />
          {error && <ErrorBanner message={error} />}
          <div className="mt-4 flex flex-wrap justify-end gap-2">
            <Button type="button" variant="secondary" onClick={onClose}>
              Close
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Saving..." : "Reset Password"}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}

function ResetPasswordModal({ user, companyId, onClose }: { user: ManagedUser; companyId: string; onClose: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.users.resetPassword(user.id, companyId, password);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not reset the password.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title={`Reset Password — ${user.fullName}`} onClose={onClose}>
      {success ? (
        <p className="text-sm text-slate-700 dark:text-slate-300">Password updated.</p>
      ) : (
        <form onSubmit={handleSubmit}>
          <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">New Password</label>
          <input
            required
            type="password"
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mb-3 w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-500"
          />
          {error && <ErrorBanner message={error} />}
          <div className="mt-4 flex flex-wrap justify-end gap-2">
            <Button type="button" variant="secondary" onClick={onClose}>
              Close
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Saving..." : "Reset Password"}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}

export default function UsersPage() {
  const me = useCurrentUser();
  const [companyId, setCompanyId] = useState<string | null>(null);
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [resetTarget, setResetTarget] = useState<ManagedUser | null>(null);

  const [superAdmins, setSuperAdmins] = useState<ManagedUser[]>([]);
  const [superAdminError, setSuperAdminError] = useState<string | null>(null);
  const [showCreateSuperAdmin, setShowCreateSuperAdmin] = useState(false);
  const [superAdminResetTarget, setSuperAdminResetTarget] = useState<ManagedUser | null>(null);

  useEffect(() => {
    if (me?.role !== "super_admin" || !companyId) return;
    let cancelled = false;
    api.users
      .list(companyId)
      .then((res) => {
        if (!cancelled) setUsers(res.users);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.detail.message : "Could not load users.");
      });
    return () => {
      cancelled = true;
    };
  }, [me, companyId]);

  // Independent of the per-company CompanySelector above - Super Admins
  // aren't scoped to any company, so this loads regardless of companyId.
  useEffect(() => {
    if (me?.role !== "super_admin") return;
    let cancelled = false;
    api.users
      .listSuperAdmins()
      .then((res) => {
        if (!cancelled) setSuperAdmins(res.users);
      })
      .catch((err) => {
        if (!cancelled) setSuperAdminError(err instanceof ApiError ? err.detail.message : "Could not load Super Admins.");
      });
    return () => {
      cancelled = true;
    };
  }, [me]);

  async function toggleSuperAdminActive(user: ManagedUser) {
    try {
      const updated = await api.users.updateSuperAdmin(user.id, { active: !user.active });
      setSuperAdmins((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
    } catch (err) {
      setSuperAdminError(err instanceof ApiError ? err.detail.message : "Could not update the Super Admin.");
    }
  }

  async function removeSuperAdmin(user: ManagedUser) {
    if (!confirm(`Delete ${user.fullName}? This cannot be undone.`)) return;
    try {
      await api.users.removeSuperAdmin(user.id);
      setSuperAdmins((prev) => prev.filter((u) => u.id !== user.id));
    } catch (err) {
      setSuperAdminError(err instanceof ApiError ? err.detail.message : "Could not delete the Super Admin.");
    }
  }

  async function toggleActive(user: ManagedUser) {
    if (!companyId) return;
    try {
      const updated = await api.users.update(user.id, { company_id: companyId, active: !user.active });
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not update the user.");
    }
  }

  async function removeUser(user: ManagedUser) {
    if (!companyId) return;
    if (!confirm(`Delete ${user.fullName}? This cannot be undone.`)) return;
    try {
      await api.users.remove(user.id, companyId);
      setUsers((prev) => prev.filter((u) => u.id !== user.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not delete the user.");
    }
  }

  if (me === undefined) return null;

  if (me === null || me.role !== "super_admin") {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <PageHeader icon={UsersIcon} title="Users" description="Manage staff accounts." />
        <ErrorBanner message="You need Super Admin access to view this page." />
      </div>
    );
  }

  const superAdminColumns: TableColumn<ManagedUser>[] = [
    { header: "Name", render: (u) => u.fullName },
    { header: "Username", render: (u) => u.username },
    {
      header: "Role",
      render: (u) => <Badge>{u.role}</Badge>,
    },
    {
      header: "Status",
      render: (u) => (
        <button
          onClick={() => toggleSuperAdminActive(u)}
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            u.active
              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400"
              : "bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
          }`}
        >
          {u.active ? "Active" : "Disabled"}
        </button>
      ),
    },
    {
      header: "Actions",
      render: (u) => (
        <div className="flex gap-2">
          <button
            onClick={() => setSuperAdminResetTarget(u)}
            title="Reset password"
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            <KeyRound className="h-4 w-4" />
          </button>
          <button
            onClick={() => removeSuperAdmin(u)}
            title="Delete Super Admin"
            className="rounded-md p-1.5 text-red-500 hover:bg-red-50 hover:text-red-700 dark:hover:bg-red-950"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ];

  const columns: TableColumn<ManagedUser>[] = [
    { header: "Name", render: (u) => u.fullName },
    { header: "Username", render: (u) => u.username },
    {
      header: "Role",
      render: (u) => <Badge>{u.role}</Badge>,
    },
    {
      header: "Status",
      render: (u) => (
        <button
          onClick={() => toggleActive(u)}
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            u.active
              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400"
              : "bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
          }`}
        >
          {u.active ? "Active" : "Disabled"}
        </button>
      ),
    },
    {
      header: "Actions",
      render: (u) => (
        <div className="flex gap-2">
          <button
            onClick={() => setResetTarget(u)}
            title="Reset password"
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            <KeyRound className="h-4 w-4" />
          </button>
          <button
            onClick={() => removeUser(u)}
            title="Delete user"
            className="rounded-md p-1.5 text-red-500 hover:bg-red-50 hover:text-red-700 dark:hover:bg-red-950"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="mx-auto max-w-4xl p-6">
      <PageHeader icon={UsersIcon} title="Users" description="Manage Super Admins and staff accounts." />

      <div className="mb-8">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-slate-900 dark:text-slate-50">Super Admins</h2>
          <Button onClick={() => setShowCreateSuperAdmin(true)}>Add Super Admin</Button>
        </div>

        {superAdminError && (
          <div className="mb-4">
            <ErrorBanner message={superAdminError} />
          </div>
        )}

        <Table columns={superAdminColumns} rows={superAdmins} rowKey={(u) => u.id} emptyMessage="No Super Admins yet." />

        {showCreateSuperAdmin && (
          <CreateSuperAdminModal
            onClose={() => setShowCreateSuperAdmin(false)}
            onCreated={(u) => setSuperAdmins((prev) => [...prev, u])}
          />
        )}
        {superAdminResetTarget && (
          <ResetSuperAdminPasswordModal user={superAdminResetTarget} onClose={() => setSuperAdminResetTarget(null)} />
        )}
      </div>

      <hr className="mb-8 border-slate-200 dark:border-slate-800" />

      <h2 className="mb-4 text-base font-semibold text-slate-900 dark:text-slate-50">Staff</h2>

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <CompanySelector value={companyId} onChange={setCompanyId} />
        <Button onClick={() => setShowCreate(true)} disabled={!companyId}>
          Add User
        </Button>
      </div>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      <Table columns={columns} rows={users} rowKey={(u) => u.id} emptyMessage="No users yet." />

      {showCreate && companyId && (
        <CreateUserModal
          companyId={companyId}
          onClose={() => setShowCreate(false)}
          onCreated={(u) => setUsers((prev) => [...prev, u])}
        />
      )}
      {resetTarget && companyId && (
        <ResetPasswordModal user={resetTarget} companyId={companyId} onClose={() => setResetTarget(null)} />
      )}
    </div>
  );
}
