"use client";

import { useState, useCallback } from "react";
import { usePathname } from "next/navigation";
import { useUser } from "@clerk/nextjs";
import { MessageSquare, Send, Check, X, Loader2 } from "lucide-react";

/**
 * Bottom-of-page feedback form mounted in the (app) layout. Visible on
 * every authenticated page; pre-fills name + email from the Clerk user
 * if available, and auto-captures the current page path.
 *
 * Submits to POST /api/feedback. The endpoint persists every submission
 * to the backend feedback table for product analytics.
 */
export default function FeedbackFooter() {
  const pathname = usePathname();
  const { user } = useUser();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pre-fill from Clerk on first open
  const handleOpen = useCallback(() => {
    if (!open) {
      if (user && !name) {
        setName(user.fullName || user.firstName || "");
      }
      if (user && !email) {
        const primary = user.primaryEmailAddress?.emailAddress;
        if (primary) setEmail(primary);
      }
    }
    setOpen(!open);
    setSubmitted(false);
    setError(null);
  }, [open, user, name, email]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) {
      setError("Please write a short message before sending.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: message.trim(),
          name: name.trim() || undefined,
          email: email.trim() || undefined,
          page: pathname || undefined,
          user_id: user?.id,
        }),
      });
      if (!res.ok) {
        let detail = `Submission failed with status ${res.status}`;
        try {
          const errJson = await res.json();
          if (errJson?.detail) detail = String(errJson.detail);
        } catch { /* not JSON */ }
        throw new Error(detail);
      }
      setSubmitted(true);
      setMessage("");
      // Auto-close after a moment so the success state is visible
      setTimeout(() => {
        setOpen(false);
        setSubmitted(false);
      }, 2200);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not send feedback");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mt-12 border-t border-gray-200/60 pt-8 pb-12">
      <div className="max-w-3xl">
        {!open ? (
          <button
            onClick={handleOpen}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-gray-300 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-400 transition-colors shadow-sm"
          >
            <MessageSquare className="w-4 h-4 text-primary-600" />
            Send feedback
          </button>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200/60 shadow-sm p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-primary-600" />
                  Send feedback
                </h3>
                <p className="text-xs text-gray-500 mt-1">
                  What is working, what is broken, what is missing. Anything you tell us
                  goes straight to the founder.
                </p>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1"
                aria-label="Close feedback form"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {submitted ? (
              <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-4 flex items-center gap-3">
                <Check className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                <p className="text-sm text-emerald-900">Thanks — we got it. We read every submission.</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Name (optional)</label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-primary-600 focus:border-primary-600 outline-none"
                      placeholder="Your name"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Email (optional)</label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-primary-600 focus:border-primary-600 outline-none"
                      placeholder="you@company.com"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Your feedback
                  </label>
                  <textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    rows={4}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-primary-600 focus:border-primary-600 outline-none resize-y"
                    placeholder={`What were you trying to do on this page? What happened? What would have been better?\n\n(We'll know which page you sent this from automatically.)`}
                  />
                </div>

                {error && (
                  <div className="rounded-md bg-amber-50 border border-amber-200 p-2.5">
                    <p className="text-xs text-amber-800">{error}</p>
                  </div>
                )}

                <div className="flex items-center justify-between gap-3">
                  <p className="text-[11px] text-gray-500">
                    Sent from <code className="font-mono bg-gray-100 px-1.5 py-0.5 rounded">{pathname || "/"}</code>
                  </p>
                  <button
                    type="submit"
                    disabled={submitting || !message.trim()}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    {submitting ? "Sending..." : "Send feedback"}
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
