"use client";

import { AlertTriangle } from "lucide-react";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "warning" | "default";
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "default",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null;

  const btnColor =
    variant === "danger"
      ? "bg-red-600 hover:bg-red-700"
      : variant === "warning"
      ? "bg-amber-600 hover:bg-amber-700"
      : "bg-primary-600 hover:bg-primary-700";

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onCancel} />
      <div className="relative bg-white rounded-2xl shadow-xl max-w-md w-full mx-4 p-6 animate-scale-up">
        <div className="flex items-start gap-4">
          {variant !== "default" && (
            <div className={`p-2 rounded-full ${variant === "danger" ? "bg-red-100" : "bg-amber-100"}`}>
              <AlertTriangle className={`w-5 h-5 ${variant === "danger" ? "text-red-600" : "text-amber-600"}`} />
            </div>
          )}
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
            <p className="text-sm text-gray-500 mt-1">{message}</p>
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors ${btnColor}`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
