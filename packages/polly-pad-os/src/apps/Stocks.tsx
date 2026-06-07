import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Loader2,
  RefreshCw,
  Search,
  ExternalLink,
} from 'lucide-react';

const DEFAULT_TICKERS = [
  'AAPL',
  'GOOGL',
  'MSFT',
  'AMZN',
  'TSLA',
  'META',
  'NVDA',
  'NFLX',
  'AMD',
  'INTC',
];

interface StockData {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  open: number;
  high: number;
  low: number;
  volume: number;
  name: string;
}

export default function Stocks() {
  const [stocks, setStocks] = useState<StockData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [watchlist, setWatchlist] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('linuxos_watchlist');
      return saved ? JSON.parse(saved) : DEFAULT_TICKERS;
    } catch {
      return DEFAULT_TICKERS;
    }
  });

  useEffect(() => {
    localStorage.setItem('linuxos_watchlist', JSON.stringify(watchlist));
  }, [watchlist]);

  const fetchStockData = async (symbols: string[]) => {
    setLoading(true);
    setError('');
    try {
      // Use Yahoo Finance via a CORS-friendly approach
      const results = await Promise.all(
        symbols.map(async (symbol) => {
          try {
            const res = await fetch(
              `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1d&range=1d`
            );
            if (!res.ok) return null;
            const data = await res.json();
            const result = data.chart?.result?.[0];
            if (!result) return null;
            const meta = result.meta;
            const prevClose =
              meta.previousClose || meta.chartPreviousClose || meta.regularMarketPrice;
            const price = meta.regularMarketPrice || prevClose;
            const change = price - prevClose;
            const changePercent = prevClose ? (change / prevClose) * 100 : 0;
            return {
              symbol,
              price: Math.round(price * 100) / 100,
              change: Math.round(change * 100) / 100,
              changePercent: Math.round(changePercent * 100) / 100,
              open: meta.regularMarketOpen || meta.previousClose,
              high: meta.regularMarketDayHigh || price,
              low: meta.regularMarketDayLow || price,
              volume: meta.regularMarketVolume || 0,
              name: meta.shortName || meta.symbol || symbol,
            };
          } catch {
            return null;
          }
        })
      );
      setStocks(results.filter(Boolean) as StockData[]);
    } catch {
      setError('Failed to fetch stock data. Using fallback values.');
      // Fallback with simulated data
      setStocks(
        symbols.map((symbol, i) => ({
          symbol,
          price: 100 + i * 50,
          change: (Math.random() - 0.5) * 10,
          changePercent: (Math.random() - 0.5) * 5,
          open: 100 + i * 50,
          high: 110 + i * 50,
          low: 90 + i * 50,
          volume: Math.floor(Math.random() * 10000000),
          name: symbol,
        }))
      );
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchStockData(watchlist);
  }, [watchlist]);

  const addStock = () => {
    const symbol = searchInput.trim().toUpperCase();
    if (symbol && !watchlist.includes(symbol)) {
      setWatchlist([...watchlist, symbol]);
      setSearchInput('');
    }
  };

  const removeStock = (symbol: string) => setWatchlist(watchlist.filter((s) => s !== symbol));

  const selectedStock = stocks.find((s) => s.symbol === selectedSymbol);
  const totalValue = stocks.reduce((sum, s) => sum + s.price, 0);
  const totalChange = stocks.reduce((sum, s) => sum + s.change, 0);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4 overflow-hidden">
      <h2 className="text-lg text-blue-200 font-semibold mb-3 flex items-center gap-2">
        <DollarSign size={18} className="text-green-400" />
        Stocks
      </h2>

      <div className="flex items-center gap-2 mb-3">
        <div className="text-xs px-2 py-1 rounded bg-blue-500/10 text-blue-300/50">
          {stocks.length} stocks
        </div>
        <div
          className={`text-xs px-2 py-1 rounded ${totalChange >= 0 ? 'bg-green-500/10 text-green-300/50' : 'bg-red-500/10 text-red-300/50'}`}
        >
          ${totalValue.toFixed(2)} ({totalChange >= 0 ? '+' : ''}
          {totalChange.toFixed(2)})
        </div>
        <div className="flex-1" />
        <button
          onClick={() => fetchStockData(watchlist)}
          className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/40 hover:text-blue-300 transition-colors"
          title="Refresh"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="flex gap-2 mb-3">
        <div className="flex-1 relative">
          <Search
            size={12}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-blue-400/30"
          />
          <input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addStock()}
            placeholder="Add ticker..."
            className="w-full bg-[#162032] border border-blue-500/15 rounded-lg pl-8 pr-2 py-1.5 text-xs outline-none focus:border-blue-500/30"
          />
        </div>
        <button
          onClick={addStock}
          className="px-3 py-1.5 rounded-lg bg-blue-500/20 text-blue-300 text-xs hover:bg-blue-500/30 transition-colors"
        >
          Add
        </button>
      </div>

      {error && (
        <div className="text-xs text-yellow-400/60 bg-yellow-500/10 rounded-lg px-3 py-1.5 mb-2">
          {error}
        </div>
      )}

      <div className="space-y-1.5 flex-1 overflow-y-auto">
        {stocks.map((s) => (
          <div
            key={s.symbol}
            onClick={() => setSelectedSymbol(selectedSymbol === s.symbol ? null : s.symbol)}
            className={`flex items-center justify-between px-3 py-2 rounded-xl bg-[#162032] border transition-all cursor-pointer ${selectedSymbol === s.symbol ? 'border-blue-500/30' : 'border-blue-500/5 hover:border-blue-500/15'}`}
          >
            <div>
              <div className="text-xs text-blue-200 font-semibold">{s.symbol}</div>
              <div className="text-[10px] text-blue-300/30">{s.name}</div>
            </div>
            <div className="text-right">
              <div className="text-xs text-blue-200 font-mono">${s.price.toFixed(2)}</div>
              <div
                className={`text-[10px] flex items-center gap-0.5 ${s.change >= 0 ? 'text-green-400' : 'text-red-400'}`}
              >
                {s.change >= 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                {s.change >= 0 ? '+' : ''}
                {s.change.toFixed(2)} ({s.changePercent >= 0 ? '+' : ''}
                {s.changePercent.toFixed(2)}%)
              </div>
            </div>
          </div>
        ))}
      </div>

      {selectedStock && (
        <div className="mt-3 p-3 rounded-xl bg-[#162032] border border-blue-500/10">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-blue-200">
              {selectedStock.symbol} Details
            </span>
            <div className="flex gap-1">
              <button
                onClick={() =>
                  window.open(`https://finance.yahoo.com/quote/${selectedStock.symbol}`, '_blank')
                }
                className="p-1 rounded hover:bg-blue-500/20 text-blue-300/40 transition-colors"
              >
                <ExternalLink size={12} />
              </button>
              <button
                onClick={() => removeStock(selectedStock.symbol)}
                className="p-1 rounded hover:bg-red-500/20 text-red-400/40 hover:text-red-400 transition-colors text-xs"
              >
                Remove
              </button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[10px]">
            <div className="text-blue-300/30">
              Open: <span className="text-blue-200/70">${selectedStock.open.toFixed(2)}</span>
            </div>
            <div className="text-blue-300/30">
              High: <span className="text-green-300/70">${selectedStock.high.toFixed(2)}</span>
            </div>
            <div className="text-blue-300/30">
              Low: <span className="text-red-300/70">${selectedStock.low.toFixed(2)}</span>
            </div>
            <div className="text-blue-300/30">
              Vol:{' '}
              <span className="text-blue-200/70">
                {(selectedStock.volume / 1000000).toFixed(1)}M
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
