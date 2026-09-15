"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { SendIcon, SparklesIcon, Trash2Icon, XIcon } from "lucide-react";
import { useWorkspace, type AskAIRequest } from "@/components/workspace/workspace-context";
import { api, ApiError } from "@/lib/api";
import type { ChatMessage, ContextMode, ExplanationLevel } from "@/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ChatMessageView } from "./chat-message";
import { QuickActions } from "./quick-actions";

const CONTEXT_OPTIONS: { value: ContextMode; label: string }[] = [
  { value: "entire_document", label: "Entire Paper" },
  { value: "current_section", label: "Current Section" },
  { value: "current_page", label: "Current Page" },
  { value: "selected_text", label: "Selected Text" },
];

const LEVEL_OPTIONS: { value: ExplanationLevel; label: string }[] = [
  { value: "beginner", label: "Beginner" },
  { value: "undergraduate", label: "Undergraduate" },
  { value: "graduate", label: "Graduate Student" },
  { value: "researcher", label: "Researcher" },
];

export function AIPanel() {
  const {
    paper,
    contextMode,
    setContextMode,
    level,
    setLevel,
    currentSectionId,
    currentPage,
    registerAskHandler,
    setAiPanelOpen,
  } = useWorkspace();
  const doc = paper.document!;
  const ready = doc.status === "ready";

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [pendingSelection, setPendingSelection] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const sessionId = useRef<string | undefined>(undefined);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const currentSection = paper.sections.find((s) => s.id === currentSectionId);

  const send = useCallback(
    async (req: AskAIRequest) => {
      const message = req.message.trim();
      if (!message || sending) return;
      const ctx = req.context ?? contextMode;
      const selectedText = req.selectedText ?? pendingSelection ?? undefined;
      const userMsg: ChatMessage = {
        id: `u-${Date.now()}`,
        role: "user",
        content: selectedText ? `${message}\n\n> ${selectedText}` : message,
        createdAt: new Date().toISOString(),
      };
      const placeholder: ChatMessage = {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: "",
        createdAt: new Date().toISOString(),
        pending: true,
      };
      setMessages((m) => [...m, userMsg, placeholder]);
      setInput("");
      setPendingSelection(null);
      setSending(true);
      try {
        const res = await api.chat(doc.id, {
          message,
          context: selectedText && ctx !== "selected_text" ? "selected_text" : ctx,
          sectionId: currentSectionId ?? undefined,
          page: currentPage,
          selectedText,
          level,
          action: req.action ?? "ask",
          sessionId: sessionId.current,
        });
        sessionId.current = res.sessionId;
        setMessages((m) =>
          m.map((msg) =>
            msg.id === placeholder.id
              ? {
                  id: res.messageId,
                  role: "assistant",
                  content: res.answer,
                  citations: res.citations,
                  createdAt: new Date().toISOString(),
                }
              : msg,
          ),
        );
      } catch (e) {
        const detail = e instanceof ApiError ? e.message : String(e);
        setMessages((m) =>
          m.map((msg) =>
            msg.id === placeholder.id
              ? { ...msg, pending: false, error: true, content: `發生錯誤：${detail}` }
              : msg,
          ),
        );
      } finally {
        setSending(false);
      }
    },
    [contextMode, currentPage, currentSectionId, doc.id, level, pendingSelection, sending],
  );

  // Requests coming from the reader (selection toolbar, figures, ...).
  useEffect(
    () =>
      registerAskHandler((req) => {
        if (req.message) {
          send(req);
        } else {
          setPendingSelection(req.selectedText ?? null);
          if (req.context) setContextMode(req.context);
          inputRef.current?.focus();
        }
      }),
    [registerAskHandler, send, setContextMode],
  );

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      send({ message: input });
    }
  };

  return (
    <div className="flex h-full w-full flex-col md:w-[380px] xl:w-[420px]">
      <div className="flex shrink-0 items-center justify-between border-b px-4 py-2.5">
        <div className="flex items-center gap-1.5 text-sm font-medium">
          <SparklesIcon className="size-4" />
          AI Assistant
        </div>
        <div className="flex items-center gap-0.5">
          {messages.length > 0 && (
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="清除對話"
              onClick={() => {
                setMessages([]);
                sessionId.current = undefined;
              }}
            >
              <Trash2Icon />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon-sm"
            className="hidden md:inline-flex"
            aria-label="關閉"
            onClick={() => setAiPanelOpen(false)}
          >
            <XIcon />
          </Button>
        </div>
      </div>

      <div className="shrink-0 space-y-2 border-b px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span className="w-14 text-[11px] text-muted-foreground">Context</span>
          <Select
            value={contextMode}
            onValueChange={(v) => v && setContextMode(v as ContextMode)}
            items={CONTEXT_OPTIONS}
          >
            <SelectTrigger size="sm" className="h-7 flex-1 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {CONTEXT_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-14 text-[11px] text-muted-foreground">Level</span>
          <Select
            value={level}
            onValueChange={(v) => v && setLevel(v as ExplanationLevel)}
            items={LEVEL_OPTIONS}
          >
            <SelectTrigger size="sm" className="h-7 flex-1 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LEVEL_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {contextMode === "current_section" && currentSection && (
          <p className="truncate pl-16 text-[11px] text-muted-foreground">
            {currentSection.sectionNumber ? `Section ${currentSection.sectionNumber} · ` : ""}
            {currentSection.title}
          </p>
        )}
        {contextMode === "current_page" && (
          <p className="pl-16 text-[11px] text-muted-foreground">Page {currentPage}</p>
        )}
      </div>

      <div ref={listRef} className="thin-scrollbar min-h-0 flex-1 overflow-y-auto px-4 py-3">
        {messages.length === 0 ? (
          <div className="space-y-4">
            <p className="text-xs leading-relaxed text-muted-foreground">
              問我關於這篇論文的任何問題。回答會附上可點擊的來源段落，點擊即可跳到原文。
            </p>
            {!ready && (
              <p className="rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
                AI 索引建立完成後即可提問。
              </p>
            )}
            <div>
              <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                Quick Actions
              </p>
              <QuickActions onPick={(m) => send({ message: m })} />
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((m) => (
              <ChatMessageView key={m.id} message={m} />
            ))}
          </div>
        )}
      </div>

      {messages.length > 0 && (
        <div className="shrink-0 border-t px-4 py-2">
          <QuickActions compact onPick={(m) => send({ message: m })} />
        </div>
      )}

      <div className="shrink-0 border-t p-3">
        {pendingSelection && (
          <div className="mb-2 flex items-start gap-2 rounded-md border bg-muted/50 px-2.5 py-1.5 text-[11px]">
            <span className="line-clamp-2 flex-1 italic text-muted-foreground">
              “{pendingSelection}”
            </span>
            <button
              type="button"
              onClick={() => setPendingSelection(null)}
              className="text-muted-foreground hover:text-foreground"
              aria-label="移除選取文字"
            >
              <XIcon className="size-3.5" />
            </button>
          </div>
        )}
        <div className="flex items-end gap-2">
          <Textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={ready ? "Ask this paper..." : "等待 AI 索引建立…"}
            disabled={!ready || sending}
            rows={2}
            className="min-h-0 resize-none text-[13px]"
          />
          <Button
            size="icon"
            aria-label="Send"
            onClick={() => send({ message: input })}
            disabled={!ready || sending || !input.trim()}
          >
            <SendIcon />
          </Button>
        </div>
        <p className="mt-1.5 text-[10px] text-muted-foreground">
          Enter 送出 · Shift+Enter 換行
        </p>
      </div>
    </div>
  );
}
