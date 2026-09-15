"use client";

import { useMemo } from "react";
import katex from "katex";

/**
 * Renders inline `$...$` / `\(...\)` and display `$$...$$` / `\[...\]` math with
 * KaTeX (SPEC §19). Everything else is emitted as plain text so extracted PDF
 * text (which is rarely valid LaTeX) never breaks the reader.
 */
const MATH_RE = /(\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\$[^$\n]+?\$|\\\([\s\S]+?\\\))/g;

type Part = { kind: "text"; value: string } | { kind: "math"; value: string; display: boolean };

function split(text: string): Part[] {
  const parts: Part[] = [];
  let last = 0;
  for (const m of text.matchAll(MATH_RE)) {
    const idx = m.index ?? 0;
    if (idx > last) parts.push({ kind: "text", value: text.slice(last, idx) });
    const raw = m[0];
    let inner = raw;
    let display = false;
    if (raw.startsWith("$$")) {
      inner = raw.slice(2, -2);
      display = true;
    } else if (raw.startsWith("\\[")) {
      inner = raw.slice(2, -2);
      display = true;
    } else if (raw.startsWith("\\(")) {
      inner = raw.slice(2, -2);
    } else {
      inner = raw.slice(1, -1);
    }
    parts.push({ kind: "math", value: inner, display });
    last = idx + raw.length;
  }
  if (last < text.length) parts.push({ kind: "text", value: text.slice(last) });
  return parts;
}

export function TextWithMath({ text }: { text: string }) {
  const parts = useMemo(() => split(text), [text]);
  if (parts.length === 1 && parts[0].kind === "text") return <>{text}</>;

  return (
    <>
      {parts.map((p, i) => {
        if (p.kind === "text") return <span key={i}>{p.value}</span>;
        let html: string;
        try {
          html = katex.renderToString(p.value, {
            displayMode: p.display,
            throwOnError: false,
            output: "html",
            strict: false,
          });
        } catch {
          return (
            <span key={i} className="font-mono text-[0.9em]">
              {p.value}
            </span>
          );
        }
        return p.display ? (
          <span
            key={i}
            className="block overflow-x-auto"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        ) : (
          <span key={i} dangerouslySetInnerHTML={{ __html: html }} />
        );
      })}
    </>
  );
}
