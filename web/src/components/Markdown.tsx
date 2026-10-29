"use client";

import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import "highlight.js/styles/github-dark.css";

/** GitHub-flavoured markdown (tables, task lists, strikethrough, autolinks, fenced code) styled like github.com in dark mode. */
export function Markdown({ children, className = "" }: { children: string; className?: string }) {
  return (
    <div className={`markdown-body ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: false, ignoreMissing: true }]]}
        components={{
          a: ({ href, children: c }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {c}
            </a>
          ),
          table: ({ children: c }) => (
            <div className="table-wrap">
              <table>{c}</table>
            </div>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
