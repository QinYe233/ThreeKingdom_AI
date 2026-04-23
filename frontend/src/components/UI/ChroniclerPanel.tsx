import { memo, useRef, useEffect } from "react";
import type { Narrative } from "../../types/game";
import type { ThemeColors } from "../../theme";
import { COUNTRY_COLORS } from "../../theme";

interface ChroniclerPanelProps {
  show: boolean;
  narratives: Narrative[];
  theme: ThemeColors;
}

const ChroniclerPanel = memo(function ChroniclerPanel({
  show,
  narratives,
  theme
}: ChroniclerPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [narratives]);

  if (!show) return null;

  if (!narratives || narratives.length === 0) {
    return (
      <div
        className="absolute bottom-0 left-0 right-0 z-30 transition-transform duration-300"
        style={{
          transform: show ? 'translateY(0)' : 'translateY(100%)',
          height: '50vh',
          backgroundColor: theme.sidebar,
          borderTop: `2px solid ${theme.accent}`,
        }}
      >
        <div className="h-full flex flex-col">
          <div className="flex items-center justify-between p-2 border-b" style={{ borderColor: theme.border }}>
            <div className="text-sm font-subtitle font-bold" style={{ color: theme.accent }}>📜 史官编年</div>
            <button
              className="w-6 h-6 rounded cursor-pointer flex items-center justify-center"
              style={{ backgroundColor: theme.border, color: theme.textMuted }}
            >
              ▼
            </button>
          </div>
          <div className="flex-1 flex items-center justify-center">
            <div className="p-4 text-center text-sm font-body" style={{ color: theme.textMuted }}>
              等待史官记录...
            </div>
          </div>
        </div>
      </div>
    );
  }

  const sortedNarratives = [...narratives].sort((a, b) => b.round - a.round);

  return (
    <div
      className="absolute bottom-0 left-0 right-0 z-30 transition-transform duration-300"
      style={{
        transform: show ? 'translateY(0)' : 'translateY(100%)',
        height: '50vh',
        backgroundColor: theme.sidebar,
        borderTop: `2px solid ${theme.accent}`,
      }}
    >
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between p-2 border-b" style={{ borderColor: theme.border }}>
          <div className="text-sm font-subtitle font-bold" style={{ color: theme.accent }}>📜 史官编年</div>
          <button
            className="w-6 h-6 rounded cursor-pointer flex items-center justify-center"
            style={{ backgroundColor: theme.border, color: theme.textMuted }}
          >
            ▼
          </button>
        </div>
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-4">
          {sortedNarratives.map((narrative) => (
            <div key={narrative.round} className="border-b pb-3" style={{ borderColor: "rgba(128,128,128,0.3)" }}>
              <div className="text-center mb-2">
                <div className="text-base font-title font-bold" style={{ color: "#d97706" }}>
                  第{narrative.round}回 · {narrative.date}
                </div>
              </div>

              {narrative.narrative && (
                <div className="text-xs p-2 rounded mb-2 font-body leading-relaxed whitespace-pre-wrap"
                  style={{ backgroundColor: "rgba(55, 65, 81, 0.15)", color: "#d4d4d8" }}
                >
                  {narrative.narrative}
                </div>
              )}

              {narrative.trend && Object.keys(narrative.trend).length > 0 && (
                <div className="flex gap-1 flex-wrap mb-2">
                  {Object.entries(narrative.trend).map(([name, t]: [string, any]) => (
                    <div key={name} className="text-xs px-2 py-1 rounded"
                      style={{ backgroundColor: "rgba(55, 65, 81, 0.2)", borderLeft: `3px solid ${COUNTRY_COLORS[name] || "#888"}` }}
                    >
                      <span style={{ color: COUNTRY_COLORS[name] || "#888", fontWeight: "bold" }}>{name}</span>
                      <span style={{ color: "#9ca3af" }}> {t.military_trend} · {t.economy_trend}</span>
                    </div>
                  ))}
                </div>
              )}

              {narrative.events && narrative.events.length > 0 && (
                <div className="space-y-1">
                  {narrative.events.map((event, i) => (
                    <div
                      key={i}
                      className="text-xs p-1.5 rounded font-body leading-relaxed"
                      style={{
                        backgroundColor: event.type === "collapse" || event.type === "capital_fallen" || event.type === "nation_defeated"
                          ? "rgba(153, 27, 27, 0.2)"
                          : event.type === "capture"
                          ? "rgba(180, 83, 9, 0.2)"
                          : event.type === "battle"
                          ? "rgba(120, 53, 15, 0.2)"
                          : "rgba(55, 65, 81, 0.15)",
                        color: event.type === "collapse" || event.type === "capital_fallen" || event.type === "nation_defeated"
                          ? "#fca5a5"
                          : event.type === "capture"
                          ? "#fcd34d"
                          : event.type === "battle"
                          ? "#fbbf24"
                          : "#d1d5db",
                      }}
                    >
                      {event.message}
                    </div>
                  ))}
                </div>
              )}

              {(!narrative.events || narrative.events.length === 0) && !narrative.narrative && (
                <div className="text-xs text-center" style={{ color: theme.textMuted }}>
                  是岁无事，天下太平。
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
});

export default ChroniclerPanel;
