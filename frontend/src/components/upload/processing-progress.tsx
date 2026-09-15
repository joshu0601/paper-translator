"use client";

import { CheckIcon, CircleIcon, Loader2Icon, XIcon } from "lucide-react";
import type { PaperDocument } from "@/types";
import { cn } from "@/lib/utils";

/** SPEC §7: step list with ✓ / percent / spinner. */
export function ProcessingProgress({
  document,
  compact = false,
}: {
  document: PaperDocument;
  compact?: boolean;
}) {
  return (
    <ul className={cn("space-y-1.5", compact ? "text-xs" : "text-sm")}>
      {document.steps.map((step) => (
        <li key={step.key} className="flex items-center gap-3">
          <span className="flex size-4 shrink-0 items-center justify-center">
            {step.status === "done" && <CheckIcon className="size-4 text-emerald-600" />}
            {step.status === "running" && (
              <Loader2Icon className="size-4 animate-spin text-foreground" />
            )}
            {step.status === "failed" && <XIcon className="size-4 text-destructive" />}
            {step.status === "pending" && (
              <CircleIcon className="size-3 text-muted-foreground/50" />
            )}
          </span>
          <span
            className={cn(
              "flex-1",
              step.status === "pending" && "text-muted-foreground",
              step.status === "failed" && "text-destructive",
            )}
          >
            {step.label}
          </span>
          {step.status === "running" && typeof step.percent === "number" && (
            <span className="tabular-nums text-muted-foreground">{step.percent}%</span>
          )}
        </li>
      ))}
      {document.error && (
        <li className="pt-2 text-xs text-destructive">{document.error}</li>
      )}
    </ul>
  );
}
