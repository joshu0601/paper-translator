"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { PaperState } from "@/hooks/use-paper";
import type {
  ChatAction,
  ContextMode,
  ExplanationLevel,
  LayoutMode,
  ReadingMode,
} from "@/types";

function readPref<T extends string>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    return (window.localStorage.getItem(key) as T | null) ?? fallback;
  } catch {
    return fallback;
  }
}

function writePref(key: string, value: string) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* private mode etc. */
  }
}

export interface TextSelection {
  paragraphId: string;
  text: string;
  startOffset: number;
  endOffset: number;
  /** viewport rect of the selection, used to place the floating toolbar */
  rect: { top: number; left: number; width: number; height: number };
}

export interface AskAIRequest {
  message: string;
  action?: ChatAction;
  selectedText?: string;
  context?: ContextMode;
}

export type SidebarTab = "outline" | "figures" | "tables" | "notes";

interface WorkspaceContextValue {
  paper: PaperState;
  readingMode: ReadingMode;
  setReadingMode: (m: ReadingMode) => void;
  layoutMode: LayoutMode;
  setLayoutMode: (m: LayoutMode) => void;
  zoom: number;
  setZoom: (z: number) => void;
  sidebarOpen: boolean;
  setSidebarOpen: (v: boolean) => void;
  sidebarTab: SidebarTab;
  setSidebarTab: (t: SidebarTab) => void;
  aiPanelOpen: boolean;
  setAiPanelOpen: (v: boolean) => void;
  currentSectionId: string | null;
  setCurrentSectionId: (id: string | null) => void;
  currentPage: number;
  setCurrentPage: (p: number) => void;
  hoveredParagraphId: string | null;
  setHoveredParagraphId: (id: string | null) => void;
  flashParagraphId: string | null;
  jumpToParagraph: (paragraphId: string) => void;
  jumpToSection: (sectionId: string) => void;
  selection: TextSelection | null;
  setSelection: (s: TextSelection | null) => void;
  contextMode: ContextMode;
  setContextMode: (m: ContextMode) => void;
  level: ExplanationLevel;
  setLevel: (l: ExplanationLevel) => void;
  askAI: (req: AskAIRequest) => void;
  registerAskHandler: (fn: (req: AskAIRequest) => void) => () => void;
  searchOpen: boolean;
  setSearchOpen: (v: boolean) => void;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({
  paper,
  children,
}: {
  paper: PaperState;
  children: ReactNode;
}) {
  const [readingMode, setReadingMode] = useState<ReadingMode>("bilingual");
  // Layout preference is remembered per browser (defaults to the original PDF layout).
  const [layoutMode, setLayoutModeState] = useState<LayoutMode>(() => readPref("paperai.layout", "page"));
  const [zoom, setZoomState] = useState<number>(() => Number(readPref("paperai.zoom", "1")) || 1);
  const setLayoutMode = useCallback((m: LayoutMode) => {
    setLayoutModeState(m);
    writePref("paperai.layout", m);
  }, []);
  const setZoom = useCallback((z: number) => {
    const clamped = Math.min(2, Math.max(0.5, Math.round(z * 100) / 100));
    setZoomState(clamped);
    writePref("paperai.zoom", String(clamped));
  }, []);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sidebarTab, setSidebarTab] = useState<SidebarTab>("outline");
  const [aiPanelOpen, setAiPanelOpen] = useState(true);
  const [currentSectionId, setCurrentSectionId] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [hoveredParagraphId, setHoveredParagraphId] = useState<string | null>(null);
  const [flashParagraphId, setFlashParagraphId] = useState<string | null>(null);
  const [selection, setSelection] = useState<TextSelection | null>(null);
  const [contextMode, setContextMode] = useState<ContextMode>("entire_document");
  const [level, setLevel] = useState<ExplanationLevel>("graduate");
  const [searchOpen, setSearchOpen] = useState(false);
  const askHandler = useRef<((req: AskAIRequest) => void) | null>(null);
  const flashTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const jumpToParagraph = useCallback((paragraphId: string) => {
    const el = document.querySelector<HTMLElement>(
      `[data-paragraph-id="${paragraphId}"]`,
    );
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    // Restart the flash animation even when the same paragraph is targeted twice.
    setFlashParagraphId(null);
    if (flashTimer.current) clearTimeout(flashTimer.current);
    requestAnimationFrame(() => setFlashParagraphId(paragraphId));
    flashTimer.current = setTimeout(() => setFlashParagraphId(null), 4000);
  }, []);

  const jumpToSection = useCallback((sectionId: string) => {
    const el = document.querySelector<HTMLElement>(
      `[data-section-id="${sectionId}"]`,
    );
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
    setCurrentSectionId(sectionId);
  }, []);

  const askAI = useCallback((req: AskAIRequest) => {
    setAiPanelOpen(true);
    askHandler.current?.(req);
  }, []);

  const registerAskHandler = useCallback((fn: (req: AskAIRequest) => void) => {
    askHandler.current = fn;
    return () => {
      if (askHandler.current === fn) askHandler.current = null;
    };
  }, []);

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      paper,
      readingMode,
      setReadingMode,
      layoutMode,
      setLayoutMode,
      zoom,
      setZoom,
      sidebarOpen,
      setSidebarOpen,
      sidebarTab,
      setSidebarTab,
      aiPanelOpen,
      setAiPanelOpen,
      currentSectionId,
      setCurrentSectionId,
      currentPage,
      setCurrentPage,
      hoveredParagraphId,
      setHoveredParagraphId,
      flashParagraphId,
      jumpToParagraph,
      jumpToSection,
      selection,
      setSelection,
      contextMode,
      setContextMode,
      level,
      setLevel,
      askAI,
      registerAskHandler,
      searchOpen,
      setSearchOpen,
    }),
    [
      paper,
      readingMode,
      layoutMode,
      setLayoutMode,
      zoom,
      setZoom,
      sidebarOpen,
      sidebarTab,
      aiPanelOpen,
      currentSectionId,
      currentPage,
      hoveredParagraphId,
      flashParagraphId,
      jumpToParagraph,
      jumpToSection,
      selection,
      contextMode,
      level,
      askAI,
      registerAskHandler,
      searchOpen,
    ],
  );

  return (
    <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return ctx;
}
