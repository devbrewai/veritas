"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, AlertCircle, User } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { RiskAssessmentCard } from "@/components/results/risk-assessment-card";
import { ExtractedDataCard } from "@/components/results/extracted-data-card";
import { SanctionsCard } from "@/components/results/sanctions-card";
import { AdverseMediaCard } from "@/components/results/adverse-media-card";
import { getKYCResults } from "@/lib/api/client";
import type { KYCResult } from "@/lib/types/api";

const statusStyles = {
  pending: { badge: "bg-gray-100 text-gray-800", label: "Pending" },
  approved: { badge: "bg-green-100 text-green-800", label: "Approved" },
  review: { badge: "bg-amber-100 text-amber-800", label: "Review Required" },
  rejected: { badge: "bg-red-100 text-red-800", label: "Rejected" },
};

function LoadingSkeleton() {
  return (
    <div className="py-6 px-4 sm:py-8 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-6 sm:space-y-8">
        <Skeleton className="h-4 w-32" />
        <div className="flex items-center gap-4">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-6 w-20" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    </div>
  );
}

export default function ResultsPage() {
  const params = useParams();
  const customerId = decodeURIComponent(params.customerId as string);

  const [result, setResult] = useState<KYCResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadResults() {
      try {
        const data = await getKYCResults(customerId);
        setResult(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load results");
      } finally {
        setIsLoading(false);
      }
    }
    loadResults();
  }, [customerId]);

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (error) {
    return (
      <div className="py-6 px-4 sm:py-8 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto space-y-6">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="py-6 px-4 sm:py-8 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto space-y-6">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>No results found for customer: {customerId}</AlertDescription>
          </Alert>
        </div>
      </div>
    );
  }

  const status = statusStyles[result.overall_status];

  return (
    <div className="py-6 px-4 sm:py-8 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-6 sm:space-y-8">
        {/* Back Link */}
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Link>

        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-gray-100 flex items-center justify-center">
                <User className="h-5 w-5 text-gray-600" />
              </div>
              <div>
                <h1 className="text-xl sm:text-2xl font-semibold text-gray-900">
                  KYC Results
                </h1>
                <p className="text-sm text-gray-600">Customer ID: {customerId}</p>
              </div>
            </div>
          </div>
          <Badge className={status.badge} variant="outline">
            {status.label}
          </Badge>
        </div>

        {/* Results Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column */}
          <div className="space-y-6">
            <ExtractedDataCard documents={result.documents} />
            <SanctionsCard sanctions={result.sanctions_screening} />
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            <RiskAssessmentCard risk={result.risk_assessment} />
            <AdverseMediaCard adverseMedia={result.adverse_media} />
          </div>
        </div>

        {/* Timestamps */}
        <div className="flex flex-wrap gap-4 text-xs text-gray-400 pt-4 border-t border-gray-200">
          <span>Created: {new Date(result.created_at).toLocaleString()}</span>
          <span>Updated: {new Date(result.updated_at).toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
}
