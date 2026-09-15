"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2Icon, SearchIcon } from "lucide-react";
import { useWorkspace } from "@/components/workspace/workspace-context";
import { api } from "@/lib/api";
import type { SearchResult } from "@/types";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { cn, paragraphNumber } from "@/lib/utils";

type Mode = "exact" | "semantic";

/** ⌘K search over the paper: exact text match or embedding search (SPEC §42). */
export function SearchDialog() {
  const { searchOpen, setSearchOpen, paper, jumpToParagraph } = useWorkspace();
  const [mode, setMode] = useState<Mode>("exact");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [busy, setBusy] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setSearchOpen]);

  const trimmed = query.trim();
  const documentId = paper.document?.id;

  useEffect(() => {
    if (!searchOpen || !trimmed || !documentId) return;
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      setBusy(true);
      try {
        setResults(await api.search(documentId, trimmed, mode));
      } catch {
        setResults([]);
      } finally {
        setBusy(false);
      }
    }, mode === "exact" ? 150 : 400);
    return () => timer.current && clearTimeout(timer.current);
  }, [trimmed, mode, searchOpen, documentId]);

  const shown = trimmed ? results : null;

  const pick = (r: SearchResult) => {
    setSearchOpen(false);
    // Let the dialog close before scrolling.
    setTimeout(() => jumpToParagraph(r.paragraphId), 50);
  };

  return (
    <Dialog open={searchOpen} onOpenChange={setSearchOpen}>
      <DialogContent className="top-[15%] translate-y-0 gap-0 p-0 sm:max-w-xl">
        <DialogTitle className="sr-only">Search paper</DialogTitle>
        <div className="flex items-center gap-2 border-b px-3">
          {busy ? (
            <Loader2Icon className="size-4 animate-spin text-muted-foreground" />
          ) : (
            <SearchIcon className="size-4 text-muted-foreground" />
          )}
          <Input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={
              mode === "exact" ? "搜尋論文原文，例如 reward function" : "語意搜尋，例如 作者在哪裡說明如何設計 reward？"
            }
            className="h-11 border-0 bg-transparent px-0 shadow-none focus-visible:ring-0"
          />
          <div className="flex shrink-0 rounded-md border p-0.5">
            {(["exact", "semantic"] as Mode[]).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                className={cn(
                  "rounded px-2 py-0.5 text-[11px] font-medium",
                  mode === m ? "bg-foreground text-background" : "text-muted-foreground",
                )}
              >
                {m === "exact" ? "Exact" : "Semantic"}
              </button>
            ))}
          </div>
        </div>
        <div className="thin-scrollbar max-h-[60vh] overflow-y-auto p-2">
          {shown === null ? (
            <p className="px-2 py-6 text-center text-xs text-muted-foreground">
              輸入關鍵字或問題開始搜尋
            </p>
          ) : shown.length === 0 ? (
            <p className="px-2 py-6 text-center text-xs text-muted-foreground">沒有結果</p>
          ) : (
            <ul className="space-y-0.5">
              {shown.map((r) => (
                <li key={r.paragraphId}>
                  <button
                    type="button"
                    onClick={() => pick(r)}
                    className="w-full rounded-md px-2.5 py-2 text-left hover:bg-muted"
                  >
                    <p className="mb-0.5 text-[11px] text-muted-foreground">
                      {r.sectionTitle} · Page {r.page} · ¶{paragraphNumber(r.paragraphId)}
                      {typeof r.score === "number" && (
                        <span className="ml-2 font-mono opacity-60">
                          {(r.score * 100).toFixed(0)}%
                        </span>
                      )}
                    </p>
                    <p className="paper-text line-clamp-2 text-[13px] leading-snug">
                      <Preview text={r.preview} query={mode === "exact" ? query : ""} />
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function Preview({ text, query }: { text: string; query: string }) {
  if (!query.trim()) return <>{text}</>;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-highlight-strong text-foreground">
        {text.slice(idx, idx + query.length)}
      </mark>
      {text.slice(idx + query.length)}
    </>
  );
}
