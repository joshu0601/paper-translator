"use client";

import Link from "next/link";
import {
  BookOpenIcon,
  DownloadIcon,
  LanguagesIcon,
  PanelLeftIcon,
  PanelRightIcon,
  SearchIcon,
  Loader2Icon,
} from "lucide-react";
import { useWorkspace } from "./workspace-context";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { fileUrl } from "@/lib/api";
import type { ReadingMode } from "@/types";
import { cn } from "@/lib/utils";

const READING_MODES: { value: ReadingMode; label: string }[] = [
  { value: "english", label: "English" },
  { value: "chinese", label: "中文" },
  { value: "bilingual", label: "中英對照" },
];

export function WorkspaceHeader() {
  const {
    paper,
    readingMode,
    setReadingMode,
    sidebarOpen,
    setSidebarOpen,
    aiPanelOpen,
    setAiPanelOpen,
    setSearchOpen,
  } = useWorkspace();
  const doc = paper.document!;
  const translating =
    doc.steps.find((s) => s.key === "translate")?.status === "running";

  const exportMarkdown = () => {
    const lines: string[] = [`# ${doc.title}`, ""];
    if (doc.authors.length) lines.push(doc.authors.join(", "), "");
    for (const section of paper.sections) {
      lines.push(`## ${section.sectionNumber ? `${section.sectionNumber} ` : ""}${section.title}`, "");
      for (const p of paper.paragraphs.filter((p) => p.sectionId === section.id)) {
        if (p.kind === "heading") continue;
        if (readingMode !== "chinese") lines.push(p.originalText, "");
        if (readingMode !== "english" && p.translatedText) lines.push(p.translatedText, "");
      }
    }
    const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(doc.title || doc.fileName).replace(/[\\/:*?"<>|]+/g, "_")}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <header className="flex h-12 shrink-0 items-center gap-2 border-b px-3">
      <Link href="/" className="flex items-center gap-1.5 text-sm font-semibold">
        <BookOpenIcon className="size-4" />
        <span className="hidden sm:inline">PaperAI</span>
      </Link>

      <Tooltip>
        <TooltipTrigger
          render={
            <Button
              variant="ghost"
              size="icon-sm"
              className="hidden md:inline-flex"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              aria-label="Toggle outline"
            />
          }
        >
          <PanelLeftIcon />
        </TooltipTrigger>
        <TooltipContent>大綱側欄</TooltipContent>
      </Tooltip>

      <div className="min-w-0 flex-1 px-2">
        <p className="truncate text-sm font-medium" title={doc.title}>
          {doc.title || doc.fileName}
        </p>
      </div>

      <Button
        variant="outline"
        size="sm"
        className="hidden text-muted-foreground sm:inline-flex"
        onClick={() => setSearchOpen(true)}
      >
        <SearchIcon />
        <span className="hidden lg:inline">Search</span>
        <kbd className="ml-1 hidden rounded border px-1 font-mono text-[10px] lg:inline">
          ⌘K
        </kbd>
      </Button>

      <div className="hidden items-center rounded-lg border p-0.5 sm:flex">
        {READING_MODES.map((m) => (
          <button
            key={m.value}
            type="button"
            onClick={() => setReadingMode(m.value)}
            className={cn(
              "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
              readingMode === m.value
                ? "bg-foreground text-background"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {m.label}
          </button>
        ))}
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger
          render={<Button variant="ghost" size="icon-sm" aria-label="Translation" />}
        >
          {translating ? <Loader2Icon className="animate-spin" /> : <LanguagesIcon />}
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>Translation</DropdownMenuLabel>
          <DropdownMenuItem
            disabled={translating || doc.status !== "ready"}
            onClick={() => paper.retranslate()}
          >
            重新翻譯整篇論文
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <DropdownMenu>
        <DropdownMenuTrigger
          render={<Button variant="ghost" size="icon-sm" aria-label="Export" />}
        >
          <DownloadIcon />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>Export</DropdownMenuLabel>
          <DropdownMenuItem onClick={exportMarkdown}>匯出 Markdown</DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            render={<a href={fileUrl(doc.id)} target="_blank" rel="noreferrer" />}
          >
            開啟原始 PDF
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <ThemeToggle />

      <Tooltip>
        <TooltipTrigger
          render={
            <Button
              variant="ghost"
              size="icon-sm"
              className="hidden md:inline-flex"
              onClick={() => setAiPanelOpen(!aiPanelOpen)}
              aria-label="Toggle AI panel"
            />
          }
        >
          <PanelRightIcon />
        </TooltipTrigger>
        <TooltipContent>AI 助理</TooltipContent>
      </Tooltip>
    </header>
  );
}
