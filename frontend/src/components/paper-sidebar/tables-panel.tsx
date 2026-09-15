"use client";

import { useWorkspace } from "@/components/workspace/workspace-context";

export function TablesPanel() {
  const { paper, askAI } = useWorkspace();

  if (paper.tables.length === 0) {
    return <p className="px-4 py-6 text-xs text-muted-foreground">此論文沒有偵測到表格。</p>;
  }

  return (
    <div className="space-y-3 px-3 py-3">
      {paper.tables.map((t) => (
        <div key={t.id} className="rounded-lg border bg-card">
          <div className="space-y-1 px-2.5 py-2">
            <p className="line-clamp-3 text-xs leading-snug">
              {t.label && <span className="font-medium">{t.label}. </span>}
              {t.caption}
            </p>
            <div className="flex gap-2 text-[11px] text-muted-foreground">
              <span>Page {t.pageNumber}</span>
              <button
                type="button"
                className="hover:text-foreground hover:underline"
                onClick={() =>
                  askAI({
                    message: `請解釋 ${t.label ?? "這個表格"} 的內容與結果：${t.caption}`,
                    action: "explain",
                    selectedText: [t.caption, ...t.rows.map((r) => r.join(" | "))].join("\n"),
                    context: "selected_text",
                  })
                }
              >
                Ask AI
              </button>
            </div>
          </div>
          {t.rows.length > 0 && (
            <div className="overflow-x-auto border-t">
              <table className="w-full text-[11px]">
                <tbody>
                  {t.rows.slice(0, 12).map((row, i) => (
                    <tr key={i} className={i === 0 ? "bg-muted/60 font-medium" : "border-t"}>
                      {row.map((cell, j) => (
                        <td key={j} className="whitespace-nowrap px-2 py-1">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {t.rows.length > 12 && (
                <p className="px-2 py-1 text-[10px] text-muted-foreground">
                  …共 {t.rows.length} 列
                </p>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
