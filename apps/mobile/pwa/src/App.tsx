import { useEffect, useState } from 'react';
import { AgentList } from './components/AgentList';
import { BusFeed } from './components/BusFeed';
import { TriggerPanel } from './components/TriggerPanel';
import { LoginGate } from './components/LoginGate';
import { useAuth } from './state/auth';

type Tab = 'agents' | 'bus' | 'trigger';

export function App() {
  const { token, backendUrl, signOut } = useAuth();
  const [tab, setTab] = useState<Tab>('agents');

  useEffect(() => {
    document.documentElement.style.setProperty('--safe-top', 'env(safe-area-inset-top)');
  }, []);

  if (!token || !backendUrl) {
    return <LoginGate />;
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <img src="/icon-512.png" alt="" width={28} height={28} />
          <span>Aethermoor Bus</span>
        </div>
        <button className="link" onClick={signOut} aria-label="Sign out">
          sign out
        </button>
      </header>
      <main className="content">
        {tab === 'agents' && <AgentList />}
        {tab === 'bus' && <BusFeed />}
        {tab === 'trigger' && <TriggerPanel />}
      </main>
      <nav className="tabs" role="tablist">
        <button
          role="tab"
          aria-selected={tab === 'agents'}
          className={tab === 'agents' ? 'active' : ''}
          onClick={() => setTab('agents')}
        >
          Agents
        </button>
        <button
          role="tab"
          aria-selected={tab === 'bus'}
          className={tab === 'bus' ? 'active' : ''}
          onClick={() => setTab('bus')}
        >
          Bus
        </button>
        <button
          role="tab"
          aria-selected={tab === 'trigger'}
          className={tab === 'trigger' ? 'active' : ''}
          onClick={() => setTab('trigger')}
        >
          Trigger
        </button>
      </nav>
    </div>
  );
}
