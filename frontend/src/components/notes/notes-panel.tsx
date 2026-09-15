"use client";

import { Trash2Icon } from "lucide-react";
import { useWorkspace } from "@/components/workspace/workspace-context";
import { Button } from "@/components/ui/button";
import { formatDate, paragraphNumber } from "@/lib/utils";

export function NotesPanel() {
  const { paper, jumpToParagraph } = useWorkspace();

  return (
    <div className="px-3 py-3">
      {paper.highlights.length > 0 && (
        <div className="mb-4">
          <p className="mb-1.5 px-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Highlights · {paper.highlights.length}
          </p>
          <ul className="space-y-1">
            {paper.highlights.map((h) => (
              <li key={h.id} className="group flex items-start gap-1">
                <button
                  type="button"
                  onClick={() => jumpToParagraph(h.paragraphId)}
                  className="min-w-0 flex-1 rounded-md px-2 py-1.5 text-left text-xs hover:bg-muted/60"
                >
                  <span className="line-clamp-2 bg-highlight">{h.selectedText}</span>
                  <span className="mt-0.5 block text-[10px] text-muted-foreground">
                    Paragraph {paragraphNumber(h.paragraphId)}
                  </span>
                </button>
                <Button
                  variant="ghost"
                  size="icon-xs"
                  className="opacity-0 group-hover:opacity-100"
                  aria-label="刪除 highlight"
                  onClick={() => paper.removeHighlight(h.id)}
                >
                  <Trash2Icon />
                </Button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="mb-1.5 px-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        Notes · {paper.notes.length}
      </p>
      {paper.notes.length === 0 ? (
        <p className="px-1 py-2 text-xs text-muted-foreground">
          選取文字後點「Add Note」即可建立筆記。
        </p>
      ) : (
        <ul className="space-y-2">
          {paper.notes.map((n) => (
            <li key={n.id} className="group rounded-lg border bg-card p-2.5">
              {n.selectedText && (
                <button
                  type="button"
                  onClick={() => jumpToParagraph(n.paragraphId)}
                  className="mb-1.5 block w-full border-l-2 pl-2 text-left text-[11px] leading-snug text-muted-foreground hover:text-foreground"
                >
                  <span className="line-clamp-2 italic">“{n.selectedText}”</span>
                </button>
              )}
              <p className="whitespace-pre-wrap text-xs leading-relaxed">{n.content}</p>
              <div className="mt-1.5 flex items-center justify-between text-[10px] text-muted-foreground">
                <button
                  type="button"
                  className="hover:underline"
                  onClick={() => jumpToParagraph(n.paragraphId)}
                >
                  Paragraph {paragraphNumber(n.paragraphId)} · {formatDate(n.createdAt)}
                </button>
                <Button
                  variant="ghost"
                  size="icon-xs"
                  className="opacity-0 group-hover:opacity-100"
                  aria-label="刪除筆記"
                  onClick={() => paper.removeNote(n.id)}
                >
                  <Trash2Icon />
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
