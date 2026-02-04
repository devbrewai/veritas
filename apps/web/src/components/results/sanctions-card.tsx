"use client";

import { CheckCircle, AlertTriangle, XCircle, Shield } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { KYCSanctionsResult } from "@/lib/types/api";

interface SanctionsCardProps {
  sanctions: KYCSanctionsResult | null;
}

const decisionStyles = {
  no_match: {
    icon: CheckCircle,
    iconColor: "text-green-600",
    bgColor: "bg-green-50",
    borderColor: "border-green-200",
    badge: "bg-green-100 text-green-800",
    label: "Clear",
  },
  review: {
    icon: AlertTriangle,
    iconColor: "text-amber-600",
    bgColor: "bg-amber-50",
    borderColor: "border-amber-200",
    badge: "bg-amber-100 text-amber-800",
    label: "Review Required",
  },
  match: {
    icon: XCircle,
    iconColor: "text-red-600",
    bgColor: "bg-red-50",
    borderColor: "border-red-200",
    badge: "bg-red-100 text-red-800",
    label: "Match Found",
  },
};

export function SanctionsCard({ sanctions }: SanctionsCardProps) {
  if (!sanctions) {
    return (
      <Card className="border-gray-200">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-gray-400" />
            <CardTitle className="text-lg">Sanctions Screening</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">
            No sanctions screening performed yet.
          </p>
        </CardContent>
      </Card>
    );
  }

  const style = decisionStyles[sanctions.decision as keyof typeof decisionStyles] || decisionStyles.no_match;
  const Icon = style.icon;
  const matchScore = sanctions.top_match_score
    ? Math.round(sanctions.top_match_score * 100)
    : null;

  return (
    <Card className={cn("border-gray-200", style.borderColor)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-gray-400" />
            <CardTitle className="text-lg">Sanctions Screening</CardTitle>
          </div>
          <Badge className={style.badge}>{style.label}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Status */}
        <div className={cn("rounded-sm p-4 flex items-center gap-3", style.bgColor)}>
          <Icon className={cn("h-8 w-8", style.iconColor)} />
          <div>
            <p className={cn("font-semibold", style.iconColor)}>
              {sanctions.decision === "no_match"
                ? "No Sanctions Match"
                : sanctions.decision === "review"
                ? "Potential Match - Review Required"
                : "Sanctions Match Detected"}
            </p>
            {matchScore !== null && (
              <p className="text-sm text-gray-600">
                Match confidence: {matchScore}%
              </p>
            )}
          </div>
        </div>

        {/* Match Details */}
        {sanctions.matched_name && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-gray-700">Match Details</h4>
            <div className="bg-gray-50 rounded-sm p-3 text-sm">
              <p className="text-gray-600">
                <span className="font-medium">Matched Name:</span>{" "}
                {sanctions.matched_name}
              </p>
            </div>
          </div>
        )}

        {/* Lists Checked */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700">Lists Checked</h4>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline" className="text-xs">OFAC SDN</Badge>
            <Badge variant="outline" className="text-xs">OFAC Consolidated</Badge>
            <Badge variant="outline" className="text-xs">UN Sanctions</Badge>
          </div>
        </div>

        {/* Screened Date */}
        <p className="text-xs text-gray-400">
          Screened {new Date(sanctions.screened_at).toLocaleString()}
        </p>
      </CardContent>
    </Card>
  );
}
