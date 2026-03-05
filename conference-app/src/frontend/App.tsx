import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import { AuthContext, useAuthProvider } from './hooks/useAuth';
import Landing from './pages/Landing';
import AuthPage from './pages/AuthPage';
import Dashboard from './pages/Dashboard';
import SubmitProject from './pages/SubmitProject';
import ProjectDetail from './pages/ProjectDetail';
import Conferences from './pages/Conferences';
import LiveRoom from './pages/LiveRoom';
import CaaSPricing from './pages/CaaSPricing';

export default function App() {
  const auth = useAuthProvider();

  return (
    <AuthContext.Provider value={auth}>
      <div className="app-layout">
        <header className="app-header">
          <Link to="/" className="logo">vibe::conference</Link>
          <nav>
            {auth.user ? (
              <>
                <Link to="/dashboard">Dashboard</Link>
                <Link to="/conferences">Demo Days</Link>
                <Link to="/pricing">CaaS</Link>
                {auth.user.role === 'coder' && <Link to="/submit">Submit Project</Link>}
                <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                  {auth.user.displayName} ({auth.user.role})
                </span>
                <button className="btn-secondary" onClick={auth.logout} style={{ padding: '6px 14px', fontSize: '0.8rem' }}>
                  Logout
                </button>
              </>
            ) : (
              <Link to="/auth">Sign In</Link>
            )}
          </nav>
        </header>

        <main className="app-main">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/auth" element={<AuthPage />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/submit" element={<SubmitProject />} />
            <Route path="/projects/:id" element={<ProjectDetail />} />
            <Route path="/conferences" element={<Conferences />} />
            <Route path="/live/:id" element={<LiveRoom />} />
            <Route path="/pricing" element={<CaaSPricing />} />
          </Routes>
        </main>
      </div>
    </AuthContext.Provider>
  );
}
