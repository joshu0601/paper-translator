"use client";

import { useWorkspace } from "@/components/workspace/workspace-context";
import { paragraphNumber } from "@/lib/utils";
import type { Citation } from "@/types";

/** Clickable source reference: scrolls the reader to the paragraph (SPEC §28–29). */
export function CitationChip({ citation }: { citation: Citation }) {
  const { jumpToParagraph, paper } = useWorkspace();
  const exists = paper.paragraphs.some((p) => p.id === citation.paragraphId);
  const label = [
    citation.page ? `p.${citation.page}` : null,
    citation.section ? citation.section : null,
    citation.paragraphId ? `¶${paragraphNumber(citation.paragraphId)}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <button
      type="button"
      disabled={!exists}
      onClick={() => jumpToParagraph(citation.paragraphId)}
      title={citation.snippet ?? citation.paragraphId}
      className="mx-0.5 inline-flex max-w-full items-center gap-1 truncate rounded border bg-muted/60 px-1.5 py-px align-baseline font-mono text-[10.5px] leading-tight text-muted-foreground transition-colors hover:bg-highlight hover:text-foreground disabled:cursor-default disabled:opacity-60"
    >
      {label || "來源"}
    </button>
  );
}
