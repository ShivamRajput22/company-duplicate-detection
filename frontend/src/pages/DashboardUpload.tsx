import React, { useEffect, useRef, useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
import { uploadCSV, runComparison, getAllResults, getRunStatus, getRunReviews, submitReview, downloadExport, saveDownload, getDatabaseStats } from '../api';
import { CandidateItem, CompareResponse, ImportResponse, PaginatedResultsResponse, ReviewHistoryItem } from '../types';
import { MatchingResults, getSections } from './MatchingResults';
import { ReportsExports } from './ReportsExports';
import { EvidenceDrawer } from '../components/EvidenceDrawer';

const HISTORY_KEY = 'relay-duplicate-run-ids';
function storedRunIds(): string[] {
  try {
    const ids = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
    return Array.isArray(ids) ? ids.filter(id => typeof id === 'string' && /^RUN-[A-Z0-9-]+$/i.test(id)).slice(0, 100) : [];
  } catch { return []; }
}
const errorText = (error: unknown) => error instanceof Error ? error.message : 'The request failed. Please retry.';

export const DashboardUpload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [upload, setUpload] = useState<ImportResponse | null>(null);
  const [run, setRun] = useState<CompareResponse | null>(null);
  const [data, setData] = useState<PaginatedResultsResponse | null>(null);
  const [busy, setBusy] = useState('');
  const busyRef = useRef(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [selectedCandidates, setSelectedCandidates] = useState(new Set<number>());
  const [selectedReady, setSelectedReady] = useState(new Set<string>());
  const [candidate, setCandidate] = useState<CandidateItem | null>(null);
  const [knownRuns, setKnownRuns] = useState(storedRunIds);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [runInput, setRunInput] = useState('');
  const [reviews, setReviews] = useState<ReviewHistoryItem[]>([]);
  const [masterCount, setMasterCount] = useState<number | null>(null);
  const [connected, setConnected] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const reviewRequest = useRef(0);
  const logsRef = useRef<HTMLElement>(null);
  const evidenceRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    getDatabaseStats().then(stats => { if (!cancelled) { setMasterCount(stats.total_entities); setConnected(true); } })
      .catch(() => { if (!cancelled) setConnected(false); });
    return () => { cancelled = true; };
  }, []);

  const rememberRun = (id: string) => {
    setKnownRuns(previous => {
      const ids = [id, ...previous.filter(item => item !== id)].slice(0, 100);
      try { localStorage.setItem(HISTORY_KEY, JSON.stringify(ids)); }
      catch { setHistoryError('Browser storage is unavailable. Copy the Run ID to reopen this run later.'); }
      return ids;
    });
  };
  const clearSelection = () => { setSelectedCandidates(new Set()); setSelectedReady(new Set()); };
  const begin = (label: string) => {
    if (busyRef.current) return false;
    busyRef.current = true; setBusy(label); setError(''); setNotice(''); return true;
  };
  const finish = () => { busyRef.current = false; setBusy(''); };
  const loadRun = async (id: string) => {
    const [status, result] = await Promise.all([getRunStatus(id), getAllResults(id)]);
    setRun(status); setData(result); setConnected(true);
    return { status, result };
  };
  const refreshReviews = async (id: string) => {
    const request = ++reviewRequest.current;
    try {
      const history = await getRunReviews(id);
      if (request === reviewRequest.current) { setReviews(history); setHistoryError(''); }
    } catch (err) {
      if (request === reviewRequest.current) { setReviews([]); setHistoryError(errorText(err)); }
    }
  };
  const openRun = async (id: string) => {
    id = id.trim();
    if (!/^RUN-[A-Z0-9-]+$/i.test(id)) { setError('Enter a valid Run ID, for example RUN-1234ABCD.'); return; }
    if (!begin('Loading saved run…')) return;
    reviewRequest.current++;
    try {
      await loadRun(id);
      setFile(null);
      const fileInput = document.querySelector<HTMLInputElement>('#csv-upload');
      if (fileInput) fileInput.value = '';
      setUpload(null); setCandidate(null); clearSelection(); rememberRun(id);
      await refreshReviews(id);
      setNotice('');
    } catch (err) { setError(errorText(err)); }
    finally { finish(); }
  };
  const validate = async () => {
    if (!file || !begin('Uploading CSV…')) return;
    reviewRequest.current++;
    setCandidate(null); clearSelection(); setUpload(null); setRun(null); setData(null); setReviews([]);
    try {
      const imported = await uploadCSV(file);
      setUpload(imported); rememberRun(imported.run_id);
      setBusy('Validating against the master database…');
      const status = await runComparison(imported.run_id, 80);
      setRun(status);
      await loadRun(imported.run_id);
      setNotice('');
    } catch (err) { setError(errorText(err)); }
    finally { finish(); }
  };
  const refresh = async () => {
    if (!run || !begin('Refreshing results…')) return;
    setCandidate(null);
    try { await loadRun(run.run_id); await refreshReviews(run.run_id); clearSelection(); }
    catch (err) { setError(errorText(err)); setData(null); }
    finally { finish(); }
  };
  const move = async (direction: 'add' | 'remove') => {
    if (!run || !data || !begin('Saving review decisions…')) return;
    setCandidate(null);
    let saved = 0;
    try {
      // Re-read before acting so decisions are based on the persisted snapshot.
      const fresh = await getAllResults(run.run_id);
      const sections = getSections(fresh);
      const targets = direction === 'add'
        ? fresh.candidates.filter(item => selectedCandidates.has(item.candidate_id) && item.latest_review_decision !== 'not_duplicate')
        : sections.ready.filter(row => selectedReady.has(row.upload_record_id))
          .flatMap(row => sections.byUpload.get(row.upload_record_id) || []);
      if (!targets.length) throw new Error('The selection has changed. Refresh and select the records again.');
      for (const item of targets) {
        await submitReview(run.run_id, item.candidate_id, direction === 'add' ? 'not_duplicate' : 'needs_review',
          'human_reviewer', direction === 'add' ? 'Cleared using Add to Ready to Import.' : 'Returned from Ready to Import for review.');
        saved++;
      }
      setNotice(`${saved} review decision${saved === 1 ? '' : 's'} saved. An upload is ready only when every blocking match is cleared.`);
    } catch (err) { setError(`${saved ? `${saved} decisions were saved before the error. ` : ''}${errorText(err)}`); }
    finally {
      clearSelection();
      try { await loadRun(run.run_id); await refreshReviews(run.run_id); }
      catch (err) { setData(null); setError(`Decisions may have been saved, but results could not be refreshed: ${errorText(err)}`); }
      finish();
    }
  };
  const download = async (type: string, section?: 'potential' | 'exact' | 'other' | 'ready') => {
    if (!run || !begin('Preparing CSV download…')) return;
    try {
      if (section) {
        const fresh = await getAllResults(run.run_id);
        setData(fresh); clearSelection();
        const groups = getSections(fresh);
        const ids = section === 'ready' ? new Set(groups.ready.map(row => row.upload_record_id))
          : new Set(groups[section].map(row => String(row.matched_entity_id)));
        if (!ids.size) throw new Error('There are no records in this section to download.');
        await downloadExport(run.run_id, type, { column: section === 'ready' ? 'Upload Record ID' : 'Matched Entity ID', ids, name: section });
      } else await downloadExport(run.run_id, type);
      setNotice('CSV download prepared successfully.');
    } catch (err) { setError(errorText(err)); }
    finally { finish(); }
  };
  const inspect = (item: CandidateItem) => {
    setCandidate(item);
    window.setTimeout(() => evidenceRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0);
  };
  const afterReview = async () => {
    if (!run) return;
    await loadRun(run.run_id); clearSelection(); await refreshReviews(run.run_id);
  };
  const completed = run?.run_status === 'completed' && !!data;
  const groups = getSections(completed ? data : null);
  const rows = data?.uploaded_rows || upload?.rows || [];
  const accepted = rows.filter(row => row.record_validation_status === 'accepted').length;
  const unique = completed ? groups.ready.filter(row => !(groups.byUpload.get(row.upload_record_id) || []).length).length : null;

  return (
    <>
      <div className="setup-grid">
        <section className="upload-panel" aria-label="CSV upload">
          <label htmlFor="entity-type" className="field-label">Select Entity Type</label>
          <div className="entity-controls"><select id="entity-type" defaultValue="company"><option value="company">Company</option></select>
            <button className="text-link" onClick={() => saveDownload(new Blob(['\uFEFFcompany_name,legal_name,web_domain,linkedin_url\r\n'],
              { type: 'text/csv;charset=utf-8' }), 'company_upload_template.csv')}>Download Template ↓</button></div>
          <label htmlFor="csv-upload" className="field-label upload-label">Upload CSV</label>
          <input id="csv-upload" type="file" accept=".csv,text/csv" disabled={!!busy}
            onChange={event => { setFile(event.target.files?.[0] || null); setError(''); setNotice(''); }} />
          <div className="validate-controls"><button className="primary-button validate-button" disabled={!file || !!busy} onClick={validate}>
            {busy.startsWith('Uploading') || busy.startsWith('Validating') ? 'Validating…' : 'Validate'}</button>
            <span className="input-hint">CSV · up to 5 MB · 80% legal-name threshold</span></div>
        </section>
        <section className="log-panel" aria-labelledby="log-heading">
          <h2 id="log-heading">Log</h2>
          <div className="log-box" aria-live="polite" aria-busy={!!busy}>
            <p className="log-status"><strong>Status: {busy || (completed ? 'Completed' : error ? 'Action failed' : run?.run_status || 'Awaiting CSV')}</strong>
              {completed && !busy && <CheckCircle2 size={17} className="success-icon" aria-label="Completed" />}</p>
            <p>Unique values found: {unique == null ? '—' : unique.toLocaleString()} <span className="muted">(no candidates)</span></p>
            <p>Potential duplications: {completed ? groups.potential.length : '—'}</p>
            <p>Exact duplications: {completed ? groups.exact.length : '—'}</p>
            <p>Inactive duplications: <span className="muted">Unavailable</span></p>
          </div>
          <h3>Instructions</h3>
          <ul className="instructions"><li>You can select an entry from <strong>Potential Duplications</strong> and move it to <strong>Ready to Import</strong> if it's not a duplicate.</li>
            <li>Hold down <strong>Ctrl + left-click</strong> to select multiple entries at once.</li></ul>
        </section>
      </div>
      {error && <div className="message error-message" role="alert">{error}</div>}
      {notice && <div className="message notice-message" role="status">{notice}</div>}
      <MatchingResults data={data} completed={completed} fuzzyThreshold={run?.fuzzy_threshold ?? 80} busy={!!busy} selectedCandidates={selectedCandidates} selectedReady={selectedReady}
        onSelectCandidates={setSelectedCandidates} onSelectReady={setSelectedReady} onInspect={inspect} onMove={move} onDownload={download} />
      <div ref={evidenceRef} className="evidence-anchor">
        {run && <EvidenceDrawer runId={run.run_id} candidate={candidate} disabled={!!busy} onClose={() => setCandidate(null)} onReviewUpdated={afterReview}
          onBusyChange={value => { busyRef.current = value; setBusy(value ? 'Saving review…' : ''); }} />}
      </div>
      {(run || upload) && <div className="run-strip"><span><strong>{data?.filename || upload?.filename}</strong> <span className="muted">· Run ID: {run?.run_id || upload?.run_id}</span></span>
        <div><button className="text-link" disabled={!!busy || !run} onClick={refresh}>Refresh results</button>
          <a href="#validation-logs" onClick={() => {
            const details = document.querySelector<HTMLDetailsElement>('#validation-logs details');
            if (details) details.open = true;
          }}>Validation Logs</a></div></div>}
      <section id="validation-logs" className="details-section" aria-labelledby="validation-heading">
        <details><summary id="validation-heading">Validation Logs {rows.length > 0 && <span className="count">{rows.length} rows</span>}</summary>
          {!rows.length ? <p className="table-note">Upload and validate a CSV to see validation results.</p> : <>
            <p className="table-note">{accepted} accepted · {rows.length - accepted} rejected{data ? ` · ${data.candidates.length} candidate pairs · ${data.reviewed_count} reviewed` : ''}{upload ? ` · ${upload.empty_rows_skipped} empty rows skipped · ${upload.invalid_identifiers} invalid identifiers` : ''}. Original uploaded values are preserved by the backend.</p>
            <div className="neutral-table table-frame"><table><thead><tr><th>CSV row</th><th>Company Name</th><th>Legal Name</th><th>Validation</th><th>Details</th></tr></thead>
              <tbody>{rows.map(row => <tr key={row.upload_record_id}><td>{row.csv_row_number}</td><td>{row.company_name_original || '—'}</td>
                <td>{row.legal_name_original || '—'}</td><td>{row.record_validation_status}</td><td>{row.validation_errors?.join('; ') || 'No validation errors'}</td></tr>)}</tbody></table></div></>}
        </details>
      </section>
      <ReportsExports runId={completed ? run.run_id : null} busy={!!busy} onDownload={type => download(type)} />
      <footer className="page-footer">
        <button className="text-link" aria-expanded={historyOpen} aria-controls="previous-logs" onClick={() => {
          setHistoryOpen(value => !value);
          if (!historyOpen && run) void refreshReviews(run.run_id);
          window.setTimeout(() => logsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 0);
        }}>View Previous Logs</button>
        <span>{connected ? `Connected · ${masterCount == null ? 'Backend' : `${masterCount.toLocaleString()} master companies`}` : 'Backend connection unavailable'}<span className="footer-divider">|</span>Local reviewer</span>
      </footer>
      {historyOpen && <section id="previous-logs" className="history-panel" ref={logsRef} aria-labelledby="history-heading">
        <h2 id="history-heading">Previous Logs</h2>
        <p className="table-note">This browser remembers Run IDs only; records and review history are fetched from the backend. The existing API cannot list all historical runs. Open a known Run ID to retrieve older results.</p>
        <form className="history-controls" onSubmit={event => { event.preventDefault(); void openRun(runInput); }}>
          <label htmlFor="run-id">Run ID</label><input id="run-id" value={runInput} onChange={event => setRunInput(event.target.value)} placeholder="RUN-1234ABCD" required disabled={!!busy} />
          <button className="secondary-button" type="submit" disabled={!!busy || !runInput.trim()}>Open saved run</button></form>
        <div className="saved-runs">{knownRuns.map(id => <button key={id} className={`saved-run ${id === run?.run_id ? 'active-run' : ''}`}
          disabled={!!busy} onClick={() => openRun(id)}>{id}</button>)}{!knownRuns.length && <p>No Run IDs have been saved in this browser.</p>}</div>
        {historyError && <p className="error-message" role="alert">{historyError}</p>}
        {run && <><h3>Review history · {run.run_id}</h3><div className="neutral-table table-frame"><table><thead><tr><th>Time</th><th>Candidate</th><th>Reviewer</th><th>Prior decision</th><th>Decision</th><th>Reason</th></tr></thead>
          <tbody>{reviews.map(review => <tr key={review.review_id}><td>{new Date(review.reviewed_at).toLocaleString()}</td><td>{review.candidate_id}</td><td>{review.reviewer}</td>
            <td>{review.prior_decision?.replace(/_/g, ' ') || '—'}</td><td>{review.new_decision.replace(/_/g, ' ')}</td><td>{review.reason || '—'}</td></tr>)}
            {!reviews.length && <tr><td colSpan={6} className="empty-cell">No reviews returned for this run.</td></tr>}</tbody></table></div></>}
      </section>}
    </>
  );
};
