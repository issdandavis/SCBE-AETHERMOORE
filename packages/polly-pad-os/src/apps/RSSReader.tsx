import React, { useState, useEffect } from 'react';
import { Rss, ExternalLink, Clock, Loader2, Plus, Trash2, RefreshCw } from 'lucide-react';

interface FeedItem {
  title: string;
  link: string;
  pubDate?: string;
  contentSnippet?: string;
}
interface Feed {
  name: string;
  url: string;
  items: FeedItem[];
}

const DEFAULT_FEEDS: Feed[] = [
  { name: 'Hacker News', url: 'https://news.ycombinator.com/rss', items: [] },
  { name: 'Dev.to', url: 'https://dev.to/feed', items: [] },
  { name: 'CSS Tricks', url: 'https://css-tricks.com/feed/', items: [] },
];

const STORAGE_KEY = 'linuxos_rss_feeds';

export default function RSSReader() {
  const [feeds, setFeeds] = useState<Feed[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch {
      /* ignore */
    }
    return DEFAULT_FEEDS;
  });
  const [selectedFeed, setSelectedFeed] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [newFeedUrl, setNewFeedUrl] = useState('');
  const [showAdd, setShowAdd] = useState(false);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(feeds));
  }, [feeds]);

  const fetchFeed = async (url: string): Promise<FeedItem[]> => {
    const res = await fetch(
      `https://api.rss2json.com/v1/api.json?rss_url=${encodeURIComponent(url)}&count=20`
    );
    if (!res.ok) throw new Error('Failed to fetch');
    const data = await res.json();
    if (data.status !== 'ok') throw new Error(data.message || 'Invalid RSS feed');
    return (data.items || []).map((item: any) => ({
      title: item.title || 'Untitled',
      link: item.link || '',
      pubDate: item.pubDate,
      contentSnippet: item.description
        ? item.description.replace(/<[^>]*>/g, '').slice(0, 200)
        : '',
    }));
  };

  const loadFeed = async (feedUrl?: string, index?: number) => {
    setLoading(true);
    setError('');
    try {
      const url = feedUrl || feeds[selectedFeed]?.url;
      if (!url) return;
      const items = await fetchFeed(url);
      const targetIndex = index !== undefined ? index : selectedFeed;
      setFeeds((prev) => prev.map((f, i) => (i === targetIndex ? { ...f, items } : f)));
    } catch {
      setError('Failed to load feed. Try again later.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFeed();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addFeed = async () => {
    if (!newFeedUrl.trim()) return;
    setLoading(true);
    try {
      const items = await fetchFeed(newFeedUrl.trim());
      const newFeed: Feed = {
        name: new URL(newFeedUrl.trim()).hostname,
        url: newFeedUrl.trim(),
        items,
      };
      setFeeds((prev) => [...prev, newFeed]);
      setSelectedFeed(feeds.length);
      setNewFeedUrl('');
      setShowAdd(false);
    } catch {
      setError('Invalid RSS feed URL');
    } finally {
      setLoading(false);
    }
  };

  const removeFeed = (idx: number) => {
    if (feeds.length <= 1) return;
    setFeeds((prev) => prev.filter((_, i) => i !== idx));
    if (selectedFeed >= idx && selectedFeed > 0) setSelectedFeed(selectedFeed - 1);
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return '';
    const diff = Date.now() - d.getTime();
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return d.toLocaleDateString();
  };

  const currentFeed = feeds[selectedFeed];

  return (
    <div className="w-full h-full flex bg-[#0d1926] text-blue-100/80">
      <div className="w-44 border-r border-blue-500/10 flex flex-col">
        <div className="flex items-center justify-between px-3 py-2 border-b border-blue-500/10">
          <div className="flex items-center gap-2">
            <Rss size={14} className="text-orange-400" />
            <span className="text-xs text-blue-200 font-semibold">Feeds</span>
          </div>
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="p-1 rounded hover:bg-blue-500/20 text-blue-400 transition-colors"
          >
            <Plus size={12} />
          </button>
        </div>
        {showAdd && (
          <div className="p-2 border-b border-blue-500/10">
            <input
              value={newFeedUrl}
              onChange={(e) => setNewFeedUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addFeed()}
              placeholder="RSS feed URL..."
              className="w-full bg-[#162032] border border-blue-500/15 rounded-lg px-2 py-1 text-[10px] outline-none focus:border-blue-500/30 mb-1"
            />
            <button
              onClick={addFeed}
              className="w-full py-1 rounded bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 text-[10px] transition-colors"
            >
              Add Feed
            </button>
          </div>
        )}
        <div className="flex-1 overflow-y-auto">
          {feeds.map((f, i) => (
            <div key={f.url} className="group relative">
              <button
                onClick={() => setSelectedFeed(i)}
                className={`w-full text-left px-3 py-1.5 text-xs transition-colors ${selectedFeed === i ? 'bg-blue-500/15 text-blue-200' : 'text-blue-200/50 hover:bg-blue-500/10'}`}
              >
                {f.name}
                <div className="text-[9px] text-blue-400/20">{f.items.length} articles</div>
              </button>
              <button
                onClick={() => removeFeed(i)}
                className="absolute right-1 top-1/2 -translate-y-1/2 p-0.5 rounded opacity-0 group-hover:opacity-100 hover:bg-red-500/20 text-red-400 transition-all"
              >
                <Trash2 size={9} />
              </button>
            </div>
          ))}
        </div>
      </div>
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-blue-500/10">
          <div>
            <h2 className="text-sm text-blue-200 font-semibold">
              {currentFeed?.name || 'Select a feed'}
            </h2>
            <span className="text-[10px] text-blue-300/30">
              {currentFeed?.items.length || 0} articles
            </span>
          </div>
          <button
            onClick={() => loadFeed()}
            className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/40 hover:text-blue-300 transition-colors"
            title="Refresh"
          >
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
        {error && <div className="px-4 py-2 text-xs text-red-400/80 bg-red-500/5">{error}</div>}
        <div className="flex-1 overflow-y-auto">
          {currentFeed?.items.map((item, i) => (
            <div
              key={i}
              onClick={() => item.link && window.open(item.link, '_blank')}
              className="px-4 py-3 border-b border-blue-500/5 hover:bg-blue-500/5 transition-colors cursor-pointer group"
            >
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 rounded-full bg-blue-500/30 mt-1 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-blue-200/70 mb-0.5 group-hover:text-blue-200 transition-colors flex items-center gap-1">
                    {item.title}
                    {item.link && (
                      <ExternalLink size={9} className="text-blue-400/30 flex-shrink-0" />
                    )}
                  </div>
                  {item.contentSnippet && (
                    <div className="text-[10px] text-blue-300/30 mb-1 line-clamp-2">
                      {item.contentSnippet}
                    </div>
                  )}
                  {item.pubDate && (
                    <div className="flex items-center gap-1 text-[10px] text-blue-300/20">
                      <Clock size={8} />
                      {formatDate(item.pubDate)}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )) || <div className="p-4 text-xs text-blue-400/20 text-center">No articles loaded</div>}
        </div>
      </div>
    </div>
  );
}
