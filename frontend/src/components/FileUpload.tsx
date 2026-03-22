"use client";

import { useCallback, useState } from "react";
import { Upload, FileCheck } from "lucide-react";

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  label?: string;
}

export default function FileUpload({
  onFileSelect,
  accept = ".pdf,.doc,.docx,.txt,.csv",
  label = "Upload a document for analysis",
}: FileUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) {
        setSelectedFile(file);
        onFileSelect(file);
      }
    },
    [onFileSelect]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        setSelectedFile(file);
        onFileSelect(file);
      }
    },
    [onFileSelect]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors cursor-pointer ${
        dragOver
          ? "border-[#1e3a5f] bg-blue-50"
          : selectedFile
          ? "border-emerald-400 bg-emerald-50"
          : "border-gray-300 bg-gray-50 hover:border-[#1e3a5f] hover:bg-blue-50/50"
      }`}
    >
      <label className="cursor-pointer flex flex-col items-center gap-3">
        {selectedFile ? (
          <>
            <FileCheck className="w-10 h-10 text-emerald-500" />
            <p className="text-sm font-medium text-emerald-700">
              {selectedFile.name}
            </p>
            <p className="text-xs text-gray-500">
              {(selectedFile.size / 1024).toFixed(1)} KB &middot; Click or drag
              to replace
            </p>
          </>
        ) : (
          <>
            <Upload className="w-10 h-10 text-gray-400" />
            <p className="text-sm font-medium text-gray-700">{label}</p>
            <p className="text-xs text-gray-500">
              Drag &amp; drop or click to browse &middot; PDF, DOC, TXT, CSV
            </p>
          </>
        )}
        <input
          type="file"
          accept={accept}
          onChange={handleChange}
          className="hidden"
        />
      </label>
    </div>
  );
}
