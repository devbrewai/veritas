/**
 * API client for communicating with the FastAPI backend.
 * Handles authentication and error handling.
 */

import { getToken } from "@/lib/auth-client";
import type {
  DocumentResponse,
  DocumentUploadResponse,
  KYCBatchRequest,
  KYCBatchResponse,
  KYCResult,
  UserStats,
} from "@/lib/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Base fetch wrapper with authentication and error handling.
 */
async function fetchWithAuth<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getToken();

  if (!token) {
    throw new Error("Not authenticated");
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  return response.json();
}

/**
 * Upload a document for processing.
 * Uses FormData for multipart/form-data upload.
 */
export async function uploadDocument(
  file: File,
  customerId: string,
  documentType: string
): Promise<DocumentUploadResponse> {
  const token = await getToken();

  if (!token) {
    throw new Error("Not authenticated");
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("customer_id", customerId);
  formData.append("document_type", documentType);

  const response = await fetch(`${API_BASE_URL}/v1/documents/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(error.detail || `Upload failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Get a document by ID.
 */
export async function getDocument(documentId: string): Promise<DocumentResponse> {
  return fetchWithAuth<DocumentResponse>(`/v1/documents/${documentId}`);
}

/**
 * Get KYC results for a customer.
 */
export async function getKYCResults(customerId: string): Promise<KYCResult> {
  return fetchWithAuth<KYCResult>(`/v1/kyc/${encodeURIComponent(customerId)}`);
}

/**
 * Process KYC for multiple customers.
 */
export async function batchKYC(customerIds: string[]): Promise<KYCBatchResponse> {
  const request: KYCBatchRequest = { customer_ids: customerIds };
  return fetchWithAuth<KYCBatchResponse>("/v1/kyc/batch", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

/**
 * Get current user's statistics.
 */
export async function getUserStats(): Promise<UserStats> {
  return fetchWithAuth<UserStats>("/v1/users/me/stats");
}
