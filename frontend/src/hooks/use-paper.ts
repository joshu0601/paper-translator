"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type {
  Figure,
  Highlight,
  Note,
  PaperDocument,
  PaperTable,
  Paragraph,
  Section,
} from "@/types";

export interface PaperData {
  document: PaperDocument | null;
  sections: Section[];
  paragraphs: Paragraph[];
  figures: Figure[];
  tables: PaperTable[];
  notes: Note[];
  highlights: Highlight[];
}

const POLL_INTERVAL_MS = 1500;

/**
 * Loads a document and keeps polling while it is still processing.
 * Sections / paragraphs are (re)loaded whenever the document becomes ready or
 * the translation step finishes, so the reader fills in progressively.
 */
export function usePaper(documentId: string) {
  const [data, setData] = useState<PaperData>({
    document: null,
    sections: [],
    paragraphs: [],
    figures: [],
    tables: [],
    notes: [],
    highlights: [],
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  // Bumped to restart the polling loop after an action re-enters "processing".
  const [pollNonce, setPollNonce] = useState(0);
  const lastContentKey = useRef<string>("");

  const loadContent = useCallback(async () => {
    const [sections, paragraphs, figures, tables] = await Promise.all([
      api.getSections(documentId),
      api.getParagraphs(documentId),
      api.getFigures(documentId),
      api.getTables(documentId),
    ]);
    setData((d) => ({ ...d, sections, paragraphs, figures, tables }));
  }, [documentId]);

  const loadAnnotations = useCallback(async () => {
    const [notes, highlights] = await Promise.all([
      api.getNotes(documentId),
      api.getHighlights(documentId),
    ]);
    setData((d) => ({ ...d, notes, highlights }));
  }, [documentId]);

  const refreshDocument = useCallback(async () => {
    const document = await api.getDocument(documentId);
    setData((d) => ({ ...d, document }));
    return document;
  }, [documentId]);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const tick = async () => {
      try {
        const document = await api.getDocument(documentId);
        if (cancelled) return;
        setData((d) => ({ ...d, document }));
        setError(null);

        // Reload paragraphs when parsing is done, and again after translation.
        const parsed = document.steps.find((s) => s.key === "parse");
        const translated = document.steps.find((s) => s.key === "translate");
        const key = `${parsed?.status}-${translated?.status}-${document.status}`;
        if (
          (parsed?.status === "done" || document.status === "ready") &&
          key !== lastContentKey.current
        ) {
          lastContentKey.current = key;
          await loadContent();
          await loadAnnotations();
        }
        setLoading(false);

        if (document.status === "processing" || document.status === "uploaded") {
          timer = setTimeout(tick, POLL_INTERVAL_MS);
        }
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof ApiError ? e.message : String(e));
        setLoading(false);
      }
    };
    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [documentId, loadContent, loadAnnotations, pollNonce]);

  const addNote = useCallback(
    async (body: { paragraphId: string; content: string; selectedText?: string }) => {
      const note = await api.createNote(documentId, body);
      setData((d) => ({ ...d, notes: [note, ...d.notes] }));
      return note;
    },
    [documentId],
  );

  const removeNote = useCallback(async (noteId: string) => {
    await api.deleteNote(noteId);
    setData((d) => ({ ...d, notes: d.notes.filter((n) => n.id !== noteId) }));
  }, []);

  const addHighlight = useCallback(
    async (body: {
      paragraphId: string;
      selectedText: string;
      startOffset: number;
      endOffset: number;
    }) => {
      const highlight = await api.createHighlight(documentId, body);
      setData((d) => ({ ...d, highlights: [...d.highlights, highlight] }));
      return highlight;
    },
    [documentId],
  );

  const removeHighlight = useCallback(async (highlightId: string) => {
    await api.deleteHighlight(highlightId);
    setData((d) => ({
      ...d,
      highlights: d.highlights.filter((h) => h.id !== highlightId),
    }));
  }, []);

  const retranslate = useCallback(async () => {
    const document = await api.translate(documentId);
    lastContentKey.current = "";
    setData((d) => ({ ...d, document }));
    setPollNonce((n) => n + 1);
  }, [documentId]);

  const reprocess = useCallback(async () => {
    const document = await api.reprocess(documentId);
    lastContentKey.current = "";
    setData((d) => ({ ...d, document, sections: [], paragraphs: [] }));
    setPollNonce((n) => n + 1);
  }, [documentId]);

  return {
    ...data,
    loading,
    error,
    refreshDocument,
    reloadContent: loadContent,
    addNote,
    removeNote,
    addHighlight,
    removeHighlight,
    retranslate,
    reprocess,
  };
}

export type PaperState = ReturnType<typeof usePaper>;
