import React, { useState, useEffect } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, Database, Play, RefreshCw, Sliders } from 'lucide-react';
import { uploadCSV, runComparison, getDatabaseStats } from '../api';
import { ImportResponse, DatabaseStats } from '../types';

interface DashboardUploadProps {
  onComparisonStarted: (runId: string) => void;
}

const SAMPLE_CSV = `company_name,legal_name,web_domain,linkedin_url
Cobalt Capital,Cobalt Capital GmbH,cobalt-capital.example,https://www.linkedin.com/company/cobalt-capital
Trimark Property Group,Trimark Property Group LLC,trimark-property.example,https://www.linkedin.com/company/trimark-property
Trimark Petroleum Group,Trimark Petroleum Group LLC,trimark-petroleum.example,https://www.linkedin.com/company/trimark-petroleum
Apex Technologies,Apex Technologies Inc,,https://www.linkedin.com/company/apex-technologies
Beacon Solutions,Beacon Solutions Corp,beacon-solutions.example,
Genesis Holdings,Genesis Holdings LLC,,
Horizon Healthcare,Horizon Healthcare Systems LLC,horizon-health.example,https://www.linkedin.com/company/horizon-health
Westbridge Properties,Westbridge Properties LLC,westbridge-properties.example,https://www.linkedin.com/company/westbridge-properties
Delta Innovations,Delta Innovations Ltd,,https://www.linkedin.com/company/delta-innovations
No Match Enterprises,Totally Unique Company Inc,totally-unique.example,https://www.linkedin.com/company/totally-unique
`;

