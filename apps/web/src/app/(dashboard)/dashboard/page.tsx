import { StatsCards } from "@/components/dashboard/stats-cards";
import { QuickActions } from "@/components/dashboard/quick-actions";
import { SavingsCalculator } from "@/components/comparison/savings-calculator";

export default function DashboardPage() {
  return (
    <div className="py-6 px-4 sm:py-8 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-6 sm:space-y-8">
        {/* Page Header */}
        <div className="space-y-2">
          <h1 className="text-xl sm:text-2xl font-semibold text-gray-900">
            Dashboard
          </h1>
          <p className="text-sm text-gray-600">
            Overview of your KYC document processing and screening activity.
          </p>
        </div>

        {/* Quick Actions */}
        <QuickActions />

        {/* Stats Cards */}
        <div className="space-y-4">
          <h2 className="text-sm font-medium uppercase tracking-wide text-gray-500">
            Statistics
          </h2>
          <StatsCards />
        </div>

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Getting Started Section */}
          <div className="rounded-sm border border-gray-200 bg-white p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Getting Started
            </h3>
            <div className="space-y-4">
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-10 h-10 rounded-sm bg-gray-100 text-gray-600 font-semibold flex items-center justify-center">
                  1
                </div>
                <div>
                  <h4 className="font-medium text-gray-900">Upload Documents</h4>
                  <p className="text-sm text-gray-600">
                    Upload passport, utility bill, or business registration documents
                    for KYC processing.
                  </p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-10 h-10 rounded-sm bg-gray-100 text-gray-600 font-semibold flex items-center justify-center">
                  2
                </div>
                <div>
                  <h4 className="font-medium text-gray-900">Automatic Processing</h4>
                  <p className="text-sm text-gray-600">
                    Documents are automatically extracted, screened against sanctions
                    lists, and scored for risk.
                  </p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-10 h-10 rounded-sm bg-gray-100 text-gray-600 font-semibold flex items-center justify-center">
                  3
                </div>
                <div>
                  <h4 className="font-medium text-gray-900">View Results</h4>
                  <p className="text-sm text-gray-600">
                    Review KYC results with risk tier, recommendation, and detailed
                    explanations.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* ROI Calculator */}
          <SavingsCalculator />
        </div>
      </div>
    </div>
  );
}
