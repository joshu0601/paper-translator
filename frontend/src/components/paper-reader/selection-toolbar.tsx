"use client";

import { useEffect, useState } from "react";
import {
  HighlighterIcon,
  LanguagesIcon,
  LightbulbIcon,
  ListIcon,
  MessageSquareIcon,
  StickyNoteIcon,
} from "lucide-react";
import { useWorkspace } from "@/components/workspace/workspace-context";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogTitle,
} from "@/components/ui/dialog";

/** Floating toolbar shown over a text selection (SPEC §31). */
export function SelectionToolbar() {
  const { selection, setSelection, askAI, paper } = useWorkspace();
  const [noteOpen, setNoteOpen] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [pendingNote, setPendingNote] = useState<{ paragraphId: string; text: string } | null>(null);

  // Clear when the user clicks elsewhere or presses Escape.
  useEffect(() => {
    if (!selection) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setSelection(null);
    const onDown = (e: MouseEvent) => {
      if ((e.target as HTMLElement).closest("[data-selection-toolbar]")) return;
      const sel = window.getSelection();
      if (sel && !sel.isCollapsed) return; // a new selection will replace it
      setSelection(null);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onDown);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onDown);
    };
  }, [selection, setSelection]);

  const submitNote = async () => {
    if (!pendingNote || !noteText.trim()) return;
    await paper.addNote({
      paragraphId: pendingNote.paragraphId,
      selectedText: pendingNote.text,
      content: noteText.trim(),
    });
    setNoteText("");
    setNoteOpen(false);
    setPendingNote(null);
  };

  const run = (
    action: "explain" | "translate" | "summarize" | "ask",
    message: string,
  ) => {
    if (!selection) return;
    askAI({ message, action, selectedText: selection.text, context: "selected_text" });
    window.getSelection()?.removeAllRanges();
    setSelection(null);
  };

  const toolbar = selection && (
    <div
      data-selection-toolbar
      className="fixed z-40 flex items-center gap-0.5 rounded-lg border bg-popover p-1 text-popover-foreground shadow-md"
      style={{
        top: Math.max(8, selection.rect.top - 44),
        left: Math.min(
          Math.max(8, selection.rect.left + selection.rect.width / 2 - 190),
          window.innerWidth - 390,
        ),
      }}
    >
      <ToolbarButton
        icon={LightbulbIcon}
        label="Explain"
        onClick={() => run("explain", "請解釋這段文字的意思，並連結到論文的脈絡。")}
      />
      <ToolbarButton
        icon={LanguagesIcon}
        label="Translate"
        onClick={() => run("translate", "請將這段文字翻譯成繁體中文。")}
      />
      <ToolbarButton
        icon={ListIcon}
        label="Summary"
        onClick={() => run("summarize", "請摘要這段文字的重點。")}
      />
      <ToolbarButton
        icon={MessageSquareIcon}
        label="Ask AI"
        onClick={() => {
          if (!selection) return;
          askAI({ message: "", action: "ask", selectedText: selection.text, context: "selected_text" });
          setSelection(null);
        }}
      />
      <span className="mx-0.5 h-5 w-px bg-border" />
      <ToolbarButton
        icon={HighlighterIcon}
        label="Highlight"
        onClick={async () => {
          if (!selection) return;
          await paper.addHighlight({
            paragraphId: selection.paragraphId,
            selectedText: selection.text,
            startOffset: selection.startOffset,
            endOffset: selection.endOffset,
          });
          window.getSelection()?.removeAllRanges();
          setSelection(null);
        }}
      />
      <ToolbarButton
        icon={StickyNoteIcon}
        label="Add Note"
        onClick={() => {
          if (!selection) return;
          setPendingNote({ paragraphId: selection.paragraphId, text: selection.text });
          setNoteOpen(true);
          setSelection(null);
        }}
      />
    </div>
  );

  return (
    <>
      {toolbar}
      <Dialog open={noteOpen} onOpenChange={setNoteOpen}>
        <DialogContent>
          <DialogTitle>新增筆記</DialogTitle>
          <DialogDescription className="line-clamp-3 border-l-2 pl-2 italic">
            “{pendingNote?.text}”
          </DialogDescription>
          <Textarea
            autoFocus
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="寫下你的想法…"
            rows={5}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setNoteOpen(false)}>
              取消
            </Button>
            <Button onClick={submitNote} disabled={!noteText.trim()}>
              儲存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

function ToolbarButton({
  icon: Icon,
  label,
  onClick,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onMouseDown={(e) => e.preventDefault()}
      onClick={onClick}
      className="flex items-center gap-1 rounded-md px-2 py-1 text-xs hover:bg-muted"
    >
      <Icon className="size-3.5" />
      {label}
    </button>
  );
}
