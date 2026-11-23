import React, { useState, useEffect } from 'react';
import { Navbar, NavPage } from './components/Navbar';
import { DashboardUpload } from './pages/DashboardUpload';
import { MatchingResults } from './pages/MatchingResults';
import { ReportsExports } from './pages/ReportsExports';
import { getDatabaseStats } from './api';

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<NavPage>('dashboard');
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [totalEntities, setTotalEntities] = useState<number>(10000);

  useEffect(() => {
    getDatabaseStats()
      .then((data) => setTotalEntities(data.total_entities))
      .catch((err) => console.warn('Could not fetch stats on init:', err));
  }, []);

  const handleComparisonStarted = (runId: string) => {
    setActiveRunId(runId);
    setCurrentPage('results');
  };

  const handleNavigateToExport = (runId: string) => {
    setActiveRunId(runId);
    setCurrentPage('reports');
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar
        currentPage={currentPage}
        onPageChange={setCurrentPage}
        totalEntities={totalEntities}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentPage === 'dashboard' && (
          <DashboardUpload onComparisonStarted={handleComparisonStarted} />
        )}
        {currentPage === 'results' && (
          <MatchingResults
            runId={activeRunId}
            onNavigateToExport={handleNavigateToExport}
          />
        )}
        {currentPage === 'reports' && (
          <ReportsExports runId={activeRunId} />
        )}
      </main>

      <footer className="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-400">
        <p>Company Duplicate Detection System &copy; 2026 &bull; Groups 1–8 Consolidated Specification &bull; Local Demo Mode</p>
      </footer>
    </div>
  );
};

export default App;
