import React from 'react';

interface ReportsExportsProps {
  runId: string | null;
  busy: boolean;
  onDownload: (type: string) => void;
}

export const ReportsExports: React.FC<ReportsExportsProps> = ({ runId, busy, onDownload }) => (
  <section className="details-section">
    <details><summary>CSV Downloads</summary>
      <p className="table-note">Download the complete backend reports, including original classifications and recorded review decisions. Section downloads above filter these same reports.</p>
      <div className="export-actions">
        <button className="secondary-button" disabled={!runId || busy} onClick={() => onDownload('uploaded_summary')}>Uploaded Company Summary</button>
        <button className="secondary-button" disabled={!runId || busy} onClick={() => onDownload('master_summary')}>Master Company Summary</button>
        <button className="secondary-button" disabled={!runId || busy} onClick={() => onDownload('candidate_details')}>Candidate Details & Decisions</button>
      </div>
      <p className="table-note">Master summaries contain one row per Entity ID, with the authoritative Legal Name beside it. CSVs retain the backend’s spreadsheet formula protection and UTF-8 encoding.</p>
    </details>
  </section>
);
