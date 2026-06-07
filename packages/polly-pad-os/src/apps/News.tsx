import React, { useState, useEffect } from 'react';
import { Newspaper, Clock, ExternalLink, Loader2 } from 'lucide-react';

interface HNItem {
  id: number;
  title: string;
  by: string;
  time: number;
  score: number;
  url?: string;
  descendants?: number;
  type: string;
}

const CATEGORY_URLS: Record<string, { endpoint: string; label: string }> = {
  top: { endpoint: 'topstories', label: 'Top' },
  new: { endpoint: 'newstories', label: 'New' },
  best: { endpoint: 'beststories', label: 'Best' },
  ask: { endpoint: 'askstories', label: 'Ask' },
  show: { endpoint: 'showstories', label: 'Show' },
  job: { endpoint: 'jobstories', label: 'Jobs' },
};

export default function News() {
  const [category, setCategory] = useState('top');
  const [articles, setArticles] = useState<HNItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchStories = async () => {
      setLoading(true);
      setError('');
      try {
        const endpoint = CATEGORY_URLS[category]?.endpoint || 'topstories';
        const res = await fetch(`https://hacker-news.firebaseio.com/v0/${endpoint}.json`);
        if (!res.ok) throw new Error('Failed to fetch');
        const ids: number[] = await res.json();
        const topIds = ids.slice(0, 20);

        const items = await Promise.all(
          topIds.map(async (id) => {
            const r = await fetch(`https://hacker-news.firebaseio.com/v0/item/${id}.json`);
            return r.json() as Promise<HNItem>;
          })
        );
        setArticles(items.filter((i) => i && i.title));
      } catch {
        setError('Failed to load news. Check your connection.');
      } finally {
        setLoading(false);
      }
    };
    fetchStories();
  }, [category]);

  const formatTime = (unixTime: number) => {
    const diff = Date.now() / 1000 - unixTime;
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  const openUrl = (url?: string, id?: number) => {
    if (url) window.open(url, '_blank');
    else if (id) window.open(`https://news.ycombinator.com/item?id=${id}`, '_blank');
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-blue-500/10">
        <Newspaper size={16} className="text-blue-400" />
        <h2 className="text-sm text-blue-200 font-semibold">Hacker News</h2>
        <div className="flex-1" />
        {loading && <Loader2 size={14} className="text-blue-400 animate-spin" />}
      </div>
      <div className="flex gap-1 p-2 overflow-x-auto border-b border-blue-500/5">
        {Object.entries(CATEGORY_URLS).map(([key, val]) => (
          <button
            key={key}
            onClick={() => setCategory(key)}
            className={`px-3 py-1 rounded-lg text-xs whitespace-nowrap transition-colors ${category === key ? 'bg-blue-500/20 text-blue-200' : 'text-blue-300/30 hover:text-blue-200/60 hover:bg-blue-500/5'}`}
          >
            {val.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto">
        {error && <div className="p-4 text-xs text-red-400/80 text-center">{error}</div>}
        {articles.map((article, i) => (
          <div
            key={article.id}
            onClick={() => openUrl(article.url, article.id)}
            className="px-4 py-3 border-b border-blue-500/5 hover:bg-blue-500/5 transition-colors cursor-pointer group"
          >
            <div className="flex items-start gap-3">
              <div className="text-[10px] text-blue-400/30 font-mono w-5 text-right flex-shrink-0 mt-0.5">
                {i + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs text-blue-200/80 mb-0.5 group-hover:text-blue-200 transition-colors flex items-center gap-1">
                  {article.title}
                  {article.url && (
                    <ExternalLink size={10} className="text-blue-400/30 flex-shrink-0" />
                  )}
                </div>
                <div className="flex items-center gap-3 text-[10px] text-blue-300/30">
                  <span>{article.score} points</span>
                  <span>by {article.by}</span>
                  <span className="flex items-center gap-0.5">
                    <Clock size={8} />
                    {formatTime(article.time)}
                  </span>
                  {article.descendants !== undefined && <span>{article.descendants} comments</span>}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
