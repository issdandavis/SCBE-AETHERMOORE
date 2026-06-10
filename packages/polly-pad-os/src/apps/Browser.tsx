import React, { useState, useRef, useEffect } from 'react';
import { useOS } from '@/os/OSStore';
import {
  ArrowLeft,
  ArrowRight,
  RotateCcw,
  Home,
  Globe,
  Lock,
  Bookmark,
  Star,
  ExternalLink,
} from 'lucide-react';

const START_PAGE = `
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:linear-gradient(135deg,#0c1929,#132744);min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#93bbfc;padding:40px}
.search-box{width:100%;max-width:580px;margin-bottom:40px}
.search-box input{width:100%;padding:14px 24px;border-radius:24px;border:1px solid rgba(59,130,246,0.2);background:rgba(30,58,95,0.4);color:#bfdbfe;font-size:15px;outline:none}
.search-box input::placeholder{color:#60a5fa50}
h1{font-size:42px;margin-bottom:8px;background:linear-gradient(135deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
p{color:#60a5fa80;margin-bottom:32px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;width:100%;max-width:580px}
.tile{display:flex;flex-direction:column;align-items:center;gap:8px;padding:20px;background:rgba(30,58,95,0.3);border-radius:16px;border:1px solid rgba(59,130,246,0.08);text-decoration:none;color:#93bbfc;transition:all 0.2s}
.tile:hover{background:rgba(59,130,246,0.12);transform:translateY(-2px)}
.tile-icon{font-size:28px}
.tile span{font-size:12px;color:#60a5fab0}
.links{display:flex;gap:24px;margin-top:32px;flex-wrap:wrap;justify-content:center}
.links a{color:#60a5fa60;text-decoration:none;font-size:13px;transition:color 0.2s}
.links a:hover{color:#60a5fab0}
</style>
</head>
<body>
<h1>SCBE Internet</h1>
<p>Routes URLs and searches through the local action bridge</p>
<div class="search-box">
  <input type="text" placeholder="Search or type a URL..." id="search" />
</div>
<div class="grid">
  <a href="https://google.com" class="tile"><div class="tile-icon">🔍</div><span>Google</span></a>
  <a href="https://github.com" class="tile"><div class="tile-icon">🐙</div><span>GitHub</span></a>
  <a href="https://wikipedia.org" class="tile"><div class="tile-icon">📚</div><span>Wikipedia</span></a>
  <a href="https://reddit.com" class="tile"><div class="tile-icon">🤖</div><span>Reddit</span></a>
  <a href="https://youtube.com" class="tile"><div class="tile-icon">▶️</div><span>YouTube</span></a>
  <a href="https://news.ycombinator.com" class="tile"><div class="tile-icon">🟠</div><span>HackerNews</span></a>
  <a href="https://stackoverflow.com" class="tile"><div class="tile-icon">🥞</div><span>StackOverflow</span></a>
  <a href="https://weather.gov" class="tile"><div class="tile-icon">🌤️</div><span>Weather</span></a>
</div>
<div class="links">
  <a href="https://openai.com">OpenAI</a>
  <a href="https://anthropic.com">Anthropic</a>
  <a href="https://vercel.com">Vercel</a>
  <a href="https://developer.mozilla.org">MDN</a>
  <a href="https://npmjs.com">npm</a>
  <a href="https://news.google.com">Google News</a>
</div>
<script>
document.getElementById('search').addEventListener('keydown',function(e){
  if(e.key==='Enter'){
    var v=this.value.trim();
    if(v){
      if(v.match(/^https?:\/\//)) window.parent.location=v;
      else window.location='https://www.google.com/search?q='+encodeURIComponent(v);
    }
  }
});
</script>
</body>
</html>
`;

function bridgeUrl() {
  return import.meta.env.VITE_SCBE_ACTION_BRIDGE || 'http://127.0.0.1:3678';
}

