import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { DocumentUploadForm } from "@/components/upload/document-upload-form";

export default function UploadPage() {
  return (
    <div className="py-6 px-4 sm:py-8 sm:px-6 lg:px-8">
      <div className="max-w-2xl mx-auto space-y-6 sm:space-y-8">
        {/* Back Link */}
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Link>

        {/* Page Header */}
        <div className="space-y-2">
          <h1 className="text-xl sm:text-2xl font-semibold text-gray-900">
            Upload Document
          </h1>
          <p className="text-sm text-gray-600">
            Upload a document for automatic KYC processing including OCR extraction,
            sanctions screening, and risk scoring.
          </p>
        </div>

        {/* Upload Form */}
        <DocumentUploadForm />

        {/* Info Section */}
        <div className="rounded-sm border border-gray-200 bg-white p-6 space-y-4">
          <h3 className="text-sm font-medium text-gray-900">
            What happens after upload?
          </h3>
          <ul className="space-y-3 text-sm text-gray-600">
            <li className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center text-xs font-medium">
                1
              </span>
              <span>
                <strong>OCR Extraction:</strong> We extract text and data from your
                document using advanced OCR technology.
              </span>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center text-xs font-medium">
                2
              </span>
              <span>
                <strong>Sanctions Screening:</strong> Names are checked against OFAC
                and other international sanctions lists.
              </span>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center text-xs font-medium">
                3
              </span>
              <span>
                <strong>Risk Scoring:</strong> Our ML model assigns a risk tier
                (Low/Medium/High) with detailed explanations.
              </span>
            </li>
          </ul>
          <p className="text-xs text-gray-500">
            Processing typically takes 4-10 seconds depending on document complexity.
          </p>
        </div>
      </div>
    </div>
  );
}
