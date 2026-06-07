import React, { useState, useCallback } from 'react';
import { ArrowRightLeft, Copy, Volume2, Loader2, Languages } from 'lucide-react';

const LANGS: Record<string, string> = {
  en: 'English',
  es: 'Spanish',
  fr: 'French',
  de: 'German',
  it: 'Italian',
  pt: 'Portuguese',
  ru: 'Russian',
  ja: 'Japanese',
  zh: 'Chinese',
  ko: 'Korean',
  ar: 'Arabic',
  hi: 'Hindi',
  pl: 'Polish',
  nl: 'Dutch',
  sv: 'Swedish',
  tr: 'Turkish',
  vi: 'Vietnamese',
  th: 'Thai',
  id: 'Indonesian',
};

// Fallback dictionary for offline use
const OFFLINE_DICT: Record<string, Record<string, string>> = {
  hello: {
    es: 'hola',
    fr: 'bonjour',
    de: 'hallo',
    it: 'ciao',
    pt: 'olá',
    ru: 'привет',
    ja: 'こんにちは',
    zh: '你好',
    ko: '안녕하세요',
    ar: 'مرحبا',
    hi: 'नमस्ते',
  },
  world: {
    es: 'mundo',
    fr: 'monde',
    de: 'welt',
    it: 'mondo',
    pt: 'mundo',
    ru: 'мир',
    ja: '世界',
    zh: '世界',
    ko: '세계',
    ar: 'عالم',
    hi: 'दुनिया',
  },
  thank: {
    es: 'gracias',
    fr: 'merci',
    de: 'danke',
    it: 'grazie',
    pt: 'obrigado',
    ru: 'спасибо',
    ja: 'ありがとう',
    zh: '谢谢',
    ko: '감사합니다',
    ar: 'شكرا',
    hi: 'धन्यवाद',
  },
  love: {
    es: 'amor',
    fr: 'amour',
    de: 'liebe',
    it: 'amore',
    pt: 'amor',
    ru: 'любовь',
    ja: '愛',
    zh: '爱',
    ko: '사랑',
    ar: 'حب',
    hi: 'प्यार',
  },
  goodbye: {
    es: 'adiós',
    fr: 'au revoir',
    de: 'auf wiedersehen',
    it: 'arrivederci',
    pt: 'adeus',
    ru: 'до свидания',
    ja: 'さようなら',
    zh: '再见',
    ko: '안녕히 가세요',
    ar: 'وداعا',
    hi: 'अलविदा',
  },
  good: {
    es: 'bueno',
    fr: 'bon',
    de: 'gut',
    it: 'buono',
    pt: 'bom',
    ru: 'хорошо',
    ja: '良い',
    zh: '好',
    ko: '좋은',
    ar: 'جيد',
    hi: 'अच्छा',
  },
  morning: {
    es: 'mañana',
    fr: 'matin',
    de: 'morgen',
    it: 'mattina',
    pt: 'manhã',
    ru: 'утро',
    ja: '朝',
    zh: '早上',
    ko: '아침',
    ar: 'صباح',
    hi: 'सुबह',
  },
  night: {
    es: 'noche',
    fr: 'nuit',
    de: 'nacht',
    it: 'notte',
    pt: 'noite',
    ru: 'ночь',
    ja: '夜',
    zh: '晚上',
    ko: '밤',
    ar: 'ليل',
    hi: 'रात',
  },
  water: {
    es: 'agua',
    fr: 'eau',
    de: 'wasser',
    it: 'acqua',
    pt: 'água',
    ru: 'вода',
    ja: '水',
    zh: '水',
    ko: '물',
    ar: 'ماء',
    hi: 'पानी',
  },
  friend: {
    es: 'amigo',
    fr: 'ami',
    de: 'freund',
    it: 'amico',
    pt: 'amigo',
    ru: 'друг',
    ja: '友達',
    zh: '朋友',
    ko: '친구',
    ar: 'صديق',
    hi: 'दोस्त',
  },
};

function offlineTranslate(text: string, targetLang: string): string | null {
  const key = Object.keys(OFFLINE_DICT).find((k) => text.toLowerCase().trim() === k);
  if (key && OFFLINE_DICT[key][targetLang]) return OFFLINE_DICT[key][targetLang];
  return null;
}