export default function Browser({ windowId }: { windowId: string }) {
  const { setWindowTitle } = useOS();
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [url, setUrl] = useState('');
  const [currentUrl, setCurrentUrl] = useState('');
  const [history, setHistory] = useState<string[]>(['about:start']);
  const [historyIdx, setHistoryIdx] = useState(0);
  const [isSecure, setIsSecure] = useState(false);
  const [bookmarks, setBookmarks] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('browser_bookmarks') || '[]');
    } catch {
      return [];
    }
  });
  const [showBookmarks, setShowBookmarks] = useState(false);
  const [lastRoutedUrl, setLastRoutedUrl] = useState('');
  const [browserResult, setBrowserResult] = useState<any>(null);
  const [loadingRealBrowser, setLoadingRealBrowser] = useState(false);
  const screenshotSrc =
    browserResult?.screenshot_url && browserResult.success
      ? `${bridgeUrl()}${browserResult.screenshot_url}`
      : '';

  const openSystemBrowser = async (target: string) => {
    const href = target.trim();
    if (!href || href === 'about:start') return;
    try {
      const response = await fetch(`${bridgeUrl()}/internet/open`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: href }),
      });
      const payload = await response.json();
      if (payload?.url) setLastRoutedUrl(payload.url);
    } catch {
      setLastRoutedUrl('bridge offline');
    }
  };

  const openHeadlessBrowser = async (target: string) => {
    let href = target.trim();
    if (!href) return;
    if (href === 'about:start') {
      setCurrentUrl('about:start');
      setIsSecure(false);
      return;
    }
    if (!href.match(/^https?:\/\//)) {
      if (href.includes('.') && !href.includes(' ')) {
        href = 'https://' + href;
      } else {
        href = 'https://www.google.com/search?q=' + encodeURIComponent(href);
      }
    }
    setCurrentUrl(href);
    setIsSecure(href.startsWith('https://'));
    setWindowTitle(windowId, new URL(href).hostname);
    const newHistory = [...history.slice(0, historyIdx + 1), href];
    setHistory(newHistory);
    setHistoryIdx(newHistory.length - 1);
    setLoadingRealBrowser(true);
    try {
      const response = await fetch(`${bridgeUrl()}/browser/open`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: href }),
      });
      const payload = await response.json();
      setBrowserResult(payload);
      if (payload?.title) setWindowTitle(windowId, payload.title);
      if (payload?.final_url) {
        setCurrentUrl(payload.final_url);
        setIsSecure(payload.final_url.startsWith('https://'));
      }
    } catch {
      setBrowserResult({ success: false, error: 'bridge offline' });
    } finally {
      setLoadingRealBrowser(false);
    }
  };

  const navigate = (target: string) => {
    void openHeadlessBrowser(target);
  };

  const goBack = () => {
    if (historyIdx > 0) {
      setHistoryIdx(historyIdx - 1);
      setCurrentUrl(history[historyIdx - 1]);
    }
  };

  const goForward = () => {
    if (historyIdx < history.length - 1) {
      setHistoryIdx(historyIdx + 1);
      setCurrentUrl(history[historyIdx + 1]);
    }
  };

  const toggleBookmark = () => {
    if (!currentUrl || currentUrl === 'about:start') return;
    const newBM = bookmarks.includes(currentUrl)
      ? bookmarks.filter((b) => b !== currentUrl)
      : [...bookmarks, currentUrl];
    setBookmarks(newBM);
    localStorage.setItem('browser_bookmarks', JSON.stringify(newBM));
  };

  useEffect(() => {
    setWindowTitle(windowId, 'Browser');
  }, [windowId, setWindowTitle]);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926]">
      <div className="flex items-center gap-1.5 px-2 py-1.5 border-b border-blue-500/10 bg-[#111d2e]">
        <button
          onClick={goBack}
          disabled={historyIdx <= 0}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50 disabled:opacity-20 transition-colors"
        >
          <ArrowLeft size={14} />
        </button>
        <button
          onClick={goForward}
          disabled={historyIdx >= history.length - 1}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50 disabled:opacity-20 transition-colors"
        >
          <ArrowRight size={14} />
        </button>
        <button
          onClick={() => navigate(currentUrl)}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50 transition-colors"
        >
          <RotateCcw size={14} />
        </button>
        <button
          onClick={() => {
            setCurrentUrl('about:start');
            setWindowTitle(windowId, 'Browser');
          }}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/50 transition-colors"
        >
          <Home size={14} />
        </button>
        <div className="flex-1 flex items-center bg-[#0d1926] rounded-lg px-2.5 py-1 border border-blue-500/10">
          {isSecure ? (
            <Lock size={11} className="text-green-400/50 mr-2" />
          ) : (
            <Globe size={11} className="text-blue-400/30 mr-2" />
          )}
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                navigate(url);
                setUrl('');
              }
            }}
            placeholder={currentUrl === 'about:start' ? 'Search or enter URL' : currentUrl}
            className="flex-1 bg-transparent text-xs text-blue-100/80 outline-none"
          />
        </div>
        <button
          onClick={toggleBookmark}
          className={`p-1.5 rounded transition-colors ${bookmarks.includes(currentUrl) ? 'text-yellow-400' : 'text-blue-300/30 hover:text-blue-200'}`}
        >
          <Star size={14} />
        </button>
        <button
          onClick={() => openSystemBrowser(currentUrl || url)}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/40 transition-colors"
          title="Open through the SCBE bridge"
        >
          <ExternalLink size={14} />
        </button>
        <button
          onClick={() => setShowBookmarks(!showBookmarks)}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/40 transition-colors relative"
        >
          <Bookmark size={14} />
          {bookmarks.length > 0 && (
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-blue-500 rounded-full" />
          )}
          {showBookmarks && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setShowBookmarks(false)} />
              <div className="absolute right-0 top-full mt-1 bg-[#162032] border border-blue-500/20 rounded-xl shadow-2xl py-1 z-50 min-w-[200px] max-h-[200px] overflow-y-auto">
                {bookmarks.length === 0 && (
                  <div className="px-3 py-2 text-xs text-blue-300/30">No bookmarks</div>
                )}
                {bookmarks.map((bm, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      navigate(bm);
                      setShowBookmarks(false);
                    }}
                    className="w-full text-left px-3 py-1.5 text-xs text-blue-200/60 hover:bg-blue-500/10 truncate"
                  >
                    {bm}
                  </button>
                ))}
              </div>
            </>
          )}
        </button>
      </div>
      {lastRoutedUrl && (
        <div className="border-b border-blue-500/10 bg-[#0d1926] px-3 py-1 text-[10px] text-blue-200/50">
          system browser: {lastRoutedUrl}
        </div>
      )}
      <div className="flex-1 overflow-hidden">
        {browserResult && currentUrl !== 'about:start' ? (
          <div className="h-full overflow-auto bg-[#08101b] p-4 text-blue-100/80">
            <div className="mb-3 rounded border border-blue-500/15 bg-blue-500/5 p-3">
              <div className="text-xs uppercase tracking-widest text-blue-300/40">
                Real browser result
              </div>
              <div className="mt-1 text-sm text-blue-100">
                {browserResult.title || '(no title)'}
              </div>
              <div className="mt-1 break-all text-xs text-blue-200/50">
                {browserResult.final_url || browserResult.requested_url || currentUrl}
              </div>
              <div className="mt-2 text-xs text-blue-200/50">
                status: {browserResult.status_code ?? 'unknown'} ·{' '}
                {browserResult.success ? 'captured' : browserResult.error || 'failed'}
              </div>
            </div>
            {loadingRealBrowser && (
              <div className="text-xs text-blue-300/60">Loading real browser...</div>
            )}
            {browserResult.out_path && (
              <>
                {screenshotSrc && (
                  <div className="overflow-hidden rounded border border-blue-500/20 bg-black shadow-2xl shadow-blue-950/30">
                    <img
                      src={screenshotSrc}
                      alt={`Browser capture of ${browserResult.final_url || browserResult.requested_url}`}
                      className="block w-full"
                    />
                  </div>
                )}
                <div className="mt-3 rounded border border-blue-500/15 bg-black/20 p-3 font-mono text-xs text-blue-200/60">
                  screenshot: {browserResult.out_path}
                </div>
              </>
            )}
            {!browserResult.success && (
              <div className="rounded border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-200">
                {browserResult.error || 'Browser capture failed'}
              </div>
            )}
          </div>
        ) : currentUrl === 'about:start' || !currentUrl ? (
          <iframe
            ref={iframeRef}
            srcDoc={START_PAGE}
            className="w-full h-full border-none"
            sandbox="allow-scripts allow-same-origin allow-popups"
            title="browser"
          />
        ) : (
          <iframe
            ref={iframeRef}
            src={currentUrl}
            className="w-full h-full border-none"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
            title="browser"
          />
        )}
      </div>
    </div>
  );
}
