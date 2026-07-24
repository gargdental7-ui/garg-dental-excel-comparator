export function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="rounded-md border border-red-300 bg-red-50 dark:border-red-900 dark:bg-red-950 px-4 py-3 text-sm text-red-800 dark:text-red-200">
      {message}
    </div>
  );
}
