import { memo, useRef, useEffect } from "react";
import type { Narrative } from "../../types/game";
import type { ThemeColors, FONTS } from "../../theme";
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
            <div className="text-sm font-subtitle font-bold" style={{ color: theme.accent, fontFamily: FONTS.subtitle }}>📜 史官编年</div>
            <button
              className="w-6 h-6 rounded cursor-pointer flex items-center justify-center"
              style={{ backgroundColor: theme.border, color: theme.textMuted }}
            >
              ▼
            </button>
          </div>
          <div className="flex-1 flex items-center justify-center">
            <div className="p-4 text-center text-sm font-body" style={{ color: theme.textMuted, fontFamily: FONTS.body }}>
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
          <div className="text-sm font-subtitle font-bold" style={{ color: theme.accent, fontFamily: FONTS.subtitle }}>📜 史官编年</div>
          <button
            className="w-6 h-6 rounded cursor-pointer flex items-center justify-center"
            style={{ backgroundColor: theme.border, color: theme.textMuted }}
          >
            ▼
          </button>
        </div>
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-4">
          {sortedNarratives.map((narrative) => (
            <div key={narrative.round} className="mb-3" style={{
              padding: "8px",
              background: "linear-gradient(to bottom, #f0e6d3, #e8dccb)",
              borderLeft: "4px solid rgba(139, 115, 85, 0.6)",
              boxShadow: "inset 0 2px 8px rgba(139, 115, 85, 0.1)"
            }}>
              {/* Header */}
              <div className="text-center mb-3 pb-2 border-b-2" style={{
                borderColor: "rgba(139, 115, 85, 0.2)",
                fontFamily: FONTS.title
              }}>
                <div className="text-lg" style={{ color: theme.text, fontWeight: "bold" }}>
                  📜 第{narrative.round}回 · {narrative.date}
                </div>
              </div>

              {/* Historian's Commentary - Main Feature */}
              {narrative.narrative && (
                <div className="mb-4 p-4 relative" style={{
                  background: "linear-gradient(to bottom, #f5f0dc 0%, #e8dccb 100%)",
                  border: "1px solid rgba(139, 115, 85, 0.3)",
                  fontFamily: FONTS.body,
                  color: theme.text,
                  fontSize: "0.875rem",
                  lineHeight: "1.75",
                  letterSpacing: "0.05em"
                }}>
                  {/* Decorative scroll ends */}
                  <div className="absolute top-0 left-0 w-4 h-full" style={{
                    background: "linear-gradient(to bottom, transparent, rgba(139, 115, 85, 0.2) 50%, transparent)"
                  }} />
                  <div className="absolute top-0 right-0 w-4 h-full" style={{
                    background: "linear-gradient(to bottom, transparent, rgba(139, 115, 85, 0.2) 50%, transparent)"
                  }} />

                  {/* Red seal for important events */}
                  {narrative.events?.some(e =>
                    e.type === "collapse" || e.type === "capital_fallen" || e.type === "nation_defeated"
                  ) && (
                    <div className="absolute top-2 right-2 w-8 h-8 rounded-full flex items-center justify-center"
                      style={{ background: theme.error, boxShadow: "0 2px 4px rgba(197, 48, 48, 0.3)" }}
                    >
                      <span className="text-xs font-bold" style={{ color: "#fff", fontFamily: FONTS.subtitle }}>
                        史
                      </span>
                    </div>
                  )}

                  <div className="pl-8 pr-8" style={{ textAlign: "justify" }}>
                    {narrative.narrative}
                  </div>
                </div>
              )}

              {/* Military Affairs Section */}
              {narrative.events && narrative.events.length > 0 && (
                <div className="mb-4">
                  <div className="text-xs mb-2 pb-1" style={{
                    color: theme.textMuted,
                    fontFamily: FONTS.subtitle,
                    borderBottom: "1px dashed rgba(139, 115, 85, 0.3)"
                  }}>
                    ─ 战况纪要 ─
                  </div>
                  <div className="space-y-1.5 pl-2" style={{ borderLeft: "2px solid rgba(139, 115, 85, 0.3)" }}>
                    {narrative.events.map((event, i) => (
                      <div
                        key={i}
                        className="text-xs pl-2 relative"
                        style={{
                          fontFamily: FONTS.body,
                          color: theme.text,
                          lineHeight: "1.6"
                        }}
                      >
                        {/* Event icon */}
                        <span className="absolute -left-3 top-0.5 w-1.5 h-1.5 text-center text-xs"
                          style={{
                            background: event.type === "collapse" || event.type === "capital_fallen" || event.type === "nation_defeated"
                              ? theme.error
                              : event.type === "capture"
                              ? theme.accent
                              : event.type === "battle"
                              ? theme.warning
                              : theme.success
                          }}
                        >
                          {event.type === "collapse" ? "🏛" :
                           event.type === "capital_fallen" ? "🏰" :
                           event.type === "nation_defeated" ? "💀" :
                           event.type === "capture" ? "🚩" :
                           event.type === "battle" ? "⚔️" : "📋"}
                        </span>
                        {event.message}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Trends Analysis */}
              {narrative.trend && Object.keys(narrative.trend).length > 0 && (
                <div>
                  <div className="text-xs mb-2 pb-1" style={{
                    color: theme.textMuted,
                    fontFamily: FONTS.subtitle,
                    borderBottom: "1px dashed rgba(139, 115, 85, 0.3)"
                  }}>
                    ─ 趋势评述 ─
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(narrative.trend).map(([name, t]: [string, any]) => (
                      <div key={name} className="p-2 relative" style={{
                        background: "linear-gradient(135deg, rgba(139, 115, 85, 0.1), rgba(139, 115, 85, 0.05))",
                        border: "1px solid rgba(139, 115, 85, 0.2)",
                        fontFamily: FONTS.body
                      }}>
                        <div className="text-xs mb-1" style={{
                          color: COUNTRY_COLORS[name] || theme.text,
                          fontWeight: "bold",
                          borderBottom: "1px solid rgba(139, 115, 85, 0.2)"
                        }}>
                          {name}
                        </div>
                        <div className="flex gap-1 text-xs">
                          <span style={{ color: theme.success }}>
                            {t.military_trend.includes("成长") ? "📈" : "📉"}
                          </span>
                          <span style={{ color: theme.textMuted }}>
                            兵势：{t.military_trend}
                          </span>
                        </div>
                        <div className="flex gap-1 text-xs">
                          <span style={{ color: theme.warning }}>
                            {t.economy_trend.includes("成长") ? "📈" : "📉"}
                          </span>
                          <span style={{ color: theme.textMuted }}>
                            库储：{t.economy_trend}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Empty State */}
              {(!narrative.events || narrative.events.length === 0) && !narrative.narrative && (
                <div className="text-center py-6" style={{
                  fontFamily: FONTS.body,
                  color: theme.textMuted,
                  fontStyle: "italic"
                }}>
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
