import Link from "next/link";
import { Terminal, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

const curlExample = `curl -X POST https://veritas-api.onrender.com/v1/kyc/process \\
  -H "X-API-Key: vrt_sk_..." \\
  -F "customer_id=cust_123" \\
  -F "document_type=passport" \\
  -F "file=@passport.jpg"

# Response (under 15s):
# { "risk_assessment": { "tier": "Low", "recommendation": "Approve" }, ... }`;

export function APIHero() {
  return (
    <section className="py-16 sm:py-24 bg-gray-950">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          {/* Left: copy */}
          <div>
            <p className="font-mono text-sm text-green-400 mb-4">
              POST /v1/kyc/process
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
              One API call replaces your entire KYC pipeline.
            </h2>
            <p className="text-lg text-gray-400 mb-8">
              Upload a document. Get a verified identity with sanctions screening
              and risk score in under 15 seconds.
            </p>
            <div className="flex flex-wrap gap-4">
              <Button asChild className="bg-white text-gray-900 hover:bg-gray-100">
                <Link href="/docs/API.md">
                  Read the docs
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Link>
              </Button>
              <Button
                asChild
                variant="outline"
                className="border-gray-600 text-gray-300 hover:border-gray-400 hover:text-white"
              >
                <Link href="/register">Try it free</Link>
              </Button>
            </div>
          </div>

          {/* Right: code block */}
          <div className="bg-gray-900 rounded-sm border border-gray-800 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-800">
              <Terminal className="h-4 w-4 text-gray-500" />
              <span className="text-xs text-gray-500 font-mono">terminal</span>
            </div>
            <pre className="p-4 sm:p-6 text-sm font-mono text-gray-300 overflow-x-auto">
              <code>{curlExample}</code>
            </pre>
          </div>
        </div>
      </div>
    </section>
  );
}
