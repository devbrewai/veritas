"use client";

import { useEffect, useState } from "react";
import { FileText, Activity, TrendingUp, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getUserStats } from "@/lib/api/client";
import type { UserStats } from "@/lib/types/api";

interface StatCardProps {
  title: string;
  value: string | number;
  description?: string;
  icon: React.ReactNode;
  trend?: {
    value: number;
    label: string;
  };
}

function StatCard({ title, value, description, icon, trend }: StatCardProps) {
  return (
    <Card className="border-gray-200">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-gray-600">
          {title}
        </CardTitle>
        <div className="text-gray-400">{icon}</div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-gray-900">{value}</div>
        {description && (
          <p className="text-xs text-gray-500 mt-1">{description}</p>
        )}
        {trend && (
          <div className="flex items-center gap-1 mt-2">
            <TrendingUp className="h-3 w-3 text-green-600" />
            <span className="text-xs text-green-600">+{trend.value}</span>
            <span className="text-xs text-gray-500">{trend.label}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function StatCardSkeleton() {
  return (
    <Card className="border-gray-200">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-4 rounded" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-16" />
        <Skeleton className="h-3 w-32 mt-2" />
      </CardContent>
    </Card>
  );
}

export function StatsCards() {
  const [stats, setStats] = useState<UserStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadStats() {
      try {
        const data = await getUserStats();
        setStats(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load stats");
      } finally {
        setIsLoading(false);
      }
    }
    loadStats();
  }, []);

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <StatCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card className="border-red-200 bg-red-50">
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="h-4 w-4" />
            <p className="text-sm">{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!stats) {
    return null;
  }

  const avgRiskScore = stats.average_risk_score
    ? `${(stats.average_risk_score * 100).toFixed(0)}%`
    : "N/A";

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        title="Total Documents"
        value={stats.total_documents}
        description={`${Object.keys(stats.documents_by_type).length} document types`}
        icon={<FileText className="h-4 w-4" />}
        trend={
          stats.documents_this_month > 0
            ? { value: stats.documents_this_month, label: "this month" }
            : undefined
        }
      />
      <StatCard
        title="Total Screenings"
        value={stats.total_screenings}
        description="Sanctions & adverse media"
        icon={<Activity className="h-4 w-4" />}
        trend={
          stats.screenings_this_month > 0
            ? { value: stats.screenings_this_month, label: "this month" }
            : undefined
        }
      />
      <StatCard
        title="Average Risk Score"
        value={avgRiskScore}
        description="Across all screenings"
        icon={<TrendingUp className="h-4 w-4" />}
      />
      <StatCard
        title="Risk Distribution"
        value={stats.risk_tier_distribution.Low || 0}
        description={`Low risk | ${stats.risk_tier_distribution.Medium || 0} Medium | ${stats.risk_tier_distribution.High || 0} High`}
        icon={<AlertTriangle className="h-4 w-4" />}
      />
    </div>
  );
}
