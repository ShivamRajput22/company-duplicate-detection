import React, { useEffect, useState } from 'react';
import { CandidateItem, CandidateDetailResponse } from '../types';
import { getCandidateDetail, submitReview } from '../api';

interface EvidenceDrawerProps {
  runId: string;
  candidate: CandidateItem | null;
  onClose: () => void;
  onReviewUpdated: () => void | Promise<void>;
  onBusyChange?: (busy: boolean) => void;
  disabled?: boolean;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({ runId, candidate, onClose, onReviewUpdated, onBusyChange, disabled }) => {
  const [detail, setDetail] = useState<CandidateDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [decision, setDecision] = useState<'confirmed_duplicate' | 'not_duplicate' | 'needs_review'>('needs_review');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const candidateId = candidate?.candidate_id;

  useEffect(() => {
    let cancelled = false;
    setDetail(null); setError(''); setMessage(''); setReason('');
    if (!candidate) return;
    setLoading(true);
    getCandidateDetail(runId, candidate.upload_record_id, candidate.matched_entity_id).then(result => {
      if (!cancelled) { setDetail(result); setDecision(result.candidate.latest_review_decision || 'needs_review'); }
    }).catch(err => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [runId, candidateId]);

  if (!candidate) return null;
  const save = async () => {
    if (saving || disabled || !detail) return;
    setSaving(true); onBusyChange?.(true); setError(''); setMessage('');
    let persisted = false;
    try {
      await submitReview(runId, candidate.candidate_id, decision, 'human_reviewer', reason || undefined);
      persisted = true;
      const refreshed = await getCandidateDetail(runId, candidate.upload_record_id, candidate.matched_entity_id);
      setDetail(refreshed); setReason('');
      await onReviewUpdated();
      setMessage('Review saved. Earlier decisions remain in the audit history.');
    } catch (err) { setError(`${persisted ? 'The review was saved, but refresh failed. ' : ''}${err instanceof Error ? err.message : 'Review failed.'}`); }
    finally { setSaving(false); onBusyChange?.(false); }
  };
  const item = detail?.candidate;
  return (
    <section className="evidence-panel" aria-labelledby="evidence-heading" aria-busy={loading || saving}>
      <div className="section-heading"><h2 id="evidence-heading">Candidate Evidence & Review</h2><button className="text-link" disabled={saving || disabled} onClick={onClose}>Close review</button></div>
      <p className="table-note">Run {runId} · Candidate {candidate.candidate_id} · Uploaded row {candidate.csv_row_number}</p>
      {loading && <p role="status">Loading evidence…</p>}
      {error && <p className="message error-message" role="alert">{error}</p>}
      {message && <p className="message notice-message" role="status">{message}</p>}
      {item && <>
        <div className="evidence-comparison"><div><h3>Uploaded company</h3>
          <dl><dt>Company Name</dt><dd>{item.uploaded_company_name || '—'}</dd><dt>Legal Name</dt><dd>{item.uploaded_legal_name || '—'}</dd>
            <dt>Website</dt><dd>{item.uploaded_domain || '—'}</dd><dt>LinkedIn</dt><dd>{item.uploaded_linkedin || '—'}</dd></dl></div>
          <div><h3>Master Entity {item.matched_entity_id}</h3><dl><dt>Legal Name</dt><dd>{item.matched_legal_name || '—'}</dd>
            <dt>Company Name</dt><dd>{item.matched_company_name || '—'}</dd><dt>Website</dt><dd>{item.matched_domain || '—'}</dd>
            <dt>LinkedIn</dt><dd>{item.matched_linkedin || '—'}</dd></dl></div></div>
        <div className="evidence-states"><span>Website: <strong>{item.website_match_state}</strong></span>
          <span>LinkedIn: <strong>{item.linkedin_match_state}</strong></span><span>Name similarity: <strong>{item.name_similarity_percent == null ? 'Not evaluated' : `${item.name_similarity_percent.toFixed(1)}%`}</strong></span></div>
        <p className="rationale">{item.rationale}</p>
        <form className="review-form" onSubmit={event => { event.preventDefault(); void save(); }}>
          <label htmlFor="review-decision">Review decision</label><select id="review-decision" value={decision} disabled={saving || disabled} onChange={event => setDecision(event.target.value as typeof decision)}>
            <option value="needs_review">Needs review</option><option value="confirmed_duplicate">Confirmed duplicate</option><option value="not_duplicate">Not a duplicate</option></select>
          <label htmlFor="review-reason">Review notes (optional)</label><textarea id="review-reason" value={reason} disabled={saving || disabled} onChange={event => setReason(event.target.value)} rows={2} />
          <button className="primary-button" type="submit" disabled={saving || disabled}>{saving ? 'Saving…' : 'Save review'}</button></form>
        <h3>Review Audit History</h3>
        <div className="neutral-table table-frame"><table><thead><tr><th>Time</th><th>Reviewer</th><th>Prior decision</th><th>Decision</th><th>Reason</th></tr></thead>
          <tbody>{detail.review_history.map(review => <tr key={review.review_id}><td>{new Date(review.reviewed_at).toLocaleString()}</td>
            <td>{review.reviewer}</td><td>{review.prior_decision?.replace(/_/g, ' ') || '—'}</td><td>{review.new_decision.replace(/_/g, ' ')}</td><td>{review.reason || '—'}</td></tr>)}
            {!detail.review_history.length && <tr><td colSpan={5} className="empty-cell">No review decisions yet.</td></tr>}</tbody></table></div>
      </>}
    </section>
  );
};
