"use client";

/* eslint-disable @next/next/no-img-element */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Loader2Icon } from "lucide-react";
import { useWorkspace } from "@/components/workspace/workspace-context";
import { SelectionToolbar } from "./selection-toolbar";
import { absoluteUrl } from "@/lib/api";
import { cn, paragraphNumber } from "@/lib/utils";
import type { PageInfo, Paragraph, TextBox } from "@/types";

const BASE_PAGE_WIDTH = 640; // px at zoom 1

interface BoxRef {
  paragraph: Paragraph;
  box: TextBox;
  index: number; // index of the box within the paragraph
}

/**
 * Layout-preserving reader (SPEC §62): every page is shown as rendered by the
 * PDF engine — figures, tables and equations stay exactly where they are — and
 * the translated variant is the same page with each paragraph re-typeset in
 * Traditional Chinese. Transparent overlays on the paragraph boxes provide
 * hover sync, citation navigation and the AI toolbar.
 */
export function PageReader() {
  const {
    paper,
    readingMode,
    zoom,
    hoveredParagraphId,
    setHoveredParagraphId,
    flashParagraphId,
    setCurrentSectionId,
    setCurrentPage,
    setSelection,
  } = useWorkspace();
  const scrollRef = useRef<HTMLDivElement>(null);
  const doc = paper.document!;
  const layoutReady = doc.steps.find((s) => s.key === "layout")?.status === "done";

  const boxesByPage = useMemo(() => {
    const map = new Map<number, BoxRef[]>();
    for (const p of paper.paragraphs) {
      p.boxes.forEach((box, index) => {
        const list = map.get(box.page) ?? [];
        list.push({ paragraph: p, box, index });
        map.set(box.page, list);
      });
    }
    return map;
  }, [paper.paragraphs]);

  // Track the section / page at the top of the viewport (same contract as the text reader).
  const onScroll = useCallback(() => {
    const root = scrollRef.current;
    if (!root) return;
    const top = root.getBoundingClientRect().top + 120;
    const nodes = root.querySelectorAll<HTMLElement>("[data-paragraph-id][data-primary]");
    for (const node of nodes) {
      if (node.getBoundingClientRect().bottom >= top) {
        setCurrentSectionId(node.dataset.sectionId ?? null);
        setCurrentPage(Number(node.dataset.page ?? "1"));
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
  }, [onScroll, paper.pages.length]);

  // Clicking a paragraph box selects the whole paragraph for the AI toolbar.
  const selectParagraph = useCallback(
    (p: Paragraph, el: HTMLElement) => {
      const rect = el.getBoundingClientRect();
      setSelection({
        paragraphId: p.id,
        text: p.originalText,
        startOffset: 0,
        endOffset: p.originalText.length,
        rect: { top: rect.top, left: rect.left, width: rect.width, height: rect.height },
      });
    },
    [setSelection],
  );

  const showOriginal = readingMode !== "chinese";
  const showTranslated = readingMode !== "english";
  const pageWidth = Math.round(BASE_PAGE_WIDTH * zoom);

  if (paper.pages.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        <Loader2Icon className="mr-2 size-4 animate-spin" /> 載入頁面…
      </div>
    );
  }

  return (
    <div className="relative h-full">
      <div ref={scrollRef} className="thin-scrollbar h-full overflow-auto bg-muted/40">
        <div className="mx-auto w-max min-w-full px-6 py-6">
          {paper.pages.map((page) => (
            <div key={page.page} className="mb-6 flex justify-center gap-4">
              {showOriginal && (
                <PageCanvas
                  page={page}
                  src={absoluteUrl(page.originalUrl)}
                  width={pageWidth}
                  boxes={boxesByPage.get(page.page) ?? []}
                  primary
                  label={`p.${page.page} · English`}
                  hoveredParagraphId={hoveredParagraphId}
                  setHoveredParagraphId={setHoveredParagraphId}
                  flashParagraphId={flashParagraphId}
                  onSelectParagraph={selectParagraph}
                />
              )}
              {showTranslated && (
                <PageCanvas
                  page={page}
                  src={layoutReady ? `${absoluteUrl(page.translatedUrl)}&v=${doc.layoutVersion}` : null}
                  width={pageWidth}
                  boxes={boxesByPage.get(page.page) ?? []}
                  primary={!showOriginal}
                  label={`p.${page.page} · 中文`}
                  placeholder={layoutReady ? undefined : "翻譯版面產生中…"}
                  hoveredParagraphId={hoveredParagraphId}
                  setHoveredParagraphId={setHoveredParagraphId}
                  flashParagraphId={flashParagraphId}
                  onSelectParagraph={selectParagraph}
                />
              )}
            </div>
          ))}
        </div>
      </div>
      <SelectionToolbar />
    </div>
  );
}

function PageCanvas({
  page,
  src,
  width,
  boxes,
  primary,
  label,
  placeholder,
  hoveredParagraphId,
  setHoveredParagraphId,
  flashParagraphId,
  onSelectParagraph,
}: {
  page: PageInfo;
  src: string | null;
  width: number;
  boxes: BoxRef[];
  primary: boolean;
  label: string;
  placeholder?: string;
  hoveredParagraphId: string | null;
  setHoveredParagraphId: (id: string | null) => void;
  flashParagraphId: string | null;
  onSelectParagraph: (p: Paragraph, el: HTMLElement) => void;
}) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const height = Math.round((width * page.height) / page.width);

  return (
    <div className="shrink-0" style={{ width }}>
      <p className="mb-1 px-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <div
        className="relative overflow-hidden rounded-sm bg-white shadow-sm ring-1 ring-black/10"
        style={{ width, height }}
      >
        {src && !failed && (
          <img
            src={src}
            alt={label}
            width={width}
            height={height}
            loading="lazy"
            decoding="async"
            draggable={false}
            onLoad={() => setLoaded(true)}
            onError={() => setFailed(true)}
            className={cn("block h-full w-full select-none transition-opacity", loaded ? "opacity-100" : "opacity-0")}
          />
        )}
        {(!src || failed || !loaded) && (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-neutral-400">
            {placeholder ?? (failed ? "尚未產生" : <Loader2Icon className="size-4 animate-spin" />)}
          </div>
        )}
        {boxes.map(({ paragraph, box, index }) => {
          const hovered = hoveredParagraphId === paragraph.id;
          const flash = flashParagraphId === paragraph.id;
          return (
            <div
              key={`${paragraph.id}-${index}`}
              data-paragraph-id={index === 0 && primary ? paragraph.id : undefined}
              data-primary={index === 0 && primary ? "" : undefined}
              data-section-id={paragraph.sectionId}
              data-page={box.page}
              title={`¶${paragraphNumber(paragraph.id)}`}
              onMouseEnter={() => setHoveredParagraphId(paragraph.id)}
              onMouseLeave={() => setHoveredParagraphId(null)}
              onClick={(e) => onSelectParagraph(paragraph, e.currentTarget)}
              className={cn(
                "absolute cursor-pointer rounded-[2px] transition-colors",
                hovered && "bg-sky-400/15 ring-1 ring-sky-400/60",
                flash && "citation-flash-overlay",
              )}
              style={{
                left: `${(box.x / page.width) * 100}%`,
                top: `${(box.y / page.height) * 100}%`,
                width: `${(box.width / page.width) * 100}%`,
                height: `${(box.height / page.height) * 100}%`,
              }}
            />
          );
        })}
      </div>
    </div>
  );
}
