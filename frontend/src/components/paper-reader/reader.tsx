"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import { useWorkspace } from "@/components/workspace/workspace-context";
import { ParagraphText } from "./paragraph-text";
import { SelectionToolbar } from "./selection-toolbar";
import { cn, paragraphNumber } from "@/lib/utils";
import type { Highlight, Paragraph, Section } from "@/types";

export function PaperReader() {
  const {
    paper,
    readingMode,
    hoveredParagraphId,
    setHoveredParagraphId,
    flashParagraphId,
    setCurrentSectionId,
    setCurrentPage,
    setSelection,
  } = useWorkspace();
  const scrollRef = useRef<HTMLDivElement>(null);

  const bySection = useMemo(() => {
    const map = new Map<string, Paragraph[]>();
    for (const p of paper.paragraphs) {
      const list = map.get(p.sectionId) ?? [];
      list.push(p);
      map.set(p.sectionId, list);
    }
    return map;
  }, [paper.paragraphs]);

  const highlightsByParagraph = useMemo(() => {
    const map = new Map<string, Highlight[]>();
    for (const h of paper.highlights) {
      const list = map.get(h.paragraphId) ?? [];
      list.push(h);
      map.set(h.paragraphId, list);
    }
    return map;
  }, [paper.highlights]);

  // Track the section / page currently at the top of the viewport (SPEC §23).
  const onScroll = useCallback(() => {
    const root = scrollRef.current;
    if (!root) return;
    const top = root.getBoundingClientRect().top + 96;
    const nodes = root.querySelectorAll<HTMLElement>("[data-paragraph-id]");
    for (const node of nodes) {
      const r = node.getBoundingClientRect();
      if (r.bottom >= top) {
        const sectionId = node.dataset.sectionId ?? null;
        const page = Number(node.dataset.page ?? "1");
        setCurrentSectionId(sectionId);
        setCurrentPage(page);
        return;
      }
    }
  }, [setCurrentSectionId, setCurrentPage]);

  useEffect(() => {
    const root = scrollRef.current;
    if (!root) return;
    let raf = 0;
    const handler = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(onScroll);
    };
    root.addEventListener("scroll", handler, { passive: true });
    onScroll();
    return () => {
      root.removeEventListener("scroll", handler);
      cancelAnimationFrame(raf);
    };
  }, [onScroll, paper.paragraphs.length]);

  // Capture text selections inside English paragraphs (SPEC §31).
  const onMouseUp = useCallback(() => {
    // Defer so the browser has finalised the selection.
    setTimeout(() => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || sel.rangeCount === 0) {
        setSelection(null);
        return;
      }
      const range = sel.getRangeAt(0);
      const container =
        range.commonAncestorContainer instanceof Element
          ? range.commonAncestorContainer
          : range.commonAncestorContainer.parentElement;
      const textEl = container?.closest<HTMLElement>("[data-lang]");
      const block = textEl?.closest<HTMLElement>("[data-paragraph-id]");
      if (!textEl || !block) {
        setSelection(null);
        return;
      }
      const text = sel.toString().trim();
      if (!text) {
        setSelection(null);
        return;
      }
      const pre = document.createRange();
      pre.selectNodeContents(textEl);
      pre.setEnd(range.startContainer, range.startOffset);
      const startOffset = pre.toString().length;
      const rect = range.getBoundingClientRect();
      setSelection({
        paragraphId: block.dataset.paragraphId!,
        text,
        startOffset,
        endOffset: startOffset + sel.toString().length,
        rect: { top: rect.top, left: rect.left, width: rect.width, height: rect.height },
      });
    }, 0);
  }, [setSelection]);

  const bilingual = readingMode === "bilingual";

  return (
    <div className="relative h-full">
      <div
        ref={scrollRef}
        className="thin-scrollbar h-full overflow-y-auto"
        onMouseUp={onMouseUp}
      >
        <div
          className={cn(
            "mx-auto px-8 py-10",
            bilingual ? "max-w-6xl" : "max-w-3xl",
          )}
        >
          <PaperHeading />

          {bilingual && (
            <div className="sticky top-0 z-10 -mx-2 mb-4 grid grid-cols-2 gap-8 border-b bg-background/95 px-2 py-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground backdrop-blur">
              <span>English</span>
              <span>中文翻譯</span>
            </div>
          )}

          {paper.sections.map((section) => (
            <SectionBlock
              key={section.id}
              section={section}
              paragraphs={bySection.get(section.id) ?? []}
              readingMode={readingMode}
              hoveredParagraphId={hoveredParagraphId}
              setHoveredParagraphId={setHoveredParagraphId}
              flashParagraphId={flashParagraphId}
              highlightsByParagraph={highlightsByParagraph}
            />
          ))}
        </div>
      </div>
      <SelectionToolbar />
    </div>
  );
}

