"use client";

/* eslint-disable @next/next/no-img-element */
import { useWorkspace } from "@/components/workspace/workspace-context";
import { absoluteUrl } from "@/lib/api";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { useState } from "react";
import type { Figure } from "@/types";

export function FiguresPanel() {
  const { paper, jumpToParagraph, askAI } = useWorkspace();
  const [open, setOpen] = useState<Figure | null>(null);

  if (paper.figures.length === 0) {
    return <p className="px-4 py-6 text-xs text-muted-foreground">此論文沒有偵測到圖片。</p>;
  }

  return (
    <div className="space-y-3 px-3 py-3">
      {paper.figures.map((fig) => (
        <div key={fig.id} className="overflow-hidden rounded-lg border bg-card">
          <button
            type="button"
            className="block w-full bg-white"
            onClick={() => setOpen(fig)}
          >
            <img
              src={absoluteUrl(fig.imageUrl)}
              alt={fig.caption}
              className="max-h-40 w-full object-contain"
              loading="lazy"
            />
          </button>
          <div className="space-y-1 px-2.5 py-2">
            <p className="line-clamp-3 text-xs leading-snug">
              {fig.label && <span className="font-medium">{fig.label}. </span>}
              {fig.caption}
            </p>
            <div className="flex gap-2 text-[11px] text-muted-foreground">
              <span>Page {fig.pageNumber}</span>
              <button
                type="button"
                className="hover:text-foreground hover:underline"
                onClick={() =>
                  askAI({
                    message: `請解釋 ${fig.label ?? "這張圖"}：${fig.caption}`,
                    action: "explain",
                    selectedText: fig.caption,
                    context: "selected_text",
                  })
                }
              >
                Ask AI
              </button>
              {fig.sectionId && (
                <button
                  type="button"
                  className="hover:text-foreground hover:underline"
                  onClick={() => {
                    const p = paper.paragraphs.find((p) => p.sectionId === fig.sectionId);
                    if (p) jumpToParagraph(p.id);
                  }}
                >
                  Go to section
                </button>
              )}
            </div>
          </div>
        </div>
      ))}

      <Dialog open={!!open} onOpenChange={(v) => !v && setOpen(null)}>
        <DialogContent className="max-w-4xl">
          <DialogTitle className="text-sm">
            {open?.label ? `${open.label}. ` : ""}
            {open?.caption}
          </DialogTitle>
          {open && (
            <div className="rounded-md bg-white p-2">
              <img
                src={absoluteUrl(open.imageUrl)}
                alt={open.caption}
                className="mx-auto max-h-[70vh] object-contain"
              />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
