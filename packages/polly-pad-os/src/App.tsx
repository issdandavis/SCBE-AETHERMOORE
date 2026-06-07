import { useState, useCallback } from 'react';
import { OSProvider } from './os/OSStore';
import Desktop from './os/Desktop';
import Taskbar from './os/Taskbar';
import StartMenu from './os/StartMenu';
import AppLoader from './os/AppLoader';
import BootScreen from './os/BootScreen';
import './App.css';

function AppContent() {
  return (
    <div className="w-screen h-screen overflow-hidden bg-[#060e18] relative select-none">
      <Desktop />
      <AppLoader />
      <StartMenu />
      <Taskbar />
    </div>
  );
}

function App() {
  const [booted, setBooted] = useState(false);

  const handleBootComplete = useCallback(() => {
    setBooted(true);
  }, []);

  return (
    <OSProvider>
      {!booted && <BootScreen onComplete={handleBootComplete} />}
      <AppContent />
    </OSProvider>
  );
}

export default App;
