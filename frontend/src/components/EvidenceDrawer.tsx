import React, { useState, useEffect } from 'react';
import { X, CheckCircle, XCircle, AlertTriangle, Clock, Sparkles, ExternalLink, ShieldCheck } from 'lucide-react';
import { CandidateItem, CandidateDetailResponse } from '../types';
import { getCandidateDetail, submitReview, triggerVerification } from '../api';

interface EvidenceDrawerProps {
  runId: string;
  candidate: CandidateItem | null;
  onClose: () => void;
  onReviewUpdated: () => void;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({
  runId,
  candidate,
  onClose,
  onReviewUpdated
}) => {
  const [detail, setDetail] = useState<CandidateDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedDecision, setSelectedDecision] = useState<'confirmed_duplicate' | 'not_duplicate' | 'needs_review' | null>(null);
  const [reviewReason, setReviewReason] = useState('');
  const [submittingReview, setSubmittingReview] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!candidate) {
      setDetail(null);
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    setSelectedDecision(candidate.latest_review_decision || null);
    setReviewReason('');

    getCandidateDetail(runId, candidate.upload_record_id, candidate.matched_entity_id)
      .then((data) => {
        setDetail(data);
        if (data.candidate.latest_review_decision) {
          setSelectedDecision(data.candidate.latest_review_decision);
        }
      })
      .catch((err) => setErrorMsg(err.message))
      .finally(() => setLoading(false));
  }, [candidate, runId]);

  if (!candidate) return null;

  const handleSaveReview = async () => {
    if (!selectedDecision) return;
    setSubmittingReview(true);
    try {
      await submitReview(runId, candidate.candidate_id, selectedDecision, 'human_reviewer', reviewReason);
      onReviewUpdated();
      // Reload detail
      const refreshed = await getCandidateDetail(runId, candidate.upload_record_id, candidate.matched_entity_id);
      setDetail(refreshed);
      setReviewReason('');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit review');
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleRunAiVerification = async () => {
    setAiLoading(true);
    try {
      await triggerVerification(runId, candidate.candidate_id);
      const refreshed = await getCandidateDetail(runId, candidate.upload_record_id, candidate.matched_entity_id);
      setDetail(refreshed);
    } catch (err: any) {
      setErrorMsg(err.message || 'AI verification failed');
    } finally {
      setAiLoading(false);
    }
  };

  const getMatchBadge = (state: string) => {
    if (state === 'MATCH') return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">MATCH</span>;
    if (state === 'CONFLICT') return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-300">CONFLICT</span>;
    return <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">UNAVAILABLE</span>;
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm transition-opacity" onClick={onClose} />

      {/* Drawer Body */}
      <div className="relative w-full max-w-2xl bg-white shadow-2xl flex flex-col h-full z-10 overflow-y-auto">
        {/* Header */}
        <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between border-b border-slate-800">
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg">Candidate Evidence & Review</span>
              <span className="text-xs bg-slate-800 text-teal-400 px-2 py-0.5 rounded font-mono">
                Pair #{candidate.candidate_id}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Run: {runId} | Source Row: {candidate.csv_row_number ? `Line ${candidate.csv_row_number}` : candidate.upload_record_id}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {errorMsg && (
          <div className="m-4 p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-md flex items-center justify-between">
            <span>{errorMsg}</span>
            <button onClick={() => setErrorMsg(null)} className="font-bold ml-2">×</button>
          </div>
        )}

        <div className="p-6 space-y-6 flex-1">
          {/* Side-by-Side Comparison */}
          <div>
            <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-3 flex items-center space-x-2">
              <span>Entity Comparison Breakdown</span>
            </h3>
            <div className="grid grid-cols-2 gap-4">
              {/* Uploaded Record */}
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-500 uppercase">Incoming Upload</span>
                  <span className="text-[11px] bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded font-mono">
                    {candidate.upload_record_id}
                  </span>
                </div>
                <div className="space-y-3">
                  <div>
                    <label className="text-[11px] text-slate-400 block">Company Name</label>
                    <p className="font-semibold text-sm text-slate-900">{candidate.uploaded_company_name || '—'}</p>
                  </div>
                  <div>
                    <label className="text-[11px] text-slate-400 block">Legal Name</label>
                    <p className="text-xs font-medium text-slate-800">{candidate.uploaded_legal_name || '—'}</p>
                  </div>
                  <div>
                    <label className="text-[11px] text-slate-400 block">Website Domain</label>
                    <p className="text-xs font-mono text-slate-700 break-all">{candidate.uploaded_domain || 'None / Missing'}</p>
                  </div>
                  <div>
                    <label className="text-[11px] text-slate-400 block">LinkedIn Profile</label>
                    <p className="text-xs font-mono text-slate-700 break-all">{candidate.uploaded_linkedin || 'None / Missing'}</p>
                  </div>
                </div>
              </div>

              {/* Master Record */}
              <div className="bg-teal-50/40 border border-teal-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-teal-800 uppercase">Master Entity</span>
                  <span className="text-[11px] bg-teal-200 text-teal-900 px-1.5 py-0.5 rounded font-bold font-mono">
                    ID #{candidate.matched_entity_id}
                  </span>
                </div>
                <div className="space-y-3">
                  <div>
                    <label className="text-[11px] text-slate-400 block">Company Name</label>
                    <p className="font-semibold text-sm text-slate-900">{candidate.matched_company_name || '—'}</p>
                  </div>
                  <div>
                    <label className="text-[11px] text-slate-400 block">Authoritative Legal Name</label>
                    <p className="text-xs font-bold text-slate-900">{candidate.matched_legal_name || '—'}</p>
                  </div>
                  <div>
                    <label className="text-[11px] text-slate-400 block">Website Domain</label>
                    <p className="text-xs font-mono text-slate-700 break-all">{candidate.matched_domain || 'None / Missing'}</p>
                  </div>
                  <div>
                    <label className="text-[11px] text-slate-400 block">LinkedIn URL</label>
                    <p className="text-xs font-mono text-slate-700 break-all">{candidate.matched_linkedin || 'None / Missing'}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Evidence States & Rationale */}
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-3">
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide">Deterministic Matching Evidence</h4>

            <div className="grid grid-cols-3 gap-2 py-2 border-y border-slate-200 text-center">
              <div>
                <span className="text-[11px] text-slate-500 block mb-1">Website Domain</span>
                {getMatchBadge(candidate.website_match_state)}
              </div>
              <div>
                <span className="text-[11px] text-slate-500 block mb-1">LinkedIn URL</span>
                {getMatchBadge(candidate.linkedin_match_state)}
              </div>
              <div>
                <span className="text-[11px] text-slate-500 block mb-1">Legal Name Similarity</span>
                <span className="text-xs font-bold text-slate-900">
                  {candidate.name_similarity_percent !== null && candidate.name_similarity_percent !== undefined
                    ? `${candidate.name_similarity_percent.toFixed(1)}%`
                    : 'N/A (Exact match)'}
                </span>
              </div>
            </div>

            <div>
              <span className="text-[11px] text-slate-500 font-medium block mb-1">Rule Rationale</span>
              <p className="text-xs text-slate-800 bg-white p-2.5 rounded border border-slate-200 font-sans leading-relaxed">
                {candidate.rationale}
              </p>
            </div>
          </div>

          {/* Human Review Decision Panel */}
          <div className="border border-slate-200 rounded-lg p-4 bg-white shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-bold text-slate-800 flex items-center space-x-1.5">
                <ShieldCheck className="w-4 h-4 text-teal-600" />
                <span>Human Review Action</span>
              </h4>
              {candidate.latest_review_decision ? (
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-indigo-100 text-indigo-800">
                  Current: {candidate.latest_review_decision.replace('_', ' ').toUpperCase()}
                </span>
              ) : (
                <span className="text-xs font-medium px-2 py-0.5 rounded bg-amber-100 text-amber-800">
                  Pending Review
                </span>
              )}
            </div>

            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setSelectedDecision('confirmed_duplicate')}
                className={`py-2 px-3 rounded-md text-xs font-semibold flex items-center justify-center space-x-1 border transition-all ${
                  selectedDecision === 'confirmed_duplicate'
                    ? 'bg-emerald-600 text-white border-emerald-600 shadow'
                    : 'bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100'
                }`}
              >
                <CheckCircle className="w-3.5 h-3.5" />
                <span>Confirm Duplicate</span>
              </button>

              <button
                type="button"
                onClick={() => setSelectedDecision('not_duplicate')}
                className={`py-2 px-3 rounded-md text-xs font-semibold flex items-center justify-center space-x-1 border transition-all ${
                  selectedDecision === 'not_duplicate'
                    ? 'bg-rose-600 text-white border-rose-600 shadow'
                    : 'bg-rose-50 text-rose-800 border-rose-200 hover:bg-rose-100'
                }`}
              >
                <XCircle className="w-3.5 h-3.5" />
                <span>Not a Duplicate</span>
              </button>

              <button
                type="button"
                onClick={() => setSelectedDecision('needs_review')}
                className={`py-2 px-3 rounded-md text-xs font-semibold flex items-center justify-center space-x-1 border transition-all ${
                  selectedDecision === 'needs_review'
                    ? 'bg-amber-600 text-white border-amber-600 shadow'
                    : 'bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100'
                }`}
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Needs Review</span>
              </button>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-700 block mb-1">
                Review Notes / Justification (optional)
              </label>
              <textarea
                value={reviewReason}
                onChange={(e) => setReviewReason(e.target.value)}
                placeholder="Enter explanation for decision..."
                rows={2}
                className="w-full text-xs p-2.5 border border-slate-300 rounded-md focus:ring-1 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <button
              onClick={handleSaveReview}
              disabled={!selectedDecision || submittingReview}
              className="w-full bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50 text-xs font-semibold py-2.5 rounded-md transition-colors"
            >
              {submittingReview ? 'Saving Decision...' : 'Save Decision (Append-Only)'}
            </button>
          </div>

          {/* Review Audit History */}
          {detail && detail.review_history && detail.review_history.length > 0 && (
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-2 flex items-center space-x-1">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span>Review Audit Trail ({detail.review_history.length})</span>
              </h4>
              <div className="space-y-2">
                {detail.review_history.map((rev) => (
                  <div key={rev.review_id} className="text-xs p-2 bg-white rounded border border-slate-200">
                    <div className="flex justify-between items-center text-slate-500 text-[11px] mb-1">
                      <span className="font-medium text-slate-800">{rev.reviewer}</span>
                      <span>{new Date(rev.reviewed_at).toLocaleString()}</span>
                    </div>
                    <div className="font-semibold text-slate-900">
                      Decision: <span className="text-teal-700 font-bold">{rev.new_decision}</span>
                      {rev.prior_decision && (
                        <span className="text-slate-400 font-normal"> (Prior: {rev.prior_decision})</span>
                      )}
                    </div>
                    {rev.reason && <p className="text-slate-600 mt-1 italic">"{rev.reason}"</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Optional AI Verification Panel */}
          <div className="border border-slate-200 rounded-lg p-4 bg-slate-50">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide flex items-center space-x-1.5">
                <Sparkles className="w-3.5 h-3.5 text-teal-600" />
                <span>Advisory Evidence Verification (Optional)</span>
              </h4>
              <button
                onClick={handleRunAiVerification}
                disabled={aiLoading}
                className="text-xs px-2.5 py-1 bg-white border border-teal-500 text-teal-700 rounded hover:bg-teal-50 font-medium transition-colors"
              >
                {aiLoading ? 'Verifying...' : 'Run Advisory Check'}
              </button>
            </div>
            {detail?.candidate.ai_verification_status ? (
              <div className="mt-2 bg-white p-3 rounded border border-teal-200 text-xs space-y-1">
                <div className="flex justify-between">
                  <span className="text-slate-500">Advisory Relationship:</span>
                  <span className="font-bold text-teal-800">{detail.candidate.ai_relationship_type}</span>
                </div>
                <p className="text-slate-700 mt-1">{detail.candidate.ai_reason}</p>
              </div>
            ) : (
              <p className="text-[11px] text-slate-500">
                AI verification is advisory only. Runs offline mock provider with zero paid external cost.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