export default function Translator() {
  const [from, setFrom] = useState('en');
  const [to, setTo] = useState('es');
  const [text, setText] = useState('Hello');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<
    { from: string; to: string; original: string; translated: string }[]
  >([]);

  const translate = useCallback(async () => {
    if (!text.trim()) return;
    setLoading(true);

    // Try offline first
    const offline = offlineTranslate(text, to);
    if (offline) {
      setResult(offline);
      setHistory((prev) =>
        [{ from, to, original: text, translated: offline }, ...prev].slice(0, 10)
      );
      setLoading(false);
      return;
    }

    // Try LibreTranslate API
    try {
      const res = await fetch('https://libretranslate.de/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ q: text, source: from, target: to, format: 'text' }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.translatedText) {
          setResult(data.translatedText);
          setHistory((prev) =>
            [{ from, to, original: text, translated: data.translatedText }, ...prev].slice(0, 10)
          );
          setLoading(false);
          return;
        }
      }
    } catch {
      /* API may be unavailable */
    }

    // Final fallback: word-by-word offline
    const words = text.toLowerCase().split(/\s+/);
    const translated = words
      .map((w) => {
        for (const [key, dict] of Object.entries(OFFLINE_DICT)) {
          if (w === key && dict[to]) return dict[to];
        }
        return w;
      })
      .join(' ');
    setResult(translated || `[Translated to ${LANGS[to]}]: ${text}`);
    setHistory((prev) =>
      [
        {
          from,
          to,
          original: text,
          translated: translated || `[Translated to ${LANGS[to]}]: ${text}`,
        },
        ...prev,
      ].slice(0, 10)
    );
    setLoading(false);
  }, [text, from, to]);

  const speak = (text: string, lang: string) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang;
      window.speechSynthesis.speak(utterance);
    }
  };

  const swap = () => {
    setFrom(to);
    setTo(from);
    setText(result);
    setResult(text);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80 p-4">
      <div className="flex items-center gap-2 mb-4">
        <Languages size={16} className="text-blue-400" />
        <h2 className="text-sm text-blue-200 font-semibold">Translator</h2>
      </div>
      <div className="flex items-center gap-2 mb-4">
        <select
          value={from}
          onChange={(e) => setFrom(e.target.value)}
          className="flex-1 bg-[#162032] border border-blue-500/15 rounded-xl px-3 py-2 text-sm outline-none"
        >
          {Object.entries(LANGS).map(([code, name]) => (
            <option key={code} value={code}>
              {name}
            </option>
          ))}
        </select>
        <button
          onClick={swap}
          className="p-2 rounded-lg hover:bg-blue-500/20 text-blue-400 transition-colors"
        >
          <ArrowRightLeft size={16} />
        </button>
        <select
          value={to}
          onChange={(e) => setTo(e.target.value)}
          className="flex-1 bg-[#162032] border border-blue-500/15 rounded-xl px-3 py-2 text-sm outline-none"
        >
          {Object.entries(LANGS).map(([code, name]) => (
            <option key={code} value={code}>
              {name}
            </option>
          ))}
        </select>
      </div>
      <div className="flex-1 flex flex-col gap-3 min-h-0">
        <div className="relative flex-1">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Enter text..."
            className="w-full h-full bg-[#162032] border border-blue-500/15 rounded-xl p-3 text-sm resize-none outline-none focus:border-blue-500/30"
          />
          <button
            onClick={() => speak(text, from)}
            className="absolute bottom-2 right-2 p-1.5 rounded hover:bg-blue-500/20 text-blue-300/40 hover:text-blue-300 transition-colors"
          >
            <Volume2 size={13} />
          </button>
        </div>
        <button
          onClick={translate}
          disabled={loading}
          className="px-6 py-2 rounded-xl bg-blue-500/20 hover:bg-blue-500/30 disabled:opacity-50 text-blue-200 text-sm transition-colors self-center flex items-center gap-2"
        >
          {loading && <Loader2 size={14} className="animate-spin" />}
          Translate
        </button>
        <div className="relative flex-1 bg-[#162032] border border-blue-500/15 rounded-xl p-3 text-sm">
          {result ? (
            <>
              <div className="text-blue-200/70">{result}</div>
              <div className="absolute top-2 right-2 flex gap-1">
                <button
                  onClick={() => navigator.clipboard.writeText(result)}
                  className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/40 hover:text-blue-300 transition-colors"
                >
                  <Copy size={13} />
                </button>
                <button
                  onClick={() => speak(result, to)}
                  className="p-1.5 rounded hover:bg-blue-500/20 text-blue-300/40 hover:text-blue-300 transition-colors"
                >
                  <Volume2 size={13} />
                </button>
              </div>
            </>
          ) : (
            <div className="text-blue-400/20 italic">Translation will appear here...</div>
          )}
        </div>
      </div>
      {history.length > 0 && (
        <div className="mt-3">
          <div className="text-[10px] uppercase tracking-wider text-blue-400/30 mb-1">Recent</div>
          <div className="space-y-1 max-h-20 overflow-y-auto">
            {history.slice(0, 5).map((h, i) => (
              <button
                key={i}
                onClick={() => {
                  setText(h.original);
                  setResult(h.translated);
                  setFrom(h.from);
                  setTo(h.to);
                }}
                className="w-full text-left px-2 py-1 rounded bg-[#162032] text-[10px] text-blue-200/50 hover:text-blue-200/70 transition-colors truncate"
              >
                {h.original} → {h.translated}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
