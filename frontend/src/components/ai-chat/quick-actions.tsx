"use client";

/** Suggested prompts (SPEC §33). */
export const QUICK_ACTIONS: { label: string; message: string }[] = [
  { label: "Summarize this paper", message: "請摘要這篇論文。" },
  { label: "這篇論文解決什麼問題？", message: "這篇論文主要解決什麼問題？" },
  { label: "主要 Contribution 是什麼？", message: "這篇論文的主要 Contribution 是什麼？" },
  { label: "解釋 Methodology", message: "請解釋這篇論文的 Methodology。" },
  { label: "解釋 System Model", message: "請解釋這篇論文的 System Model。" },
  { label: "解釋 MDP", message: "請解釋這篇論文如何建模 MDP。" },
  { label: "State 是什麼？", message: "這篇論文的 State 是如何定義的？" },
  { label: "Action 是什麼？", message: "這篇論文的 Action 是如何定義的？" },
  { label: "Reward Function 是什麼？", message: "這篇論文的 Reward Function 是什麼？" },
  { label: "使用哪些 Baseline？", message: "這篇論文使用了哪些 Baseline 方法？" },
  { label: "Experimental Setup 是什麼？", message: "這篇論文的 Experimental Setup 是什麼？" },
  { label: "結果證明了什麼？", message: "這篇論文的實驗結果證明了什麼？" },
  { label: "有哪些 Limitations？", message: "這篇論文有哪些 Limitations？" },
  { label: "幫我整理成論文簡報", message: "請幫我把這篇論文整理成簡報大綱（每頁重點與來源）。" },
];

export function QuickActions({
  onPick,
  compact,
}: {
  onPick: (message: string) => void;
  compact?: boolean;
}) {
  const items = compact ? QUICK_ACTIONS.slice(0, 5) : QUICK_ACTIONS;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((a) => (
        <button
          key={a.label}
          type="button"
          onClick={() => onPick(a.message)}
          className="rounded-full border px-2.5 py-1 text-[11.5px] text-muted-foreground transition-colors hover:border-foreground/40 hover:text-foreground"
        >
          {a.label}
        </button>
      ))}
    </div>
  );
}
