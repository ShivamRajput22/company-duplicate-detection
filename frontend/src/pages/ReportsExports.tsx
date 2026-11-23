import React, { useState } from 'react';
import { FileDown, CheckCircle, ShieldAlert, Table, FileSpreadsheet, Layers, ExternalLink } from 'lucide-react';
import { getExportUrl } from '../api';

interface ReportsExportsProps {
  runId: string | null;
}

export const ReportsExports: React.FC<ReportsExportsProps> = ({ runId }) => {
  const [selectedType, setSelectedType] = useState<'uploaded_summary' | 'master_summary' | 'candidate_details'>('candidate_details');
  const [downloading, setDownloading] = useState(false);

  if (!runId) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-12 text-center max-w-lg mx-auto mt-10">
        <Layers className="w-12 h-12 text-slate-300 mx-auto mb-3" />
        <h3 className="text-base font-bold text-slate-800">No Matching Run Selected</h3>
        <p className="text-xs text-slate-500 mt-1 mb-4">
          Please upload and execute a comparison run before exporting reports.
        </p>
      </div>
    );
  }

  const handleDownload = () => {
    setDownloading(true);
    const url = getExportUrl(runId, selectedType);
    window.open(url, '_blank');
    setTimeout(() => setDownloading(false), 1500);
  };

  const EXPORT_VIEWS = [
    {
      id: 'uploaded_summary',
      title: 'Uploaded Company Summary',
      grain: '1 row per incoming uploaded company (run_id, upload_record_id)',
      badge: 'Upload-Centric View',
      description: 'Provides full accounting of every uploaded record in the batch, including records with 0 matches. Contains original name & identifiers, validation status, candidate match count, and strongest match outcome.',
      fields: ['Upload Record ID', 'CSV Row Number', 'Company Name', 'Legal Name', 'Domain', 'LinkedIn', 'Validation Status', 'Candidate Matches Count', 'Strongest Status']
    },
    {
      id: 'master_summary',
      title: 'Master Company Summary (Potential Duplicates)',
      grain: '1 row per matched master Entity ID (run_id, entity_id)',
      badge: 'Client-Compliant Non-Repeating',
      description: 'Guarantees zero repeat master companies. Displays authoritative entities.entity_id with adjacent authoritative entities.legal_name (AC-03, AC-04, AC-05). Never substitutes IMPORT_BATCH.',
      fields: ['Matched Entity ID', 'Matched Legal Name', 'Matched Company Name', 'Website Domain', 'LinkedIn URL', 'Matched Uploaded Count', 'Strongest Match Status']
    },
    {
      id: 'candidate_details',
      title: 'Detailed Candidate Pairs (Full Audit)',
      grain: '1 row per distinct candidate pair (run_id, upload_record_id, entity_id)',
      badge: 'Comprehensive Audit Grain',
      description: 'Contains every distinct candidate pair identified. Displays exact domain/LinkedIn states, actual Name Similarity (%) when evaluated (or N/A for exact matches), rule rationale, and latest human review decision.',
      fields: ['Upload Record ID', 'Uploaded Company', 'Uploaded Legal Name', 'Matched Entity ID', 'Matched Legal Name', 'Match Methods', 'Name Similarity (%)', 'Match Status', 'Rationale', 'Latest Review Decision']
    }
  ];

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Title */}
      <div className="pb-2 border-b border-slate-200">
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Reports & Exports</h1>
        <p className="text-sm text-slate-500">
          Export verified matching results and review decisions. One backend export engine with three distinct view grains.
        </p>
        <div className="mt-2 inline-flex items-center space-x-2 bg-slate-100 px-3 py-1 rounded text-xs">
          <span className="text-slate-500">Active Run:</span>
          <span className="font-mono font-bold text-slate-800">{runId}</span>
        </div>
      </div>

      {/* Export Format Selection Cards */}
      <div className="space-y-4">
        {EXPORT_VIEWS.map((view) => {
          const isSelected = selectedType === view.id;
          return (
            <div
              key={view.id}
              onClick={() => setSelectedType(view.id as any)}
              className={`p-5 rounded-lg border-2 cursor-pointer transition-all ${
                isSelected
                  ? 'border-teal-500 bg-teal-50/20 shadow-md'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-base font-bold text-slate-900">{view.title}</span>
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                      {view.badge}
                    </span>
                  </div>
                  <p className="text-xs font-mono text-teal-700 font-medium">Grain: {view.grain}</p>
                  <p className="text-xs text-slate-600 mt-2 leading-relaxed">{view.description}</p>
                </div>

                <div className="w-5 h-5 rounded-full border flex items-center justify-center mt-1 flex-shrink-0">
                  {isSelected && <div className="w-3 h-3 rounded-full bg-teal-600" />}
                </div>
              </div>

              {/* Field Previews */}
              <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap gap-1.5">
                {view.fields.map((f) => (
                  <span key={f} className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
                    {f}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Security & Integrity Note */}
      <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs text-slate-600 space-y-2">
        <div className="flex items-center space-x-2 font-bold text-slate-800">
          <ShieldAlert className="w-4 h-4 text-teal-600" />
          <span>Security & Formula Injection Defenses</span>
        </div>
        <p>
          All exported text cells are sanitized to prevent spreadsheet formula injection. Values starting with <code className="bg-white px-1 py-0.5 border rounded">=, +, -, @, \t, \r</code> are prepended with an apostrophe (<code className="bg-white px-1 py-0.5 border rounded">'</code>). Encoded in UTF-8 with BOM for Excel compatibility.
        </p>
      </div>

      {/* Download Action Button */}
      <div className="pt-2">
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="w-full bg-slate-900 hover:bg-slate-800 text-white font-bold text-sm py-3.5 rounded-lg shadow-md transition-colors flex items-center justify-center space-x-2"
        >
          <FileDown className="w-4 h-4 text-teal-400" />
          <span>
            {downloading ? 'Preparing CSV...' : `Download CSV (${selectedType.replace('_', ' ').toUpperCase()})`}
          </span>
        </button>
      </div>
    </div>
  );
};