function PaperHeading() {
  const { paper } = useWorkspace();
  const doc = paper.document!;
  return (
    <div className="mb-8">
      <h1 className="paper-text text-2xl font-semibold leading-snug tracking-tight">
        {doc.title}
      </h1>
      {doc.authors.length > 0 && (
        <p className="mt-2 text-sm text-muted-foreground">{doc.authors.join(", ")}</p>
      )}
      {doc.affiliations.length > 0 && (
        <p className="mt-0.5 text-xs text-muted-foreground">{doc.affiliations.join(" · ")}</p>
      )}
      {(doc.venue || doc.year || doc.doi) && (
        <p className="mt-1 text-xs text-muted-foreground">
          {[doc.venue, doc.year, doc.doi].filter(Boolean).join(" · ")}
        </p>
      )}
    </div>
  );
}

function SectionBlock({
  section,
  paragraphs,
  readingMode,
  hoveredParagraphId,
  setHoveredParagraphId,
  flashParagraphId,
  highlightsByParagraph,
}: {
  section: Section;
  paragraphs: Paragraph[];
  readingMode: "english" | "chinese" | "bilingual";
  hoveredParagraphId: string | null;
  setHoveredParagraphId: (id: string | null) => void;
  flashParagraphId: string | null;
  highlightsByParagraph: Map<string, Highlight[]>;
}) {
  const bilingual = readingMode === "bilingual";
  return (
    <section data-section-id={section.id} className="mb-10 scroll-mt-16">
      <h2 className="paper-text mb-4 text-lg font-semibold">
        {section.sectionNumber && (
          <span className="mr-2 text-muted-foreground">{section.sectionNumber}</span>
        )}
        {section.title}
      </h2>
      <div className="space-y-4">
        {paragraphs
          .filter((p) => p.kind !== "heading")
          .map((p) => {
            const hovered = hoveredParagraphId === p.id;
            const flash = flashParagraphId === p.id;
            const highlights = highlightsByParagraph.get(p.id) ?? [];
            return (
              <div
                key={p.id}
                data-paragraph-id={p.id}
                data-section-id={p.sectionId}
                data-page={p.pageNumber}
                onMouseEnter={() => setHoveredParagraphId(p.id)}
                onMouseLeave={() => setHoveredParagraphId(null)}
                className={cn(
                  "group relative -mx-2 rounded-md px-2 py-1 transition-colors scroll-mt-20",
                  hovered && "bg-muted/60",
                  flash && "citation-flash",
                )}
              >
                <span
                  className="pointer-events-none absolute -left-10 top-1.5 hidden w-8 select-none text-right font-mono text-[10px] text-muted-foreground/60 group-hover:block lg:block"
                  title={`${p.id} · p.${p.pageNumber}`}
                >
                  {paragraphNumber(p.id)}
                </span>
                {bilingual ? (
                  <div className="grid grid-cols-2 gap-8">
                    <ParagraphText paragraph={p} lang="en" highlights={highlights} />
                    <ParagraphText paragraph={p} lang="zh" highlights={highlights} />
                  </div>
                ) : readingMode === "english" ? (
                  <ParagraphText paragraph={p} lang="en" highlights={highlights} />
                ) : (
                  <ParagraphText paragraph={p} lang="zh" highlights={highlights} />
                )}
              </div>
            );
          })}
      </div>
    </section>
  );
}
