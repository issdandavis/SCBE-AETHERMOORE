import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import './styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    const serviceWorkerUrl = new URL('sw.js', document.baseURI);
    const scope = new URL('./', document.baseURI).pathname;

    void navigator.serviceWorker
      .register(serviceWorkerUrl.toString(), { scope })
      .then((registration) => {
        const update = () => void registration.update();
        window.addEventListener('online', update);
        window.setInterval(update, 60 * 60 * 1000);
      })
      .catch((error: unknown) => {
        console.warn('Aethermoor service worker registration failed', error);
      });
  });
}
