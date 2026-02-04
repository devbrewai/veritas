"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { FileDropzone } from "./file-dropzone";
import { uploadDocument } from "@/lib/api/client";
import type { DocumentType } from "@/lib/types/api";

const DOCUMENT_TYPES: { value: DocumentType; label: string }[] = [
  { value: "passport", label: "Passport" },
  { value: "utility_bill", label: "Utility Bill" },
  { value: "business_reg", label: "Business Registration" },
  { value: "drivers_license", label: "Driver's License" },
];

type UploadStatus = "idle" | "uploading" | "success" | "error";

export function DocumentUploadForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [customerId, setCustomerId] = useState("");
  const [documentType, setDocumentType] = useState<DocumentType>("passport");
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [uploadedDocumentId, setUploadedDocumentId] = useState<string | null>(null);

  const canSubmit = file && customerId.trim() && documentType && status !== "uploading";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!file || !customerId.trim()) {
      setError("Please provide a file and customer ID");
      return;
    }

    setStatus("uploading");
    setError(null);

    try {
      const response = await uploadDocument(file, customerId.trim(), documentType);

      if (response.status === "completed" || response.status === "processing") {
        setStatus("success");
        setUploadedDocumentId(response.document_id);
        // Redirect to results after short delay
        setTimeout(() => {
          router.push(`/dashboard/results/${encodeURIComponent(customerId.trim())}`);
        }, 1500);
      } else {
        throw new Error(response.message || "Upload failed");
      }
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  };

  const handleReset = () => {
    setFile(null);
    setCustomerId("");
    setDocumentType("passport");
    setStatus("idle");
    setError(null);
    setUploadedDocumentId(null);
  };

  return (
    <Card className="border-gray-200">
      <CardHeader>
        <CardTitle>Upload Document</CardTitle>
        <CardDescription>
          Upload a document for KYC processing. Supports passport, utility bill,
          business registration, and driver's license.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* File Dropzone */}
          <div className="space-y-2">
            <Label>Document File</Label>
            <FileDropzone
              file={file}
              onFileSelect={setFile}
              disabled={status === "uploading" || status === "success"}
            />
          </div>

          {/* Customer ID */}
          <div className="space-y-2">
            <Label htmlFor="customerId">Customer ID</Label>
            <Input
              id="customerId"
              type="text"
              placeholder="e.g., cust_123 or john.doe@example.com"
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              disabled={status === "uploading" || status === "success"}
            />
            <p className="text-xs text-gray-500">
              A unique identifier for the customer (can be email, internal ID, etc.)
            </p>
          </div>

          {/* Document Type */}
          <div className="space-y-2">
            <Label htmlFor="documentType">Document Type</Label>
            <Select
              value={documentType}
              onValueChange={(value) => setDocumentType(value as DocumentType)}
              disabled={status === "uploading" || status === "success"}
            >
              <SelectTrigger id="documentType">
                <SelectValue placeholder="Select document type" />
              </SelectTrigger>
              <SelectContent>
                {DOCUMENT_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Error Alert */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Success Alert */}
          {status === "success" && (
            <Alert className="border-green-200 bg-green-50">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800">
                Document uploaded successfully! Redirecting to results...
              </AlertDescription>
            </Alert>
          )}

          {/* Submit Button */}
          <div className="flex gap-3">
            {status === "success" ? (
              <Button
                type="button"
                variant="outline"
                onClick={handleReset}
                className="flex-1"
              >
                Upload Another
              </Button>
            ) : (
              <>
                <Button
                  type="submit"
                  disabled={!canSubmit}
                  className="flex-1 bg-gray-900 hover:bg-gray-800"
                >
                  {status === "uploading" ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    "Upload & Process"
                  )}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleReset}
                  disabled={status === "uploading"}
                >
                  Clear
                </Button>
              </>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
