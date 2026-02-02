import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import Layout from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import CreateProposal from '@/pages/CreateProposal';
import ProposalDetail from '@/pages/ProposalDetail';
import ClauseLibrary from '@/pages/ClauseLibrary';
import Analytics from '@/pages/Analytics';
import Settings from '@/pages/Settings';
import '@/App.css';

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="create" element={<CreateProposal />} />
            <Route path="proposals/:id" element={<ProposalDetail />} />
            <Route path="clauses" element={<ClauseLibrary />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </div>
  );
}

export default App;