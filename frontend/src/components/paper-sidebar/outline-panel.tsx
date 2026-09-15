"use client";

import { useWorkspace } from "@/components/workspace/workspace-context";
import { cn } from "@/lib/utils";

export function OutlinePanel() {
  const { paper, currentSectionId, jumpToSection } = useWorkspace();
  const doc = paper.document!;

  return (
    <div className="px-2 py-3">
      <div className="mb-3 px-2">
        <p className="line-clamp-3 text-sm font-medium leading-snug">{doc.title}</p>
        {doc.authors.length > 0 && (
          <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
            {doc.authors.join(", ")}
          </p>
        )}
        <p className="mt-1 text-xs text-muted-foreground">
          {[doc.venue, doc.year].filter(Boolean).join(" · ")}
          {doc.pageCount ? ` · ${doc.pageCount} 頁` : ""}
        </p>
      </div>

      <p className="mb-1 px-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        Outline
      </p>
      <nav>
        <ul className="space-y-0.5">
          {paper.sections.map((s) => {
            const depth = s.sectionNumber ? s.sectionNumber.split(".").length - 1 : 0;
            return (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => jumpToSection(s.id)}
                  className={cn(
                    "flex w-full items-baseline gap-1.5 rounded-md px-2 py-1 text-left text-[13px] leading-snug transition-colors",
                    currentSectionId === s.id
                      ? "bg-muted font-medium text-foreground"
                      : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                  )}
                  style={{ paddingLeft: `${8 + Math.min(depth, 3) * 12}px` }}
                >
                  {s.sectionNumber && (
                    <span className="shrink-0 font-mono text-[11px] tabular-nums opacity-70">
                      {s.sectionNumber}
                    </span>
                  )}
                  <span className="line-clamp-2">{s.title}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}
