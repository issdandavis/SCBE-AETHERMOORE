import React, { useState } from 'react';
import { Search, BookOpen } from 'lucide-react';

const ARTICLES: Record<string, { title: string; content: string }> = {
  linux: {
    title: 'Linux',
    content:
      'Linux is a family of open-source Unix-like operating systems based on the Linux kernel. The Linux kernel was first released by Linus Torvalds in 1991. Linux is typically packaged as a Linux distribution, which includes the kernel and supporting system software and libraries.',
  },
  react: {
    title: 'React',
    content:
      'React is a free and open-source front-end JavaScript library for building user interfaces based on components. It is maintained by Meta and a community of individual developers and companies.',
  },
  typescript: {
    title: 'TypeScript',
    content:
      'TypeScript is a free and open-source high-level programming language developed by Microsoft that adds static typing with optional type annotations to JavaScript.',
  },
  webassembly: {
    title: 'WebAssembly',
    content:
      'WebAssembly (Wasm) is a binary instruction format for a stack-based virtual machine. Wasm is designed as a portable compilation target for programming languages, enabling deployment on the web.',
  },
  javascript: {
    title: 'JavaScript',
    content:
      'JavaScript is a programming language that is one of the core technologies of the World Wide Web, alongside HTML and CSS. As of 2023, 98.7% of websites use JavaScript on the client side.',
  },
  html: {
    title: 'HTML',
    content:
      'The HyperText Markup Language (HTML) is the standard markup language for documents designed to be displayed in a web browser. It defines the content and structure of web content.',
  },
  css: {
    title: 'CSS',
    content:
      'Cascading Style Sheets (CSS) is a style sheet language used for specifying the presentation and styling of a document written in a markup language such as HTML or XML.',
  },
  git: {
    title: 'Git',
    content:
      'Git is a distributed version control system that tracks changes in any set of computer files, usually used for coordinating work among programmers collaboratively developing source code during software development.',
  },
};

export default function Wiki() {
  const [query, setQuery] = useState('');
  const [article, setArticle] = useState(ARTICLES['linux']);

  const results = query
    ? Object.entries(ARTICLES).filter(
        ([k, v]) =>
          k.includes(query.toLowerCase()) || v.title.toLowerCase().includes(query.toLowerCase())
      )
    : [];

  return (
    <div className="w-full h-full flex bg-[#0d1926] text-blue-100/80">
      <div className="w-56 border-r border-blue-500/10 p-3 overflow-y-auto">
        <div className="relative mb-3">
          <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-blue-400/30" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search..."
            className="w-full bg-[#162032] border border-blue-500/10 rounded-lg pl-7 pr-2 py-1 text-xs outline-none"
          />
        </div>
        {query
          ? results.map(([k, v]) => (
              <button
                key={k}
                onClick={() => {
                  setArticle(v);
                  setQuery('');
                }}
                className="w-full text-left px-2 py-1 text-xs text-blue-200/50 hover:bg-blue-500/10 rounded transition-colors"
              >
                {v.title}
              </button>
            ))
          : Object.entries(ARTICLES).map(([k, v]) => (
              <button
                key={k}
                onClick={() => setArticle(v)}
                className={`w-full text-left px-2 py-1 text-xs rounded transition-colors ${article.title === v.title ? 'bg-blue-500/15 text-blue-200' : 'text-blue-200/50 hover:bg-blue-500/10'}`}
              >
                {v.title}
              </button>
            ))}
      </div>
      <div className="flex-1 p-6 overflow-y-auto">
        <div className="flex items-center gap-2 mb-4">
          <BookOpen size={20} className="text-blue-400" />
          <h1 className="text-2xl text-blue-100 font-semibold">{article.title}</h1>
        </div>
        <div className="bg-[#162032] rounded-xl p-4 border border-blue-500/10 mb-4">
          <p className="text-sm text-blue-200/60 leading-relaxed">{article.content}</p>
        </div>
        <div className="text-xs text-blue-300/20">
          From SCBE Desktop Wiki, the free encyclopedia
        </div>
      </div>
    </div>
  );
}
