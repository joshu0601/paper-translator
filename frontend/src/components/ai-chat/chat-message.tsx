"use client";

import { Loader2Icon } from "lucide-react";
import type { ChatMessage } from "@/types";
import { MarkdownLite } from "./markdown-lite";
import { CitationChip } from "./citation-chip";
import { cn } from "@/lib/utils";

export function ChatMessageView({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    const [text, quote] = message.content.split("\n\n> ");
    return (
      <div className="flex justify-end">
        <div className="max-w-[90%] rounded-xl rounded-br-sm bg-foreground px-3 py-2 text-[13px] leading-relaxed text-background">
          {quote && (
            <p className="mb-1 line-clamp-3 border-l-2 border-background/40 pl-2 text-[11.5px] italic opacity-80">
              {quote}
            </p>
          )}
          <p className="whitespace-pre-wrap">{text}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-full">
      {message.pending ? (
        <div className="flex items-center gap-2 py-1 text-xs text-muted-foreground">
          <Loader2Icon className="size-3.5 animate-spin" />
          正在查閱論文…
        </div>
      ) : (
        <div className={cn(message.error && "text-destructive")}>
          <MarkdownLite text={message.content} citations={message.citations} />
          {message.citations && message.citations.length > 0 && (
            <div className="mt-2 border-t pt-2">
              <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                來源
              </p>
              <div className="flex flex-wrap gap-1">
                {message.citations.map((c, i) => (
                  <CitationChip key={`${c.paragraphId}-${i}`} citation={c} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
