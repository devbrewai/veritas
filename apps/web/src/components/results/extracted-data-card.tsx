"use client";

import { FileText, User, Building2, CreditCard, MapPin, Calendar } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import type { KYCDocumentSummary } from "@/lib/types/api";

interface ExtractedDataCardProps {
  documents: KYCDocumentSummary[];
}

const documentTypeLabels: Record<string, string> = {
  passport: "Passport",
  utility_bill: "Utility Bill",
  business_reg: "Business Registration",
  drivers_license: "Driver's License",
};

const documentTypeIcons: Record<string, typeof FileText> = {
  passport: User,
  utility_bill: Building2,
  business_reg: CreditCard,
  drivers_license: User,
};

function DataField({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div className="space-y-1">
      <dt className="text-xs text-gray-500 uppercase tracking-wide">{label}</dt>
      <dd className="text-sm text-gray-900 font-medium">{value}</dd>
    </div>
  );
}

function PassportFields({ data }: { data: Record<string, unknown> }) {
  return (
    <dl className="grid grid-cols-2 gap-4">
      <DataField label="Full Name" value={data.full_name as string} />
      <DataField label="Passport Number" value={data.passport_number as string} />
      <DataField label="Nationality" value={data.nationality as string} />
      <DataField label="Date of Birth" value={data.date_of_birth as string} />
      <DataField label="Sex" value={data.sex as string} />
      <DataField label="Expiry Date" value={data.expiry_date as string} />
      <DataField label="Issuing Country" value={data.issuing_country as string} />
    </dl>
  );
}

function UtilityBillFields({ data }: { data: Record<string, unknown> }) {
  return (
    <dl className="grid grid-cols-2 gap-4">
      <DataField label="Name" value={data.name as string} />
      <DataField label="Provider" value={data.utility_provider as string} />
      <div className="col-span-2">
        <DataField label="Address" value={data.address as string} />
      </div>
      <DataField label="Bill Date" value={data.bill_date as string} />
      <DataField label="Amount Due" value={data.amount_due ? `$${data.amount_due}` : undefined} />
    </dl>
  );
}

function BusinessRegFields({ data }: { data: Record<string, unknown> }) {
  return (
    <dl className="grid grid-cols-2 gap-4">
      <DataField label="Company Name" value={data.company_name as string} />
      <DataField label="Registration Number" value={data.registration_number as string} />
      <DataField label="Business Type" value={data.business_type as string} />
      <DataField label="Registration Date" value={data.registration_date as string} />
      <DataField label="Jurisdiction" value={data.jurisdiction as string} />
      <DataField label="Status" value={data.status as string} />
      <div className="col-span-2">
        <DataField label="Registered Address" value={data.registered_address as string} />
      </div>
    </dl>
  );
}

function DocumentContent({ doc }: { doc: KYCDocumentSummary }) {
  const Icon = documentTypeIcons[doc.document_type] || FileText;
  const confidencePercent = doc.ocr_confidence ? Math.round(doc.ocr_confidence * 100) : 0;

  return (
    <div className="space-y-4">
      {/* Document Info Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-gray-400" />
          <span className="text-sm font-medium text-gray-900">
            {documentTypeLabels[doc.document_type] || doc.document_type}
          </span>
        </div>
        {doc.processed && (
          <Badge variant="outline" className="text-xs">
            {confidencePercent}% confidence
          </Badge>
        )}
      </div>

      {/* OCR Confidence Bar */}
      {doc.ocr_confidence && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-gray-500">
            <span>OCR Confidence</span>
            <span>{confidencePercent}%</span>
          </div>
          <Progress value={confidencePercent} className="h-1" />
        </div>
      )}

      {/* Extracted Fields */}
      {doc.extracted_data ? (
        <div className="pt-2">
          {doc.document_type === "passport" && (
            <PassportFields data={doc.extracted_data} />
          )}
          {doc.document_type === "utility_bill" && (
            <UtilityBillFields data={doc.extracted_data} />
          )}
          {doc.document_type === "business_reg" && (
            <BusinessRegFields data={doc.extracted_data} />
          )}
          {!["passport", "utility_bill", "business_reg"].includes(doc.document_type) && (
            <dl className="grid grid-cols-2 gap-4">
              {Object.entries(doc.extracted_data).map(([key, value]) => (
                <DataField
                  key={key}
                  label={key.replace(/_/g, " ")}
                  value={typeof value === "string" ? value : JSON.stringify(value)}
                />
              ))}
            </dl>
          )}
        </div>
      ) : (
        <p className="text-sm text-gray-500">
          {doc.processed ? "No data extracted" : "Document not yet processed"}
        </p>
      )}

      {/* Created Date */}
      <div className="flex items-center gap-1 text-xs text-gray-400 pt-2 border-t border-gray-100">
        <Calendar className="h-3 w-3" />
        <span>Uploaded {new Date(doc.created_at).toLocaleDateString()}</span>
      </div>
    </div>
  );
}

export function ExtractedDataCard({ documents }: ExtractedDataCardProps) {
  if (documents.length === 0) {
    return (
      <Card className="border-gray-200">
        <CardHeader>
          <CardTitle className="text-lg">Extracted Data</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">
            No documents uploaded yet. Upload a document to see extracted data.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (documents.length === 1) {
    return (
      <Card className="border-gray-200">
        <CardHeader>
          <CardTitle className="text-lg">Extracted Data</CardTitle>
        </CardHeader>
        <CardContent>
          <DocumentContent doc={documents[0]} />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-gray-200">
      <CardHeader>
        <CardTitle className="text-lg">Extracted Data</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue={documents[0].document_id} className="w-full">
          <TabsList className="w-full justify-start mb-4">
            {documents.map((doc) => (
              <TabsTrigger key={doc.document_id} value={doc.document_id}>
                {documentTypeLabels[doc.document_type] || doc.document_type}
              </TabsTrigger>
            ))}
          </TabsList>
          {documents.map((doc) => (
            <TabsContent key={doc.document_id} value={doc.document_id}>
              <DocumentContent doc={doc} />
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  );
}
