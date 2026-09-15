"use client";

import { Fragment, type ReactNode } from "react";
import { CitationChip } from "./citation-chip";
import { TextWithMath } from "@/components/paper-reader/text-with-math";
import type { Citation } from "@/types";

/**
 * Minimal Markdown renderer for assistant messages: headings, bullet / numbered
 * lists, paragraphs, **bold**, `code`, math and inline citation tokens such as
 * `[Page 7 · Section 4.2 · Paragraph 73]` (SPEC §73) which become clickable.
 */
const CITATION_RE =
  /\[(?:Page\s*(\d+))?\s*(?:·|,|;)?\s*(?:Section\s*([^·\]]+?))?\s*(?:·|,|;)?\s*Paragraph\s*(\d+)\s*\]|\[(paragraph_\d+)\]/g;

export function MarkdownLite({
  text,
  citations,
}: {
  text: string;
  citations?: Citation[];
}) {
  const blocks = text.replace(/\r\n/g, "\n").split(/\n{2,}/);
  return (
    <div className="chat-markdown text-[13px] leading-relaxed">
      {blocks.map((block, i) => (
        <Block key={i} block={block} citations={citations} />
      ))}
    </div>
  );
}

function Block({ block, citations }: { block: string; citations?: Citation[] }) {
  const lines = block.split("\n").filter((l) => l.trim().length > 0);
  if (lines.length === 0) return null;

  const heading = lines.length === 1 && lines[0].match(/^(#{1,4})\s+(.*)$/);
  if (heading) {
    const level = heading[1].length;
    const Tag = (`h${Math.min(level + 2, 6)}`) as "h3" | "h4" | "h5" | "h6";
    return (
      <Tag>
        <Inline text={heading[2]} citations={citations} />
      </Tag>
    );
  }

  const isBullet = lines.every((l) => /^\s*[-*•]\s+/.test(l));
  const isNumbered = lines.every((l) => /^\s*\d+[.)]\s+/.test(l));
  if (isBullet || isNumbered) {
    const Tag = isBullet ? "ul" : "ol";
    return (
      <Tag>
        {lines.map((l, i) => (
          <li key={i}>
            <Inline
              text={l.replace(isBullet ? /^\s*[-*•]\s+/ : /^\s*\d+[.)]\s+/, "")}
              citations={citations}
            />
          </li>
        ))}
      </Tag>
    );
  }

  return (
    <p>
      {lines.map((l, i) => (
        <Fragment key={i}>
          {i > 0 && <br />}
          <Inline text={l} citations={citations} />
        </Fragment>
      ))}
    </p>
  );
}

function Inline({ text, citations }: { text: string; citations?: Citation[] }) {
  const nodes: ReactNode[] = [];
  let last = 0;
  let key = 0;
  for (const m of text.matchAll(CITATION_RE)) {
    const idx = m.index ?? 0;
    if (idx > last) nodes.push(<Styled key={key++} text={text.slice(last, idx)} />);
    const paragraphNo = m[3] ? parseInt(m[3], 10) : undefined;
    const paragraphId = m[4] ?? (paragraphNo !== undefined ? `paragraph_${String(paragraphNo).padStart(4, "0")}` : undefined);
    const known = citations?.find((c) => c.paragraphId === paragraphId);
    nodes.push(
      <CitationChip
        key={key++}
        citation={
          known ?? {
            paragraphId: paragraphId ?? "",
            page: m[1] ? parseInt(m[1], 10) : 0,
            section: m[2]?.trim() ?? "",
          }
        }
      />,
    );
    last = idx + m[0].length;
  }
  if (last < text.length) nodes.push(<Styled key={key++} text={text.slice(last)} />);
  return <>{nodes}</>;
}

/** **bold** and `code` */
function Styled({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return (
    <>
      {parts.map((p, i) => {
        if (p.startsWith("**") && p.endsWith("**"))
          return <strong key={i}>{p.slice(2, -2)}</strong>;
        if (p.startsWith("`") && p.endsWith("`")) return <code key={i}>{p.slice(1, -1)}</code>;
        return <TextWithMath key={i} text={p} />;
      })}
    </>
  );
}
