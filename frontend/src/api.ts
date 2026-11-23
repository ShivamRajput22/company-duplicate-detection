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
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || 'Failed to fetch run status');
  }
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
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || 'Failed to submit review');
  }
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
  return `${API_BASE}/imports/${encodeURIComponent(runId)}/export?type=${encodeURIComponent(type)}`;
}

export async function getAllResults(runId: string): Promise<PaginatedResultsResponse> {
  const first = await getResults(runId, { pageSize: 100 });
  const candidates = [...first.candidates];
  // Bounded batches, with no silent first-page truncation.
  for (let start = 2; start <= first.total_pages; start += 4) {
    const pages = await Promise.all(Array.from(
      { length: Math.min(4, first.total_pages - start + 1) },
      (_, index) => getResults(runId, { page: start + index, pageSize: 100 })
    ));
    pages.forEach(page => candidates.push(...page.candidates));
  }
  return { ...first, candidates };
}

export async function getRunReviews(runId: string): Promise<ReviewHistoryItem[]> {
  const res = await fetch(`${API_BASE}/imports/${encodeURIComponent(runId)}/reviews`);
  if (!res.ok) throw new Error('Failed to load review history');
  return res.json();
}

export function saveDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Filter complete records from the existing backend CSV exports. All field
// values, formula protection, column ordering and row grain remain server-owned.
export async function downloadExport(
  runId: string, type: string, selection?: { column: string; ids: Set<string>; name: string }
) {
  const res = await fetch(getExportUrl(runId, type));
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || 'CSV download failed');
  }
  if (!selection) {
    saveDownload(await res.blob(), `${runId}_${type}.csv`);
    return;
  }
  const text = (await res.text()).replace(/^\uFEFF/, '');
  const records: { raw: string; fields: string[] }[] = [];
  let start = 0, field = '', fields: string[] = [], quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') {
      if (quoted && text[i + 1] === '"') { field += '"'; i++; }
      else quoted = !quoted;
    } else if (ch === ',' && !quoted) {
      fields.push(field); field = '';
    } else if ((ch === '\r' || ch === '\n') && !quoted) {
      fields.push(field);
      records.push({ raw: text.slice(start, i), fields });
      if (ch === '\r' && text[i + 1] === '\n') i++;
      start = i + 1; field = ''; fields = [];
    } else field += ch;
  }
  if (start < text.length) records.push({ raw: text.slice(start), fields: [...fields, field] });
  const header = records.shift();
  const index = header?.fields.indexOf(selection.column) ?? -1;
  if (!header || index < 0) throw new Error('Unexpected export columns; download was stopped.');
  const selected = records.filter(row => selection.ids.has(row.fields[index]));
  if (new Set(selected.map(row => row.fields[index])).size !== selection.ids.size) {
    throw new Error('The exported records changed. Refresh the run before downloading.');
  }
  saveDownload(new Blob(['\uFEFF', [header.raw, ...selected.map(row => row.raw)].join('\r\n') + '\r\n'],
    { type: 'text/csv;charset=utf-8' }), `${runId}_${selection.name}.csv`);
}
