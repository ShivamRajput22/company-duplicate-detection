import React from 'react';
import { ExternalLink } from 'lucide-react';
import { CandidateItem, ImportRowItem, PaginatedResultsResponse } from '../types';

// These are presentation groups of persisted classifications, never new matching rules.
export function getSections(data: PaginatedResultsResponse | null) {
  const candidates = data?.candidates || [];
  const byUpload = new Map<string, CandidateItem[]>();
  candidates.forEach(candidate => {
    const list = byUpload.get(candidate.upload_record_id) || [];
    list.push(candidate);
    byUpload.set(candidate.upload_record_id, list);
  });
  const cleared = (candidate: CandidateItem) => candidate.latest_review_decision === 'not_duplicate'
    || (!candidate.latest_review_decision && candidate.match_status === 'not_a_match');
  const ready = (data?.uploaded_rows || []).filter(row => row.record_validation_status === 'accepted'
    && (byUpload.get(row.upload_record_id) || []).every(cleared));
  const outstanding = candidates.filter(candidate => candidate.latest_review_decision !== 'not_duplicate');
  const potential = outstanding.filter(candidate => candidate.match_status === 'potential_duplicate');
  const exact = outstanding.filter(candidate => candidate.website_match_state === 'MATCH' && candidate.linkedin_match_state === 'MATCH');
  const other = outstanding.filter(candidate => !potential.includes(candidate) && !exact.includes(candidate));
  return { potential, exact, other, ready, byUpload };
}

export function safeExternalUrl(value?: string, linkedin = false): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(/^https?:\/\//i.test(value) ? value : `https://${value}`);
    if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password
      || !url.hostname.includes('.') || /[\s<>]/.test(value)) return undefined;
    if (linkedin && !(url.hostname === 'linkedin.com' || url.hostname.endsWith('.linkedin.com'))) return undefined;
    return url.href;
  } catch { return undefined; }
}

interface MatchingResultsProps {
  data: PaginatedResultsResponse | null;
  completed: boolean;
  fuzzyThreshold: number;
  busy: boolean;
  selectedCandidates: Set<number>;
  selectedReady: Set<string>;
  onSelectCandidates: (ids: Set<number>) => void;
  onSelectReady: (ids: Set<string>) => void;
  onInspect: (candidate: CandidateItem) => void;
  onMove: (direction: 'add' | 'remove') => void;
  onDownload: (type: string, section?: 'potential' | 'exact' | 'other' | 'ready') => void;
}

