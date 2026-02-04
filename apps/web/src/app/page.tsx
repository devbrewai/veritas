"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Shield,
  BarChart3,
  FileText,
} from "lucide-react";
import { useSession } from "@/lib/auth-client";
import { Button } from "@/components/ui/button";

export default function Home() {
  const router = useRouter();
  const { data: session, isPending } = useSession();

  // Redirect authenticated users to dashboard
  useEffect(() => {
    if (!isPending && session) {
      router.push("/dashboard");
    }
  }, [session, isPending, router]);

  // Show nothing while checking auth (prevents flash)
  if (isPending) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="h-8 w-8 border-4 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
      </div>
    );
  }

  // Show landing page for unauthenticated users
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-sm bg-gray-900 flex items-center justify-center">
                <span className="text-white font-bold text-sm">V</span>
              </div>
              <span className="text-lg font-semibold text-gray-900">Veritas</span>
            </div>
            <div className="flex items-center gap-3">
              <Button asChild variant="ghost">
                <Link href="/login">Sign In</Link>
              </Button>
              <Button asChild className="bg-gray-900 hover:bg-gray-800">
                <Link href="/register">Get Started</Link>
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="py-16 sm:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 mb-6">
            KYC Automation in{" "}
            <span className="text-green-600">Seconds</span>, Not Days
          </h1>
          <p className="text-lg sm:text-xl text-gray-600 max-w-2xl mx-auto mb-8">
            Automate document extraction, sanctions screening, and risk scoring for
            cross-border payments. Cut onboarding time by 95% and costs by 70%.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button asChild size="lg" className="bg-gray-900 hover:bg-gray-800">
              <Link href="/register">
                Start Free Trial
                <ArrowRight className="h-4 w-4 ml-2" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/login">View Demo</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-12 bg-white border-y border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-3xl sm:text-4xl font-bold text-gray-900">4s</div>
              <div className="text-sm text-gray-600">Processing Time</div>
            </div>
            <div>
              <div className="text-3xl sm:text-4xl font-bold text-gray-900">95%</div>
              <div className="text-sm text-gray-600">Time Saved</div>
            </div>
            <div>
              <div className="text-3xl sm:text-4xl font-bold text-gray-900">70%</div>
              <div className="text-sm text-gray-600">Cost Reduction</div>
            </div>
            <div>
              <div className="text-3xl sm:text-4xl font-bold text-gray-900">98%</div>
              <div className="text-sm text-gray-600">Accuracy</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 sm:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 text-center mb-12">
            Complete KYC Pipeline
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-white rounded-sm border border-gray-200 p-6">
              <div className="h-10 w-10 rounded-sm bg-blue-50 flex items-center justify-center mb-4">
                <FileText className="h-5 w-5 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Document Extraction
              </h3>
              <p className="text-sm text-gray-600">
                OCR extraction from passports, utility bills, and business documents
                with 96%+ accuracy.
              </p>
            </div>
            <div className="bg-white rounded-sm border border-gray-200 p-6">
              <div className="h-10 w-10 rounded-sm bg-red-50 flex items-center justify-center mb-4">
                <Shield className="h-5 w-5 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Sanctions Screening
              </h3>
              <p className="text-sm text-gray-600">
                Real-time screening against OFAC, EU, and UN sanctions lists with
                fuzzy matching.
              </p>
            </div>
            <div className="bg-white rounded-sm border border-gray-200 p-6">
              <div className="h-10 w-10 rounded-sm bg-green-50 flex items-center justify-center mb-4">
                <BarChart3 className="h-5 w-5 text-green-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                ML Risk Scoring
              </h3>
              <p className="text-sm text-gray-600">
                Explainable risk tiers (Low/Medium/High) with SHAP-based feature
                contributions.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Comparison */}
      <section className="py-16 sm:py-24 bg-white border-y border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 text-center mb-12">
            Manual KYC vs Veritas
          </h2>
          <div className="max-w-3xl mx-auto">
            <div className="grid grid-cols-3 gap-4 text-center mb-4">
              <div></div>
              <div className="text-sm font-medium text-gray-500">Manual</div>
              <div className="text-sm font-medium text-green-600">Veritas</div>
            </div>
            {[
              { metric: "Time per customer", manual: "48 hours", veritas: "4 seconds" },
              { metric: "Cost per customer", manual: "$150", veritas: "$45" },
              { metric: "Risk consistency", manual: "Variable", veritas: "ML-based" },
              { metric: "Scalability", manual: "Linear (hire)", veritas: "Instant" },
            ].map((row) => (
              <div
                key={row.metric}
                className="grid grid-cols-3 gap-4 py-4 border-t border-gray-100 items-center"
              >
                <div className="text-sm text-gray-600">{row.metric}</div>
                <div className="text-sm text-gray-400 text-center">{row.manual}</div>
                <div className="text-sm text-green-600 font-medium text-center">
                  {row.veritas}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 sm:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-4">
            Ready to automate your KYC?
          </h2>
          <p className="text-lg text-gray-600 mb-8">
            Start your free trial and process documents in seconds.
          </p>
          <Button asChild size="lg" className="bg-gray-900 hover:bg-gray-800">
            <Link href="/register">
              Get Started Free
              <ArrowRight className="h-4 w-4 ml-2" />
            </Link>
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded-sm bg-gray-900 flex items-center justify-center">
                <span className="text-white font-bold text-xs">V</span>
              </div>
              <span className="text-sm font-medium text-gray-900">Veritas</span>
            </div>
            <p className="text-xs text-gray-500">
              KYC/AML automation for cross-border payments
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
