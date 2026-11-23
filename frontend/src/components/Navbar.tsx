import React from 'react';

export const Navbar: React.FC = () => (
  <header className="page-header">
    <h1>Duplicate Records</h1>
    <div className="relay-brand" aria-label="Relay">
      <svg viewBox="0 0 40 40" width="38" height="38" aria-hidden="true">
        {[0, 60, 120, 180, 240, 300].map(angle => (
          <path key={angle} transform={`rotate(${angle} 20 20)`}
            d="M18 2C24 1 29 4 31 8L25 13C23 10 21 10 18 10Z" fill="currentColor" />
        ))}
      </svg>
      <span>RELAY</span>
    </div>
  </header>
);
