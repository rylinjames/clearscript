"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      <div className="bg-red-50 rounded-2xl p-6 mb-6">
        <AlertTriangle className="w-12 h-12 text-red-400" />
      </div>
      <h2 className="text-xl font-bold text-gray-900 mb-2">Something went wrong</h2>
      <p className="text-sm text-gray-500 text-center max-w-md mb-2">
        {error.message || "An unexpected error occurred while loading this page."}
      </p>
      {error.digest && (
        <p className="text-xs text-gray-400 mb-6 font-mono">Error ID: {error.digest}</p>
      )}
      <button
        onClick={reset}
        className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
      >
        <RefreshCw className="w-4 h-4" />
        Try again
      </button>
    </div>
  );
}
