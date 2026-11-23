import {
  DatabaseStats,
  ImportResponse,
  CompareResponse,
  PaginatedResultsResponse,
  CandidateDetailResponse,
  ReviewHistoryItem
} from './types';

const API_BASE = '/api';

export async function getDatabaseStats(): Promise<DatabaseStats> {
  const res = await fetch(`${API_BASE}/database/stats`);
  if (!res.ok) throw new Error('Failed to fetch database statistics');
  return res.json();
}

export async function uploadCSV(file: File): Promise<ImportResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/imports`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail));
  }
  return res.json();
}

export async function runComparison(runId: string, fuzzyThreshold: number = 80): Promise<CompareResponse> {
  const res = await fetch(`${API_BASE}/imports/${runId}/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fuzzy_threshold: fuzzyThreshold })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Comparison failed' }));
    throw new Error(err.detail || 'Comparison failed');
  }
  return res.json();
}

export async function getRunStatus(runId: string): Promise<CompareResponse> {
  const res = await fetch(`${API_BASE}/imports/${runId}/status`);
  if (!res.ok) throw new Error('Failed to fetch run status');
  return res.json();
}

export interface ResultsFilterParams {
  page?: number;
  pageSize?: number;
  status?: string;
  method?: string;
  reviewDecision?: string;
  discoveryType?: string;
  q?: string;
  minSimilarity?: number;
  maxSimilarity?: number;
}

export async function getResults(
  runId: string,
  params: ResultsFilterParams = {}
): Promise<PaginatedResultsResponse> {
  const query = new URLSearchParams();
  if (params.page) query.append('page', params.page.toString());
  if (params.pageSize) query.append('page_size', params.pageSize.toString());
  if (params.status && params.status !== 'ALL') query.append('status', params.status);
  if (params.method && params.method !== 'ALL') query.append('method', params.method);
  if (params.reviewDecision && params.reviewDecision !== 'ALL') query.append('review_decision', params.reviewDecision);
  if (params.discoveryType && params.discoveryType !== 'ALL') query.append('discovery_type', params.discoveryType);
  if (params.q) query.append('q', params.q);
  if (params.minSimilarity !== undefined) query.append('min_similarity', params.minSimilarity.toString());
  if (params.maxSimilarity !== undefined) query.append('max_similarity', params.maxSimilarity.toString());

  const res = await fetch(`${API_BASE}/imports/${runId}/results?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch results');
  return res.json();
}

export async function getCandidateDetail(
  runId: string,
  uploadRecordId: string,
  entityId: number
): Promise<CandidateDetailResponse> {
  const res = await fetch(`${API_BASE}/imports/${runId}/candidates/${uploadRecordId}/${entityId}`);
  if (!res.ok) throw new Error('Failed to fetch candidate details');
  return res.json();
}

export async function submitReview(
  runId: string,
  candidateId: number,
  decision: 'confirmed_duplicate' | 'not_duplicate' | 'needs_review',
  reviewer: string = 'human_reviewer',
  reason?: string
): Promise<any> {
  const res = await fetch(`${API_BASE}/imports/${runId}/reviews`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      candidate_id: candidateId,
      decision,
      reviewer,
      reason,
      request_id: `req-${Date.now()}-${candidateId}`
    })
  });
  if (!res.ok) throw new Error('Failed to submit review');
  return res.json();
}

export async function triggerVerification(runId: string, candidateId: number): Promise<any> {
  const res = await fetch(`${API_BASE}/imports/${runId}/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ candidate_id: candidateId })
  });
  if (!res.ok) throw new Error('Verification failed');
  return res.json();
}

export function getExportUrl(runId: string, type: string): string {
  return `${API_BASE}/imports/${runId}/export?type=${type}`;
}
