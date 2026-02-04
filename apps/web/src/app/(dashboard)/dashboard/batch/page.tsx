"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Loader2,
  FileStack,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Clock,
  ExternalLink,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { batchKYC } from "@/lib/api/client";
import type { KYCBatchResponse, KYCResult } from "@/lib/types/api";

const statusIcons = {
  pending: Clock,
  approved: CheckCircle,
  review: AlertTriangle,
  rejected: XCircle,
};

const statusColors = {
  pending: "text-gray-600",
  approved: "text-green-600",
  review: "text-amber-600",
  rejected: "text-red-600",
};

const statusBadges = {
  pending: "bg-gray-100 text-gray-800",
  approved: "bg-green-100 text-green-800",
  review: "bg-amber-100 text-amber-800",
  rejected: "bg-red-100 text-red-800",
};

export default function BatchPage() {
  const [customerIdsText, setCustomerIdsText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<KYCBatchResponse | null>(null);

  const customerIds = customerIdsText
    .split(/[\n,]/)
    .map((id) => id.trim())
    .filter((id) => id.length > 0);

  const canSubmit = customerIds.length > 0 && customerIds.length <= 10 && !isProcessing;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (customerIds.length === 0) {
      setError("Please enter at least one customer ID");
      return;
    }

    if (customerIds.length > 10) {
      setError("Maximum 10 customers per batch");
      return;
    }

    setIsProcessing(true);
    setError(null);
    setResults(null);

    try {
      const response = await batchKYC(customerIds);
      setResults(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Batch processing failed");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleClear = () => {
    setCustomerIdsText("");
    setResults(null);
    setError(null);
  };

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
        <div className="space-y-2">
          <h1 className="text-xl sm:text-2xl font-semibold text-gray-900">
            Batch KYC Processing
          </h1>
          <p className="text-sm text-gray-600">
            Process KYC results for multiple customers at once. Enter up to 10 customer IDs.
          </p>
        </div>

        {/* Input Form */}
        <Card className="border-gray-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileStack className="h-5 w-5 text-gray-400" />
              Customer IDs
            </CardTitle>
            <CardDescription>
              Enter customer IDs separated by commas or new lines (max 10)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="customerIds">Customer IDs</Label>
                <textarea
                  id="customerIds"
                  className="w-full min-h-32 p-3 rounded-sm border border-gray-200 text-sm focus:outline-none focus:ring-1 focus:ring-gray-400"
                  placeholder="cust_001&#10;cust_002&#10;cust_003"
                  value={customerIdsText}
                  onChange={(e) => setCustomerIdsText(e.target.value)}
                  disabled={isProcessing}
                />
                <p className="text-xs text-gray-500">
                  {customerIds.length} customer{customerIds.length !== 1 ? "s" : ""} entered
                  {customerIds.length > 10 && (
                    <span className="text-red-600"> (max 10)</span>
                  )}
                </p>
              </div>

              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="flex gap-3">
                <Button
                  type="submit"
                  disabled={!canSubmit}
                  className="bg-gray-900 hover:bg-gray-800"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    "Process Batch"
                  )}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleClear}
                  disabled={isProcessing}
                >
                  Clear
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Results */}
        {results && (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <Card className="border-gray-200">
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold text-gray-900">
                    {results.total_processed}
                  </div>
                  <p className="text-sm text-gray-500">Total Processed</p>
                </CardContent>
              </Card>
              <Card className="border-green-200 bg-green-50">
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold text-green-600">
                    {results.total_approved}
                  </div>
                  <p className="text-sm text-green-700">Approved</p>
                </CardContent>
              </Card>
              <Card className="border-amber-200 bg-amber-50">
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold text-amber-600">
                    {results.total_review}
                  </div>
                  <p className="text-sm text-amber-700">Review</p>
                </CardContent>
              </Card>
              <Card className="border-red-200 bg-red-50">
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold text-red-600">
                    {results.total_rejected}
                  </div>
                  <p className="text-sm text-red-700">Rejected</p>
                </CardContent>
              </Card>
            </div>

            {/* Results Table */}
            <Card className="border-gray-200">
              <CardHeader>
                <CardTitle>Results</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Customer ID</TableHead>
                      <TableHead>Documents</TableHead>
                      <TableHead>Risk Tier</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {results.results.map((result) => {
                      const StatusIcon = statusIcons[result.overall_status];
                      return (
                        <TableRow key={result.customer_id}>
                          <TableCell className="font-medium">
                            {result.customer_id}
                          </TableCell>
                          <TableCell>{result.documents.length}</TableCell>
                          <TableCell>
                            {result.risk_assessment ? (
                              <Badge
                                variant="outline"
                                className={
                                  result.risk_assessment.risk_tier === "Low"
                                    ? "bg-green-50 text-green-700 border-green-200"
                                    : result.risk_assessment.risk_tier === "Medium"
                                    ? "bg-amber-50 text-amber-700 border-amber-200"
                                    : "bg-red-50 text-red-700 border-red-200"
                                }
                              >
                                {result.risk_assessment.risk_tier}
                              </Badge>
                            ) : (
                              <span className="text-gray-400">N/A</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <StatusIcon
                                className={`h-4 w-4 ${statusColors[result.overall_status]}`}
                              />
                              <Badge className={statusBadges[result.overall_status]}>
                                {result.overall_status.charAt(0).toUpperCase() +
                                  result.overall_status.slice(1)}
                              </Badge>
                            </div>
                          </TableCell>
                          <TableCell className="text-right">
                            <Button asChild variant="ghost" size="sm">
                              <Link
                                href={`/dashboard/results/${encodeURIComponent(
                                  result.customer_id
                                )}`}
                              >
                                View
                                <ExternalLink className="h-3 w-3 ml-1" />
                              </Link>
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
