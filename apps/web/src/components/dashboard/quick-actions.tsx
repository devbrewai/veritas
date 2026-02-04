"use client";

import Link from "next/link";
import { Upload, FileStack } from "lucide-react";
import { Button } from "@/components/ui/button";

export function QuickActions() {
  return (
    <div className="flex flex-wrap gap-3">
      <Button asChild className="bg-gray-900 hover:bg-gray-800">
        <Link href="/dashboard/upload">
          <Upload className="h-4 w-4 mr-2" />
          Upload Document
        </Link>
      </Button>
      <Button asChild variant="outline">
        <Link href="/dashboard/batch">
          <FileStack className="h-4 w-4 mr-2" />
          Batch Process
        </Link>
      </Button>
    </div>
  );
}
