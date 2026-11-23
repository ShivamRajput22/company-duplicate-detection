import React from 'react';
import { Layers, Upload, ListFilter, FileDown, Database } from 'lucide-react';

export type NavPage = 'dashboard' | 'results' | 'reports';

interface NavbarProps {
  currentPage: NavPage;
  onPageChange: (page: NavPage) => void;
  totalEntities?: number;
}

export const Navbar: React.FC<NavbarProps> = ({ currentPage, onPageChange, totalEntities }) => {
  return (
    <header className="bg-slate-900 text-white shadow-md sticky top-0 z-40 border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => onPageChange('dashboard')}>
            <div className="w-9 h-9 rounded-lg bg-teal-500/20 border border-teal-500/40 flex items-center justify-center text-teal-400">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight text-white">EntityMatch AI</span>
                <span className="text-[10px] bg-teal-950 text-teal-400 border border-teal-800 px-1.5 py-0.5 rounded font-mono font-medium">
                  HYBRID POC
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">Company Duplicate Detection System</p>
            </div>
          </div>

          {/* Navigation Tabs - Exactly 3 Pages */}
          <nav className="flex space-x-1 sm:space-x-2">
            <button
              onClick={() => onPageChange('dashboard')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentPage === 'dashboard'
                  ? 'bg-slate-800 text-teal-400 border-b-2 border-teal-400'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <Upload className="w-4 h-4" />
              <span>Dashboard & Upload</span>
            </button>

            <button
              onClick={() => onPageChange('results')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentPage === 'results'
                  ? 'bg-slate-800 text-teal-400 border-b-2 border-teal-400'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <ListFilter className="w-4 h-4" />
              <span>Matching Results & Reviews</span>
            </button>

            <button
              onClick={() => onPageChange('reports')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentPage === 'reports'
                  ? 'bg-slate-800 text-teal-400 border-b-2 border-teal-400'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <FileDown className="w-4 h-4" />
              <span>Reports & Exports</span>
            </button>
          </nav>

          {/* Master DB Status Badge */}
          <div className="hidden lg:flex items-center space-x-2 bg-slate-800/80 px-3 py-1.5 rounded-full border border-slate-700 text-xs">
            <Database className="w-3.5 h-3.5 text-teal-400" />
            <span className="text-slate-300">Master DB:</span>
            <span className="font-semibold text-teal-400">
              {totalEntities !== undefined ? totalEntities.toLocaleString() : '10,000'} rows
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
