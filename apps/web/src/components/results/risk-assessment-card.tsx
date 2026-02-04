"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { KYCRiskResult } from "@/lib/types/api";

interface RiskAssessmentCardProps {
  risk: KYCRiskResult | null;
}

const tierStyles = {
  Low: {
    badge: "bg-green-100 text-green-800 hover:bg-green-100",
    text: "text-green-600",
    bg: "bg-green-50",
    border: "border-green-200",
  },
  Medium: {
    badge: "bg-amber-100 text-amber-800 hover:bg-amber-100",
    text: "text-amber-600",
    bg: "bg-amber-50",
    border: "border-amber-200",
  },
  High: {
    badge: "bg-red-100 text-red-800 hover:bg-red-100",
    text: "text-red-600",
    bg: "bg-red-50",
    border: "border-red-200",
  },
};

const recommendationStyles = {
  Approve: "bg-green-100 text-green-800",
  Review: "bg-amber-100 text-amber-800",
  Reject: "bg-red-100 text-red-800",
};

export function RiskAssessmentCard({ risk }: RiskAssessmentCardProps) {
  if (!risk) {
    return (
      <Card className="border-gray-200">
        <CardHeader>
          <CardTitle className="text-lg">Risk Assessment</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">
            No risk assessment available. Upload and process a document to see risk scoring.
          </p>
        </CardContent>
      </Card>
    );
  }

  const style = tierStyles[risk.risk_tier];
  const scorePercent = Math.round(risk.risk_score * 100);

  return (
    <Card className={cn("border-gray-200", style.border)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Risk Assessment</CardTitle>
          <Badge className={recommendationStyles[risk.recommendation]}>
            {risk.recommendation}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Risk Score */}
        <div className={cn("rounded-sm p-4 text-center", style.bg)}>
          <div className={cn("text-5xl font-bold", style.text)}>
            {scorePercent}%
          </div>
          <div className="mt-2">
            <Badge variant="outline" className={style.badge}>
              {risk.risk_tier} Risk
            </Badge>
          </div>
        </div>

        {/* Risk Gauge Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-gray-500">
            <span>Low</span>
            <span>Medium</span>
            <span>High</span>
          </div>
          <div className="h-2 rounded-full bg-gray-200 overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500",
                scorePercent < 30 ? "bg-green-500" :
                scorePercent < 70 ? "bg-amber-500" : "bg-red-500"
              )}
              style={{ width: `${scorePercent}%` }}
            />
          </div>
        </div>

        {/* Risk Factors */}
        {risk.top_risk_factors.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-gray-700">Risk Factors</h4>
            <ul className="space-y-2">
              {risk.top_risk_factors.map((factor, index) => {
                const isNegative = factor.toLowerCase().includes("risk") ||
                  factor.toLowerCase().includes("match") ||
                  factor.toLowerCase().includes("negative");
                const isPositive = factor.toLowerCase().includes("clean") ||
                  factor.toLowerCase().includes("no ") ||
                  factor.toLowerCase().includes("low");

                return (
                  <li key={index} className="flex items-start gap-2 text-sm">
                    {isPositive ? (
                      <TrendingDown className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
                    ) : isNegative ? (
                      <TrendingUp className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
                    ) : (
                      <Minus className="h-4 w-4 text-gray-400 flex-shrink-0 mt-0.5" />
                    )}
                    <span className="text-gray-600">{factor}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
