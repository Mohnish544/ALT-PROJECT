// MedLens — root application shell
// Sets up React Router with sidebar + main layout, and mounts all pages.

import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import { Sidebar }        from './components/layout/Sidebar';
import { ToastContainer } from './components/ui/Toast';
import { useStore }       from './store';
import { statusApi }      from './services/api';

// Pages
import Home         from './pages/Home';
import Documents    from './pages/Documents';
import Chat         from './pages/Chat';
import Evaluation   from './pages/Evaluation';
import Architecture from './pages/Architecture';
import Settings     from './pages/Settings';

function AppShell() {
  const { setSystemStatus } = useStore();

  // Poll system status on mount so the sidebar status dot is accurate
  useEffect(() => {
    statusApi.get().then(setSystemStatus).catch(() => {});
    const id = setInterval(() => {
      statusApi.get().then(setSystemStatus).catch(() => {});
    }, 30_000);
    return () => clearInterval(id);
  }, [setSystemStatus]);

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-area">
        <Routes>
          <Route path="/"             element={<Home />} />
          <Route path="/documents"    element={<Documents />} />
          <Route path="/chat"         element={<Chat />} />
          <Route path="/evaluation"   element={<Evaluation />} />
          <Route path="/architecture" element={<Architecture />} />
          <Route path="/settings"     element={<Settings />} />
          {/* Catch-all → home */}
          <Route path="*"             element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <ToastContainer />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}
