"use client";

import type { Highlight, Paragraph } from "@/types";
import { TextWithMath } from "./text-with-math";
import { cn } from "@/lib/utils";

interface Props {
  paragraph: Paragraph;
  lang: "en" | "zh";
  highlights: Highlight[];
  className?: string;
}

/**
 * One language column of a paragraph. Splits the text around user highlights
 * (only applied to the English source, where the offsets were captured).
 */
export function ParagraphText({ paragraph, lang, highlights, className }: Props) {
  const text =
    lang === "en" ? paragraph.originalText : (paragraph.translatedText ?? "");

  const base = cn(
    "paper-text",
    lang === "zh" && "paper-text-zh",
    paragraph.kind === "heading" && "font-semibold",
    paragraph.kind === "equation" && "text-center font-mono text-[0.95em]",
    paragraph.kind === "caption" && "text-[0.9em] text-muted-foreground",
    paragraph.kind === "reference" && "text-[0.85em] leading-relaxed text-muted-foreground",
    className,
  );

  if (lang === "zh" && !text) {
    return (
      <div className={cn(base, "text-muted-foreground/60 italic")}>
        翻譯中…
      </div>
    );
  }

  const ranges =
    lang === "en"
      ? highlights
          .filter((h) => h.startOffset < h.endOffset && h.startOffset < text.length)
          .sort((a, b) => a.startOffset - b.startOffset)
      : [];

  if (ranges.length === 0) {
    return (
      <div className={base} data-lang={lang}>
        <TextWithMath text={text} />
      </div>
    );
  }

  const segments: { text: string; mark: boolean; key: string }[] = [];
  let cursor = 0;
  for (const h of ranges) {
    const start = Math.max(h.startOffset, cursor);
    const end = Math.min(h.endOffset, text.length);
    if (start > cursor) segments.push({ text: text.slice(cursor, start), mark: false, key: `t${cursor}` });
    if (end > start) segments.push({ text: text.slice(start, end), mark: true, key: h.id });
    cursor = Math.max(cursor, end);
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor), mark: false, key: `t${cursor}` });

  return (
    <div className={base} data-lang={lang}>
      {segments.map((s) =>
        s.mark ? (
          <mark key={s.key} className="user-highlight">
            <TextWithMath text={s.text} />
          </mark>
        ) : (
          <TextWithMath key={s.key} text={s.text} />
        ),
      )}
    </div>
  );
}
