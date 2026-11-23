import React, { useState, useEffect } from 'react';
import {
  Search, Filter, RefreshCw, CheckCircle2, AlertTriangle,
  HelpCircle, Eye, Sliders, ChevronLeft, ChevronRight, Layers, FileDown
} from 'lucide-react';
import { getResults, ResultsFilterParams } from '../api';
import { CandidateItem, PaginatedResultsResponse } from '../types';
import { EvidenceDrawer } from '../components/EvidenceDrawer';

interface MatchingResultsProps {
  runId: string | null;
  onNavigateToExport: (runId: string) => void;
}

export const MatchingResults: React.FC<MatchingResultsProps> = ({
  runId,
  onNavigateToExport
}) => {
  const [resultsData, setResultsData] = useState<PaginatedResultsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateItem | null>(null);

  // Filters state
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [methodFilter, setMethodFilter] = useState('ALL');
  const [reviewFilter, setReviewFilter] = useState('ALL');
  const [discoveryFilter, setDiscoveryFilter] = useState<'ALL' | 'standard' | 'related_name'>('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  useEffect(() => {
    if (runId) {
      loadResults();
    }
  }, [runId, currentPage, statusFilter, methodFilter, reviewFilter, discoveryFilter]);

  const loadResults = () => {
    if (!runId) return;
    setLoading(true);

    const params: ResultsFilterParams = {
      page: currentPage,
      pageSize,
      status: statusFilter,
      method: methodFilter,
      reviewDecision: reviewFilter,
      discoveryType: discoveryFilter,
      q: searchQuery || undefined
    };

    getResults(runId, params)
      .then(setResultsData)
      .catch((err) => console.error('Failed to load results:', err))
      .finally(() => setLoading(false));
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    loadResults();
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'high_confidence_candidate':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">High Confidence</span>;
      case 'potential_duplicate':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300">Potential Duplicate</span>;
      case 'needs_review':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-300">Needs Review</span>;
      case 'insufficient_data':
        return <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">Insufficient Data</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700">{status}</span>;
    }
  };

  const getReviewBadge = (decision?: string | null) => {
    switch (decision) {
      case 'confirmed_duplicate':
        return <span className="px-2 py-0.5 rounded text-xs font-bold bg-emerald-600 text-white shadow-sm">Confirmed</span>;
      case 'not_duplicate':
        return <span className="px-2 py-0.5 rounded text-xs font-bold bg-rose-600 text-white shadow-sm">Not Duplicate</span>;
      case 'needs_review':
        return <span className="px-2 py-0.5 rounded text-xs font-bold bg-amber-500 text-white shadow-sm">Review Needed</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-500 border border-slate-200">Pending</span>;
    }
  };

  if (!runId) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-12 text-center max-w-lg mx-auto mt-10">
        <Layers className="w-12 h-12 text-slate-300 mx-auto mb-3" />
        <h3 className="text-base font-bold text-slate-800">No Matching Run Selected</h3>
        <p className="text-xs text-slate-500 mt-1 mb-4">
          Please upload a CSV file in the Dashboard & Upload page and run the comparison to view matching candidate results.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Run Header Banner */}
      <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Matching Results & Reviews</h1>
            <span className="text-xs font-mono font-bold bg-slate-800 text-teal-400 px-2 py-0.5 rounded">
              {runId}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Deterministic candidate pairs identified against 10,000 master entities.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={loadResults}
            className="flex items-center space-x-1.5 text-xs text-slate-700 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => onNavigateToExport(runId)}
            className="flex items-center space-x-1.5 text-xs text-white bg-slate-900 hover:bg-slate-800 px-3 py-1.5 rounded font-medium shadow-sm transition-colors"
          >
            <FileDown className="w-3.5 h-3.5 text-teal-400" />
            <span>Go to Exports</span>
          </button>
        </div>
      </div>

      {/* 5 Summary Metric Cards (Approved Visual Specification) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm border-l-4 border-l-blue-500">
          <span className="text-xs font-semibold text-slate-500 uppercase">Uploaded Rows</span>
          <p className="text-xl font-bold text-slate-900 mt-1">
            {resultsData ? resultsData.total_uploaded_rows : '—'}
          </p>
          <span className="text-[11px] text-slate-400">Incoming records</span>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm border-l-4 border-l-emerald-500">
          <span className="text-xs font-semibold text-emerald-700 uppercase">Strong Candidates</span>
          <p className="text-xl font-bold text-slate-900 mt-1">
            {resultsData ? resultsData.strong_candidates_count : '—'}
          </p>
          <span className="text-[11px] text-emerald-600 font-medium">Exact Domain / LinkedIn</span>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm border-l-4 border-l-amber-500">
          <span className="text-xs font-semibold text-amber-700 uppercase">Potential Fuzzy</span>
          <p className="text-xl font-bold text-slate-900 mt-1">
            {resultsData ? resultsData.potential_fuzzy_count : '—'}
          </p>
          <span className="text-[11px] text-amber-600 font-medium">Legal Name ≥ 80% fallback</span>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm border-l-4 border-l-rose-500">
          <span className="text-xs font-semibold text-rose-700 uppercase">Needs Review</span>
          <p className="text-xl font-bold text-slate-900 mt-1">
            {resultsData ? resultsData.needs_review_count : '—'}
          </p>
          <span className="text-[11px] text-rose-600 font-medium">Conflicting evidence</span>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm border-l-4 border-l-indigo-500">
          <span className="text-xs font-semibold text-indigo-700 uppercase">Reviewed Pairs</span>
          <p className="text-xl font-bold text-slate-900 mt-1">
            {resultsData ? resultsData.reviewed_count : '—'}
          </p>
          <span className="text-[11px] text-indigo-600 font-medium">Human decisions persisted</span>
        </div>
      </div>

      {/* Filter Row */}
      <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm space-y-3">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
          {/* Search bar */}
          <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search company name, legal name, or Entity ID..."
              className="w-full text-xs pl-9 pr-3 py-2 border border-slate-300 rounded-md focus:ring-1 focus:ring-teal-500 focus:outline-none"
            />
          </form>

          {/* Discovery Filter Toggle (Standard vs Trimark Related Leads) */}
          <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-md text-xs font-medium">
            <button
              type="button"
              onClick={() => { setDiscoveryFilter('ALL'); setCurrentPage(1); }}
              className={`px-3 py-1 rounded transition-colors ${discoveryFilter === 'ALL' ? 'bg-white shadow-sm text-slate-900 font-bold' : 'text-slate-600 hover:text-slate-900'}`}
            >
              All Pairs
            </button>
            <button
              type="button"
              onClick={() => { setDiscoveryFilter('standard'); setCurrentPage(1); }}
              className={`px-3 py-1 rounded transition-colors ${discoveryFilter === 'standard' ? 'bg-white shadow-sm text-slate-900 font-bold' : 'text-slate-600 hover:text-slate-900'}`}
            >
              Standard Rule Candidates
            </button>
            <button
              type="button"
              onClick={() => { setDiscoveryFilter('related_name'); setCurrentPage(1); }}
              className={`px-3 py-1 rounded transition-colors ${discoveryFilter === 'related_name' ? 'bg-white shadow-sm text-teal-800 font-bold' : 'text-slate-600 hover:text-slate-900'}`}
            >
              Related-Name Leads (Trimark)
            </button>
          </div>
        </div>

        {/* Dropdowns */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-slate-100 text-xs">
          <div>
            <label className="text-[11px] text-slate-500 block mb-1">Match Status</label>
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setCurrentPage(1); }}
              className="w-full p-1.5 border border-slate-300 rounded focus:ring-1 focus:ring-teal-500 bg-white"
            >
              <option value="ALL">All Statuses</option>
              <option value="high_confidence_candidate">High Confidence Candidate</option>
              <option value="potential_duplicate">Potential Duplicate (Fuzzy ≥80%)</option>
              <option value="needs_review">Needs Review (Conflicts)</option>
              <option value="insufficient_data">Insufficient Data</option>
            </select>
          </div>

          <div>
            <label className="text-[11px] text-slate-500 block mb-1">Match Method</label>
            <select
              value={methodFilter}
              onChange={(e) => { setMethodFilter(e.target.value); setCurrentPage(1); }}
              className="w-full p-1.5 border border-slate-300 rounded focus:ring-1 focus:ring-teal-500 bg-white"
            >
              <option value="ALL">All Methods</option>
              <option value="website">Website Domain</option>
              <option value="linkedin">LinkedIn Company URL</option>
              <option value="fuzzy_legal_name">Fuzzy Legal Name</option>
              <option value="related_name_lead">Related Name Lead</option>
            </select>
          </div>

          <div>
            <label className="text-[11px] text-slate-500 block mb-1">Human Review Decision</label>
            <select
              value={reviewFilter}
              onChange={(e) => { setReviewFilter(e.target.value); setCurrentPage(1); }}
              className="w-full p-1.5 border border-slate-300 rounded focus:ring-1 focus:ring-teal-500 bg-white"
            >
              <option value="ALL">All Decisions</option>
              <option value="pending">Pending</option>
              <option value="confirmed_duplicate">Confirmed Duplicate</option>
              <option value="not_duplicate">Not a Duplicate</option>
              <option value="needs_review">Needs Review</option>
            </select>
          </div>
        </div>
      </div>

      {/* Results Table */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-100 text-slate-700">
              <tr>
                <th className="px-4 py-3 text-left font-bold">Uploaded Company</th>
                <th className="px-4 py-3 text-left font-bold">Matched Entity ID</th>
                <th className="px-4 py-3 text-left font-bold">Matched Legal Name</th>
                <th className="px-4 py-3 text-left font-bold">Match Method(s)</th>
                <th className="px-4 py-3 text-left font-bold">Name Similarity (%)</th>
                <th className="px-4 py-3 text-left font-bold">Match Status</th>
                <th className="px-4 py-3 text-left font-bold">Review Decision</th>
                <th className="px-4 py-3 text-center font-bold">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-400">
                    Loading matching candidate results...
                  </td>
                </tr>
              ) : !resultsData || resultsData.candidates.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-400">
                    No candidate matches found matching the selected filters.
                  </td>
                </tr>
              ) : (
                resultsData.candidates.map((c) => (
                  <tr key={c.candidate_id} className="hover:bg-slate-50/80 transition-colors">
                    {/* Uploaded Company */}
                    <td className="px-4 py-3">
                      <div className="font-semibold text-slate-900">{c.uploaded_company_name || '—'}</div>
                      <div className="text-[11px] text-slate-500">{c.uploaded_legal_name || '—'}</div>
                    </td>

                    {/* Matched Entity ID (AC-03: Real Entity ID, never IMPORT_BATCH) */}
                    <td className="px-4 py-3 font-mono">
                      <span className="font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                        #{c.matched_entity_id}
                      </span>
                    </td>

                    {/* Matched Legal Name (AC-04: adjacent legal name) */}
                    <td className="px-4 py-3">
                      <div className="font-semibold text-slate-900">{c.matched_legal_name || '—'}</div>
                      <div className="text-[11px] text-slate-400 font-mono truncate max-w-xs">{c.matched_domain || '—'}</div>
                    </td>

                    {/* Match Method(s) */}
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {c.match_methods.map((m) => (
                          <span key={m} className="px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded text-[10px] font-mono border border-slate-200">
                            {m}
                          </span>
                        ))}
                      </div>
                    </td>

                    {/* Name Similarity (%) */}
                    <td className="px-4 py-3 font-mono font-semibold">
                      {c.name_similarity_percent !== null && c.name_similarity_percent !== undefined ? (
                        <span className="text-teal-700 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                          {c.name_similarity_percent.toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-slate-400 font-normal">N/A</span>
                      )}
                    </td>

                    {/* Match Status */}
                    <td className="px-4 py-3">
                      {getStatusBadge(c.match_status)}
                    </td>

                    {/* Review Decision */}
                    <td className="px-4 py-3">
                      {getReviewBadge(c.latest_review_decision)}
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => setSelectedCandidate(c)}
                        className="inline-flex items-center space-x-1 text-xs bg-white text-slate-700 hover:text-teal-700 border border-slate-300 hover:border-teal-500 px-2.5 py-1 rounded transition-colors shadow-sm font-medium"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Evidence & Review</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        {resultsData && resultsData.total_pages > 1 && (
          <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-600">
            <span>
              Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, resultsData.total_candidates)} of {resultsData.total_candidates} candidate pairs
            </span>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                disabled={currentPage === 1}
                className="p-1 rounded border border-slate-300 bg-white disabled:opacity-40 hover:bg-slate-50"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="font-semibold text-slate-800">
                Page {currentPage} of {resultsData.total_pages}
              </span>
              <button
                onClick={() => setCurrentPage((p) => Math.min(p + 1, resultsData.total_pages))}
                disabled={currentPage === resultsData.total_pages}
                className="p-1 rounded border border-slate-300 bg-white disabled:opacity-40 hover:bg-slate-50"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Slide-over Evidence & Review Drawer */}
      <EvidenceDrawer
        runId={runId}
        candidate={selectedCandidate}
        onClose={() => setSelectedCandidate(null)}
        onReviewUpdated={loadResults}
      />
    </div>
  );
};
