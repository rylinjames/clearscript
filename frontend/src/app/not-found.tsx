import Link from "next/link";
import { ShieldCheck, ArrowLeft } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      <div className="bg-gray-100 rounded-2xl p-6 mb-6">
        <ShieldCheck className="w-12 h-12 text-gray-400" />
      </div>
      <h2 className="text-4xl font-bold text-gray-900 mb-2">404</h2>
      <p className="text-lg text-gray-500 mb-1">Page not found</p>
      <p className="text-sm text-gray-400 text-center max-w-md mb-8">
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <Link
        href="/"
        className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Dashboard
      </Link>
    </div>
  );
}
