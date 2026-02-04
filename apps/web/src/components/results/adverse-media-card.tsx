"use client";

import { Newspaper, CheckCircle, AlertTriangle, XCircle, TrendingDown, TrendingUp, Minus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { KYCAdverseMediaResult } from "@/lib/types/api";

interface AdverseMediaCardProps {
  adverseMedia: KYCAdverseMediaResult | null;
}

const sentimentStyles = {
  positive: {
    icon: TrendingUp,
    iconColor: "text-green-600",
    bgColor: "bg-green-50",
    badge: "bg-green-100 text-green-800",
    label: "Positive",
  },
  neutral: {
    icon: Minus,
    iconColor: "text-gray-600",
    bgColor: "bg-gray-50",
    badge: "bg-gray-100 text-gray-800",
    label: "Neutral",
  },
  negative: {
    icon: TrendingDown,
    iconColor: "text-red-600",
    bgColor: "bg-red-50",
    badge: "bg-red-100 text-red-800",
    label: "Negative",
  },
};

export function AdverseMediaCard({ adverseMedia }: AdverseMediaCardProps) {
  if (!adverseMedia) {
    return (
      <Card className="border-gray-200">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Newspaper className="h-5 w-5 text-gray-400" />
            <CardTitle className="text-lg">Adverse Media</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">
            No adverse media scan performed yet.
          </p>
        </CardContent>
      </Card>
    );
  }

  const hasArticles = adverseMedia.article_count > 0;
  const sentiment = adverseMedia.sentiment_category || "neutral";
  const style = sentimentStyles[sentiment as keyof typeof sentimentStyles] || sentimentStyles.neutral;
  const SentimentIcon = style.icon;

  // Overall status
  const StatusIcon = hasArticles
    ? adverseMedia.sentiment_category === "negative"
      ? XCircle
      : AlertTriangle
    : CheckCircle;
  const statusColor = hasArticles
    ? adverseMedia.sentiment_category === "negative"
      ? "text-red-600"
      : "text-amber-600"
    : "text-green-600";
  const statusBg = hasArticles
    ? adverseMedia.sentiment_category === "negative"
      ? "bg-red-50"
      : "bg-amber-50"
    : "bg-green-50";

  return (
    <Card className="border-gray-200">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Newspaper className="h-5 w-5 text-gray-400" />
            <CardTitle className="text-lg">Adverse Media</CardTitle>
          </div>
          <Badge className={hasArticles ? style.badge : "bg-green-100 text-green-800"}>
            {hasArticles ? `${adverseMedia.article_count} Articles` : "Clear"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Status */}
        <div className={cn("rounded-sm p-4 flex items-center gap-3", statusBg)}>
          <StatusIcon className={cn("h-8 w-8", statusColor)} />
          <div>
            <p className={cn("font-semibold", statusColor)}>
              {hasArticles
                ? `${adverseMedia.article_count} Article${adverseMedia.article_count !== 1 ? "s" : ""} Found`
                : "No Adverse Media Found"}
            </p>
            {hasArticles && (
              <p className="text-sm text-gray-600">
                Review recommended for media mentions
              </p>
            )}
          </div>
        </div>

        {/* Sentiment Analysis */}
        {hasArticles && adverseMedia.average_sentiment !== null && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-gray-700">Sentiment Analysis</h4>
            <div className={cn("rounded-sm p-3 flex items-center gap-2", style.bgColor)}>
              <SentimentIcon className={cn("h-5 w-5", style.iconColor)} />
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">
                  {style.label} Sentiment
                </p>
                <p className="text-xs text-gray-600">
                  Average score: {adverseMedia.average_sentiment.toFixed(2)}
                </p>
              </div>
            </div>
            <p className="text-xs text-gray-500">
              Sentiment ranges from -1.0 (negative) to +1.0 (positive)
            </p>
          </div>
        )}

        {/* Search Info */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700">Search Sources</h4>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline" className="text-xs">GDELT</Badge>
            <Badge variant="outline" className="text-xs">News Archives</Badge>
          </div>
        </div>

        {/* No articles message */}
        {!hasArticles && (
          <p className="text-sm text-gray-600">
            No negative news articles or adverse media mentions were found in our
            search of news databases and archives.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
