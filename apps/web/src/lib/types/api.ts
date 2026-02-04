/**
 * TypeScript types matching the FastAPI backend schemas.
 * These types ensure type safety when interacting with the API.
 */

// ============================================================================
// User Types
// ============================================================================

export interface UserStats {
  total_documents: number;
  documents_by_type: Record<string, number>;
  documents_this_month: number;
  total_screenings: number;
  screenings_by_decision: Record<string, number>;
  screenings_this_month: number;
  average_risk_score: number | null;
  risk_tier_distribution: Record<string, number>;
  generated_at: string;
}

// ============================================================================
// Document Types
// ============================================================================

export type DocumentType = "passport" | "utility_bill" | "business_reg" | "drivers_license";

export type DocumentStatus = "processing" | "completed" | "failed";

export interface DocumentUploadResponse {
  document_id: string;
  status: DocumentStatus;
  message: string;
}

export interface DocumentResponse {
  id: string;
  customer_id: string | null;
  document_type: string;
  uploaded_at: string;
  file_size_bytes: number;
  processed: boolean;
  ocr_confidence: number | null;
  extracted_data: Record<string, unknown> | null;
  processing_error: string | null;
}

// Document-specific extracted data types
export interface PassportData {
  document_type: string;
  issuing_country: string;
  surname: string;
  given_names: string;
  passport_number: string;
  nationality: string;
  date_of_birth: string;
  sex: "M" | "F" | "X" | null;
  expiry_date: string;
  personal_number: string | null;
  mrz_line1: string | null;
  mrz_line2: string | null;
  full_name: string;
}

export interface UtilityBillData {
  name: string;
  address: string;
  bill_date: string;
  utility_provider: string;
  account_number: string | null;
  amount_due: number | null;
  due_date: string | null;
  utility_type: string | null;
  address_lines: string[];
}

export interface BusinessDocumentData {
  company_name: string;
  registration_number: string;
  directors: { name: string; title: string | null }[];
  registration_date: string;
  business_type: string | null;
  registered_address: string | null;
  jurisdiction: string | null;
  status: string | null;
}

// ============================================================================
// KYC Types
// ============================================================================

export type KYCStatus = "pending" | "approved" | "review" | "rejected";

export interface KYCDocumentSummary {
  document_id: string;
  document_type: string;
  processed: boolean;
  ocr_confidence: number | null;
  extracted_data: Record<string, unknown> | null;
  created_at: string;
}

export interface KYCSanctionsResult {
  screening_id: string;
  decision: "match" | "review" | "no_match";
  top_match_score: number | null;
  matched_name: string | null;
  screened_at: string;
}

export interface KYCAdverseMediaResult {
  article_count: number;
  average_sentiment: number | null;
  sentiment_category: "negative" | "neutral" | "positive" | null;
}

export interface KYCRiskResult {
  risk_score: number;
  risk_tier: "Low" | "Medium" | "High";
  recommendation: "Approve" | "Review" | "Reject";
  top_risk_factors: string[];
}

export interface KYCResult {
  customer_id: string;
  documents: KYCDocumentSummary[];
  sanctions_screening: KYCSanctionsResult | null;
  adverse_media: KYCAdverseMediaResult | null;
  risk_assessment: KYCRiskResult | null;
  overall_status: KYCStatus;
  created_at: string;
  updated_at: string;
}

export interface KYCBatchRequest {
  customer_ids: string[];
}

export interface KYCBatchResponse {
  results: KYCResult[];
  total_processed: number;
  total_approved: number;
  total_review: number;
  total_rejected: number;
  total_pending: number;
}

// ============================================================================
// API Error Types
// ============================================================================

export interface APIError {
  detail: string;
}

export interface ValidationError {
  detail: {
    loc: (string | number)[];
    msg: string;
    type: string;
  }[];
}
