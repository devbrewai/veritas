"use client";

import { useCallback, useState } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { Upload, X, FileText, Image } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const ACCEPTED_TYPES = {
  "image/jpeg": [".jpg", ".jpeg"],
  "image/png": [".png"],
  "application/pdf": [".pdf"],
};

const MAX_SIZE = 10 * 1024 * 1024; // 10MB

interface FileDropzoneProps {
  onFileSelect: (file: File | null) => void;
  file: File | null;
  disabled?: boolean;
}

export function FileDropzone({ onFileSelect, file, disabled }: FileDropzoneProps) {
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
      setError(null);

      if (rejectedFiles.length > 0) {
        const errors = rejectedFiles[0].errors;
        if (errors.some((e) => e.message.includes("larger"))) {
          setError("File is too large. Maximum size is 10MB.");
        } else {
          setError("Invalid file type. Please upload JPG, PNG, or PDF.");
        }
        return;
      }

      if (acceptedFiles.length > 0) {
        onFileSelect(acceptedFiles[0]);
      }
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_SIZE,
    maxFiles: 1,
    disabled,
  });

  const removeFile = () => {
    onFileSelect(null);
    setError(null);
  };

  const getFileIcon = (type: string) => {
    if (type.startsWith("image/")) {
      return <Image className="h-8 w-8 text-gray-400" />;
    }
    return <FileText className="h-8 w-8 text-gray-400" />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (file) {
    return (
      <div className="rounded-sm border border-gray-200 bg-white p-4">
        <div className="flex items-center gap-4">
          {getFileIcon(file.type)}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">
              {file.name}
            </p>
            <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={removeFile}
            disabled={disabled}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-4 w-4" />
            <span className="sr-only">Remove file</span>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div
        {...getRootProps()}
        className={cn(
          "rounded-sm border-2 border-dashed p-8 transition-colors cursor-pointer",
          "flex flex-col items-center justify-center text-center",
          isDragActive
            ? "border-gray-400 bg-gray-50"
            : "border-gray-200 hover:border-gray-300 hover:bg-gray-50",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        <input {...getInputProps()} />
        <Upload className="h-10 w-10 text-gray-400 mb-4" />
        <p className="text-sm font-medium text-gray-900 mb-1">
          {isDragActive ? "Drop the file here" : "Drag and drop a file here"}
        </p>
        <p className="text-xs text-gray-500 mb-4">or click to browse</p>
        <p className="text-xs text-gray-400">
          Supports JPG, PNG, PDF up to 10MB
        </p>
      </div>
      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}
    </div>
  );
}
