"use client";

import { ImageIcon, ListIcon, StickyNoteIcon, TableIcon } from "lucide-react";
import { useWorkspace, type SidebarTab } from "@/components/workspace/workspace-context";
import { ScrollArea } from "@/components/ui/scroll-area";
import { OutlinePanel } from "./outline-panel";
import { FiguresPanel } from "./figures-panel";
import { TablesPanel } from "./tables-panel";
import { NotesPanel } from "@/components/notes/notes-panel";
import { cn } from "@/lib/utils";

const TABS: { value: SidebarTab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { value: "outline", label: "Paper", icon: ListIcon },
  { value: "figures", label: "Figures", icon: ImageIcon },
  { value: "tables", label: "Tables", icon: TableIcon },
  { value: "notes", label: "Notes", icon: StickyNoteIcon },
];

export function PaperSidebar() {
  const { sidebarTab, setSidebarTab, paper } = useWorkspace();
  const counts: Record<SidebarTab, number | null> = {
    outline: null,
    figures: paper.figures.length,
    tables: paper.tables.length,
    notes: paper.notes.length,
  };

  return (
    <div className="flex h-full w-64 flex-col">
      <div className="flex shrink-0 items-center gap-0.5 border-b px-2 py-1.5">
        {TABS.map((t) => (
          <button
            key={t.value}
            type="button"
            onClick={() => setSidebarTab(t.value)}
            title={t.label}
            className={cn(
              "flex flex-1 items-center justify-center gap-1 rounded-md px-1.5 py-1 text-xs transition-colors",
              sidebarTab === t.value
                ? "bg-muted text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <t.icon className="size-3.5" />
            {counts[t.value] !== null && counts[t.value]! > 0 && (
              <span className="tabular-nums">{counts[t.value]}</span>
            )}
          </button>
        ))}
      </div>
      <ScrollArea className="min-h-0 flex-1">
        {sidebarTab === "outline" && <OutlinePanel />}
        {sidebarTab === "figures" && <FiguresPanel />}
        {sidebarTab === "tables" && <TablesPanel />}
        {sidebarTab === "notes" && <NotesPanel />}
      </ScrollArea>
    </div>
  );
}
