import React, { useState, useCallback } from 'react';
import { BookOpen, Search, Volume2, Loader2, ExternalLink } from 'lucide-react';

interface Definition {
  definition: string;
  example?: string;
  synonyms: string[];
  antonyms: string[];
}
interface Meaning {
  partOfSpeech: string;
  definitions: Definition[];
  synonyms: string[];
  antonyms: string[];
}
interface Phonetic {
  text?: string;
  audio?: string;
}
interface DictEntry {
  word: string;
  phonetics: Phonetic[];
  meanings: Meaning[];
  sourceUrls: string[];
}

export default function Dictionary() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<DictEntry | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState<DictEntry[]>([]);

  const search = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    setResult(null);

    try {
      const res = await fetch(
        `https://api.dictionaryapi.dev/api/v2/entries/en/${encodeURIComponent(query.trim().toLowerCase())}`
      );
      if (!res.ok) {
        if (res.status === 404) setError(`No definitions found for "${query}"`);
        else setError('Failed to fetch definition. Try again.');
        setLoading(false);
        return;
      }
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) {
        const entry: DictEntry = data[0];
        setResult(entry);
        setHistory((prev) => [entry, ...prev.filter((e) => e.word !== entry.word)].slice(0, 10));
      }
    } catch {
      setError('Network error. Check your connection.');
    }
    setLoading(false);
  }, [query]);

  const speak = (text: string) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'en';
      window.speechSynthesis.speak(utterance);
    }
  };

  const audioUrl = result?.phonetics.find((p) => p.audio)?.audio;
  const phoneticText = result?.phonetics.find((p) => p.text)?.text;

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4 overflow-hidden">
      <div className="flex items-center gap-2 mb-4">
        <BookOpen size={18} className="text-blue-400" />
        <h2 className="text-lg text-blue-200 font-semibold">Dictionary</h2>
      </div>
      <div className="flex gap-2 mb-4">
        <div className="flex-1 relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-blue-400/30" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search()}
            placeholder="Search word..."
            className="w-full bg-[#162032] border border-blue-500/15 rounded-xl pl-9 pr-3 py-2 text-sm outline-none focus:border-blue-500/30"
          />
        </div>
        <button
          onClick={search}
          disabled={loading}
          className="px-4 py-2 rounded-xl bg-blue-500/20 text-blue-200 text-xs hover:bg-blue-500/30 transition-colors disabled:opacity-50 flex items-center gap-1.5"
        >
          {loading && <Loader2 size={12} className="animate-spin" />}
          Search
        </button>
      </div>

      {error && (
        <div className="text-xs text-red-400/80 bg-red-500/5 rounded-lg px-3 py-2 mb-3">
          {error}
        </div>
      )}

      {result && (
        <div className="flex-1 overflow-y-auto space-y-3">
          <div className="bg-[#162032] rounded-xl p-4 border border-blue-500/10">
            <div className="flex items-center gap-3 mb-2">
              <div className="text-2xl text-blue-100 font-semibold capitalize">{result.word}</div>
              {phoneticText && (
                <div className="text-sm text-blue-400/50 font-mono">{phoneticText}</div>
              )}
              {audioUrl && (
                <button
                  onClick={() => new Audio(audioUrl).play()}
                  className="p-1.5 rounded-full bg-blue-500/15 hover:bg-blue-500/25 text-blue-300 transition-colors"
                >
                  <Volume2 size={14} />
                </button>
              )}
              <button
                onClick={() => speak(result.word)}
                className="p-1.5 rounded-full bg-blue-500/15 hover:bg-blue-500/25 text-blue-300 transition-colors"
              >
                <Volume2 size={14} />
              </button>
            </div>

            {result.meanings.map((meaning, mi) => (
              <div key={mi} className="mb-3 last:mb-0">
                <div className="text-xs text-blue-400/60 italic mb-1.5 font-medium">
                  {meaning.partOfSpeech}
                </div>
                <div className="space-y-1.5">
                  {meaning.definitions.slice(0, 3).map((def, di) => (
                    <div key={di} className="flex gap-2">
                      <span className="text-blue-400/30 text-xs mt-0.5">{di + 1}.</span>
                      <div>
                        <div className="text-sm text-blue-200/70">{def.definition}</div>
                        {def.example && (
                          <div className="text-xs text-blue-300/30 italic mt-0.5">
                            "{def.example}"
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                {meaning.synonyms.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    <span className="text-[10px] text-blue-400/30">Synonyms:</span>
                    {meaning.synonyms.slice(0, 5).map((s) => (
                      <span
                        key={s}
                        className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-300/50"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {result.sourceUrls.length > 0 && (
              <div className="mt-2 pt-2 border-t border-blue-500/5 flex items-center gap-1">
                <span className="text-[10px] text-blue-400/20">Source:</span>
                {result.sourceUrls.map((url) => (
                  <button
                    key={url}
                    onClick={() => window.open(url, '_blank')}
                    className="text-[10px] text-blue-400/40 hover:text-blue-300 flex items-center gap-0.5 transition-colors"
                  >
                    <ExternalLink size={8} />
                    {new URL(url).hostname}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {history.length > 0 && !result && (
        <div className="mt-2">
          <div className="text-[10px] uppercase tracking-wider text-blue-400/30 mb-2">
            Recent Searches
          </div>
          <div className="flex flex-wrap gap-1.5">
            {history.map((e) => (
              <button
                key={e.word}
                onClick={() => {
                  setQuery(e.word);
                  setResult(e);
                  setError('');
                }}
                className="px-2 py-1 rounded-lg bg-[#162032] text-xs text-blue-200/50 hover:text-blue-200 hover:bg-blue-500/10 transition-colors capitalize"
              >
                {e.word}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