export const DashboardUpload: React.FC<DashboardUploadProps> = ({ onComparisonStarted }) => {
  const [stats, setStats] = useState<DatabaseStats | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<ImportResponse | null>(null);
  const [fuzzyThreshold, setFuzzyThreshold] = useState<number>(80);
  const [uploading, setUploading] = useState(false);
  const [comparing, setComparing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = () => {
    getDatabaseStats()
      .then(setStats)
      .catch((err) => console.error('Failed to load stats:', err));
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      await processUpload(selected);
    }
  };

  const handleLoadSample = async () => {
    const sampleBlob = new Blob([SAMPLE_CSV], { type: 'text/csv' });
    const sampleFile = new File([sampleBlob], 'sample_10_companies.csv', { type: 'text/csv' });
    setFile(sampleFile);
    await processUpload(sampleFile);
  };

  const processUpload = async (fileToUpload: File) => {
    setUploading(true);
    setErrorMsg(null);
    try {
      const res = await uploadCSV(fileToUpload);
      setUploadResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'CSV upload failed');
      setUploadResult(null);
    } finally {
      setUploading(false);
    }
  };

  const handleStartComparison = async () => {
    if (!uploadResult) return;
    setComparing(true);
    setErrorMsg(null);
    try {
      await runComparison(uploadResult.run_id, fuzzyThreshold);
      onComparisonStarted(uploadResult.run_id);
    } catch (err: any) {
      setErrorMsg(err.message || 'Comparison execution failed');
      setComparing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Title & Context */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Dashboard & Ingestion</h1>
          <p className="text-sm text-slate-500">
            Upload incoming company records to execute normalized identifier and fuzzy legal entity matching against the master database.
          </p>
        </div>
        <button
          onClick={loadStats}
          className="mt-2 sm:mt-0 flex items-center space-x-1.5 text-xs text-slate-600 bg-white border border-slate-300 px-3 py-1.5 rounded hover:bg-slate-50 shadow-sm"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh DB Stats</span>
        </button>
      </div>

      {errorMsg && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-sm flex items-start justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-rose-500 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="font-bold text-rose-700">×</button>
        </div>
      )}

      {/* Database Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase">Master Entities</span>
            <Database className="w-4 h-4 text-teal-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {stats ? stats.total_entities.toLocaleString() : '10,000'}
          </p>
          <p className="text-xs text-slate-400 mt-1">Authoritative SQLite Master</p>
        </div>

        <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase">With Registered Domain</span>
            <CheckCircle2 className="w-4 h-4 text-sky-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {stats ? stats.entities_with_domain.toLocaleString() : '—'}
          </p>
          <p className="text-xs text-slate-400 mt-1">PSL-normalized registered domains</p>
        </div>

        <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase">With LinkedIn</span>
            <CheckCircle2 className="w-4 h-4 text-indigo-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {stats ? stats.entities_with_linkedin.toLocaleString() : '—'}
          </p>
          <p className="text-xs text-slate-400 mt-1">Canonical company pages</p>
        </div>

        <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase">Fuzzy Fallback Eligible</span>
            <Sliders className="w-4 h-4 text-amber-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {stats ? stats.entities_with_both_blank.toLocaleString() : '—'}
          </p>
          <p className="text-xs text-slate-400 mt-1">Master records with both IDs blank</p>
        </div>
      </div>

      {/* Ingestion & Config Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Dropzone */}
        <div className="lg:col-span-2 bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <Upload className="w-5 h-5 text-teal-600" />
            <span>Upload Company CSV</span>
          </h2>

          <div className="border-2 border-dashed border-slate-300 rounded-lg p-6 text-center hover:border-teal-500 transition-colors bg-slate-50/50">
            <FileText className="w-10 h-10 text-slate-400 mx-auto mb-3" />
            <p className="text-sm font-medium text-slate-700">Drag and drop your company CSV file here</p>
            <p className="text-xs text-slate-400 mt-1">Supported headers: company_name, legal_name, web_domain, linkedin_url (Max 5MB)</p>

            <div className="mt-4 flex items-center justify-center space-x-3">
              <label className="cursor-pointer bg-slate-900 text-white hover:bg-slate-800 text-xs font-semibold px-4 py-2 rounded-md transition-colors shadow-sm">
                Browse Files
                <input
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </label>

              <button
                type="button"
                onClick={handleLoadSample}
                className="bg-white text-slate-700 border border-slate-300 hover:bg-slate-100 text-xs font-semibold px-4 py-2 rounded-md transition-colors shadow-sm"
              >
                Load Sample 10-Row CSV
              </button>
            </div>
          </div>

          {file && (
            <div className="flex items-center justify-between text-xs bg-slate-50 p-3 rounded-md border border-slate-200">
              <span className="font-medium text-slate-800">Selected file: <strong className="text-teal-700">{file.name}</strong> ({(file.size / 1024).toFixed(1)} KB)</span>
              {uploading && <span className="text-teal-600 font-semibold animate-pulse">Uploading & Validating...</span>}
            </div>
          )}
        </div>

        {/* Configuration Card */}
        <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-5">
          <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <Sliders className="w-5 h-5 text-teal-600" />
            <span>Matching Configuration</span>
          </h2>

          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-xs font-semibold text-slate-700">
                Fuzzy Legal Name Threshold
              </label>
              <span className="text-xs font-bold bg-teal-100 text-teal-900 px-2 py-0.5 rounded">
                {fuzzyThreshold}%
              </span>
            </div>
            <input
              type="range"
              min="50"
              max="100"
              step="1"
              value={fuzzyThreshold}
              onChange={(e) => setFuzzyThreshold(Number(e.target.value))}
              className="w-full accent-teal-600 cursor-pointer"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Default 80% (Group 1 mandate). Applied strictly when master identifiers are unavailable (DEC-01).
            </p>
          </div>

          <div className="p-3 bg-slate-50 rounded border border-slate-200 text-xs text-slate-600 space-y-1">
            <div className="font-semibold text-slate-800">Rule Priority:</div>
            <div>1. Match + Conflict → Needs Review</div>
            <div>2. Exact Domain / LinkedIn → High Confidence</div>
            <div>3. Blank IDs Fallback → Legal Name ≥ {fuzzyThreshold}%</div>
          </div>

          <button
            onClick={handleStartComparison}
            disabled={!uploadResult || comparing}
            className="w-full bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white font-bold text-sm py-3 rounded-lg shadow transition-colors flex items-center justify-center space-x-2"
          >
            <Play className="w-4 h-4 fill-current" />
            <span>{comparing ? 'Matching Running...' : 'Execute Duplicate Matching'}</span>
          </button>
        </div>
      </div>

      {/* Uploaded Records Preview Table */}
      {uploadResult && (
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="font-bold text-sm text-slate-900">Validated Ingestion Rows ({uploadResult.total_rows})</h3>
              <p className="text-xs text-slate-500">Run ID: <span className="font-mono font-semibold text-slate-800">{uploadResult.run_id}</span> | Accepted: {uploadResult.accepted_rows} | Rejected: {uploadResult.rejected_rows}</p>
            </div>
            <span className="text-xs bg-emerald-100 text-emerald-800 font-semibold px-2.5 py-1 rounded-full border border-emerald-300 mt-2 sm:mt-0">
              CSV Validation Passed
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-xs">
              <thead className="bg-slate-100 text-slate-700">
                <tr>
                  <th className="px-4 py-2.5 text-left font-semibold">Row</th>
                  <th className="px-4 py-2.5 text-left font-semibold">Company Name</th>
                  <th className="px-4 py-2.5 text-left font-semibold">Legal Name</th>
                  <th className="px-4 py-2.5 text-left font-semibold">Website Domain</th>
                  <th className="px-4 py-2.5 text-left font-semibold">LinkedIn Profile</th>
                  <th className="px-4 py-2.5 text-left font-semibold">Validation Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {uploadResult.rows.map((r) => (
                  <tr key={r.upload_record_id} className="hover:bg-slate-50">
                    <td className="px-4 py-2 font-mono text-slate-500">{r.csv_row_number}</td>
                    <td className="px-4 py-2 font-semibold text-slate-900">{r.company_name_original || '—'}</td>
                    <td className="px-4 py-2 text-slate-700">{r.legal_name_original || '—'}</td>
                    <td className="px-4 py-2 font-mono text-slate-600">{r.web_domain_original || '—'}</td>
                    <td className="px-4 py-2 font-mono text-slate-600 truncate max-w-xs">{r.linkedin_url_original || '—'}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                        r.record_validation_status === 'accepted'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-rose-100 text-rose-800'
                      }`}>
                        {r.record_validation_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