export const MatchingResults: React.FC<MatchingResultsProps> = ({ data, completed, fuzzyThreshold, busy, selectedCandidates,
  selectedReady, onSelectCandidates, onSelectReady, onInspect, onMove, onDownload }) => {
  const sections = getSections(completed ? data : null);
  const toggleCandidate = (id: number) => {
    const next = new Set(selectedCandidates);
    next.has(id) ? next.delete(id) : next.add(id);
    onSelectCandidates(next);
  };
  const toggleReady = (id: string) => {
    const next = new Set(selectedReady);
    next.has(id) ? next.delete(id) : next.add(id);
    onSelectReady(next);
  };
  const removable = sections.ready.filter(row => (sections.byUpload.get(row.upload_record_id) || []).length > 0);
  const link = (value?: string, linkedin = false) => {
    const href = safeExternalUrl(value, linkedin);
    if (!href) return <span title={value || 'Not provided'}>{value || '—'}</span>;
    return <a href={href} target="_blank" rel="noopener noreferrer" onClick={event => event.stopPropagation()}
      aria-label={linkedin ? `LinkedIn: ${value}` : undefined} className={linkedin ? 'linkedin-link' : 'website-link'}>
      {linkedin ? 'in' : <span title={value}>{value?.replace(/^https?:\/\//, '').replace(/\/$/, '')}</span>}
      {!linkedin && <ExternalLink size={11} aria-hidden="true" />}
    </a>;
  };
  const renderCandidates = (title: string, name: 'potential' | 'exact' | 'other', description: string, rows: CandidateItem[]) => (
    <section className={`result-section ${name}`} aria-labelledby={`${name}-heading`}>
      <div className="section-heading">
        <h2 id={`${name}-heading`}>{title} <span className="count">{completed ? rows.length : '—'}</span></h2>
        <button className="text-link" disabled={busy || !completed || !rows.length}
          onClick={() => onDownload('master_summary', name)}>Download ↓</button>
      </div>
      <p className="section-description">{description}</p>
      <div className="table-frame" tabIndex={0} aria-label={`${title} table`}>
        <table>
          <thead><tr>
            <th className="check-cell"><input type="checkbox" aria-label={`Select all ${title}`}
              disabled={busy || !rows.length} checked={rows.length > 0 && rows.every(row => selectedCandidates.has(row.candidate_id))}
              onChange={event => {
                const next = new Set(selectedCandidates);
                rows.forEach(row => event.target.checked ? next.add(row.candidate_id) : next.delete(row.candidate_id));
                onSelectCandidates(next);
              }} /></th>
            <th>Entity ID</th><th>Legal Name</th><th>Company Name</th><th>Website</th><th>LinkedIn</th><th>Category</th><th>Duplicate Status</th>
          </tr></thead>
          <tbody>{rows.map(row => (
            <tr key={row.candidate_id} className={selectedCandidates.has(row.candidate_id) ? 'selected-row' : ''}
              onClick={event => { if (busy) return; if (event.ctrlKey || event.metaKey) toggleCandidate(row.candidate_id); else onInspect(row); }}>
              <td className="check-cell" onClick={event => event.stopPropagation()}><input type="checkbox"
                disabled={busy} aria-label={`Select candidate ${row.candidate_id}`}
                checked={selectedCandidates.has(row.candidate_id)} onChange={() => toggleCandidate(row.candidate_id)} /></td>
              <td><button className="entity-link" disabled={busy} onClick={event => { event.stopPropagation(); onInspect(row); }}
                aria-label={`Review entity ${row.matched_entity_id} for row ${row.csv_row_number}`}>{row.matched_entity_id}</button></td>
              <td><span className="cell-value" title={row.matched_legal_name}>{row.matched_legal_name || '—'}</span></td>
              <td><span className="cell-value" title={row.matched_company_name}>{row.matched_company_name || '—'}</span>
                <small className="cell-value" title={`Upload row ${row.csv_row_number}: ${row.uploaded_company_name || row.uploaded_legal_name}`}>Row {row.csv_row_number} · {row.uploaded_company_name || row.uploaded_legal_name}</small></td>
              <td>{link(row.matched_domain)}</td><td className="linkedin-cell">{link(row.matched_linkedin, true)}</td>
              <td className="muted" title="Category is not stored by the existing backend">—</td>
              <td className="status-cell"><span>{name === 'exact' ? 'Exact identifiers' : name === 'potential' && row.name_similarity_percent != null ? `${row.name_similarity_percent.toFixed(1)}% similarity` : row.match_status.replace(/_/g, ' ')}</span>
                {name !== 'potential' && row.name_similarity_percent != null && <small>{row.name_similarity_percent.toFixed(1)}% name similarity</small>}
                {row.latest_review_decision && <small className="review-state">{row.latest_review_decision.replace(/_/g, ' ')}</small>}
              </td>
            </tr>
          ))}
          {!rows.length && <tr><td colSpan={8} className="empty-cell">{completed ? 'No records in this section.' : 'Upload a CSV and validate to see records.'}</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );

  return (
    <div className="results-layout">
      <div className="duplicate-column">
        {renderCandidates('Potential Duplications', 'potential',
          `Legal Name matches under the approved identifier rules at ${fuzzyThreshold}% similarity or above.`, sections.potential)}
        {renderCandidates('Exact Duplications', 'exact',
          'Both normalized Website Domain and LinkedIn URL match an existing company.', sections.exact)}
        <section className="result-section inactive" aria-labelledby="inactive-heading">
          <div className="section-heading"><h2 id="inactive-heading">Inactive Duplications</h2>
            <button className="text-link" disabled title="Inactive status is unavailable in the backend">Download ↓</button></div>
          <p className="section-description">Entries matching an inactive existing company.</p>
          <div className="table-frame"><table><thead><tr><th>Entity ID</th><th>Legal Name</th><th>Company Name</th><th>Website</th><th>LinkedIn</th><th>Category</th></tr></thead>
            <tbody><tr><td colSpan={6} className="empty-cell">Unavailable: the existing backend does not store active/inactive company status.</td></tr></tbody></table></div>
        </section>
        {sections.other.length > 0 && renderCandidates('Other Matches & Review', 'other',
          'Single-identifier matches, conflicts, insufficient data and related-name leads retain their original classification.', sections.other)}
      </div>
      <div className="transfer-actions" aria-label="Move selected records">
        <button className="primary-button" disabled={busy || !completed || !selectedCandidates.size} onClick={() => onMove('add')}>Add &gt;&gt;</button>
        <button className="primary-button" disabled={busy || !completed || !selectedReady.size} onClick={() => onMove('remove')}>&lt;&lt; Remove</button>
        {(selectedCandidates.size > 0 || selectedReady.size > 0) && <small>{selectedCandidates.size + selectedReady.size} selected</small>}
      </div>
      <section className="result-section ready" aria-labelledby="ready-heading">
        <div className="section-heading"><h2 id="ready-heading">Ready to Import <span className="count">{completed ? sections.ready.length : '—'}</span></h2>
          <button className="text-link" disabled={busy || !completed || !sections.ready.length} onClick={() => onDownload('uploaded_summary', 'ready')}>Download ↓</button></div>
        <p className="section-description">Accepted uploads with no blocking matches, or with every match cleared by review.</p>
        <div className="table-frame" tabIndex={0} aria-label="Ready to Import table"><table>
          <thead><tr><th className="check-cell"><input type="checkbox" aria-label="Select all removable ready records"
            disabled={busy || !removable.length} checked={removable.length > 0 && removable.every(row => selectedReady.has(row.upload_record_id))}
            onChange={event => onSelectReady(event.target.checked ? new Set(removable.map(row => row.upload_record_id)) : new Set())} /></th>
            <th>Company</th><th>Legal Name</th><th>Website</th><th>LinkedIn</th><th>Category</th></tr></thead>
          <tbody>{sections.ready.map((row: ImportRowItem) => {
            const canRemove = (sections.byUpload.get(row.upload_record_id) || []).length > 0;
            return <tr key={row.upload_record_id} className={selectedReady.has(row.upload_record_id) ? 'selected-row' : ''}
              onClick={() => { if (!busy && canRemove) toggleReady(row.upload_record_id); }}>
              <td className="check-cell" onClick={event => event.stopPropagation()}><input type="checkbox" disabled={busy || !canRemove}
                title={canRemove ? 'Select to return to review' : 'No candidate exists for a review; removal is not supported by the existing API.'}
                aria-label={`Select ready row ${row.csv_row_number}`} checked={selectedReady.has(row.upload_record_id)} onChange={() => toggleReady(row.upload_record_id)} /></td>
              <td><span className="cell-value" title={row.company_name_original}>{row.company_name_original || '—'}</span><small>Upload row {row.csv_row_number}</small></td>
              <td><span className="cell-value" title={row.legal_name_original}>{row.legal_name_original || '—'}</span></td>
              <td>{link(row.web_domain_original)}</td><td className="linkedin-cell">{link(row.linkedin_url_original, true)}</td><td className="muted">—</td>
            </tr>;
          })}
          {!sections.ready.length && <tr><td colSpan={6} className="empty-cell">{completed ? 'No records are ready to import.' : 'Validated records will appear here.'}</td></tr>}
          </tbody></table></div>
        <p className="table-note">Add saves “not duplicate” for selected matches. Remove reopens review for a selected upload. Unmatched uploads cannot be removed with the existing API.</p>
        <p className="table-note">Downloads contain original upload values. Ready records are not inserted into the master database.</p>
      </section>
    </div>
  );
};
