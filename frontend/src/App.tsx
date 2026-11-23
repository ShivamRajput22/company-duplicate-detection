import React from 'react';
import { Navbar } from './components/Navbar';
import { DashboardUpload } from './pages/DashboardUpload';

export const App: React.FC = () => (
  <div className="relay-page">
    <Navbar />
    <main><DashboardUpload /></main>
  </div>
);
export default App;
