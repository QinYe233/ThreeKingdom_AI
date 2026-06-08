/**
 * 史官编年面板 - 展示史官AI撰写的叙事文本
 * 包含编年叙事、战况纪要、势力趋势等内容
 */
import { memo, useRef, useEffect } from "react";
import type { Narrative } from "../../types/game";
import type { ThemeColors } from "../../theme";
import { FONTS, COUNTRY_COLORS } from "../../theme";
import { usePanelAnimation } from "../../hooks/usePanelAnimation";

interface ChroniclerPanelProps {
  show: boolean;
  narratives: Narrative[];
  onClose: () => void;
  theme: ThemeColors;
}

const ChroniclerPanel = memo(function ChroniclerPanel({
  show,
  narratives,
  onClose,
  theme
}: ChroniclerPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { panelRef, visible } = usePanelAnimation(show, "up", window.innerHeight * 0.5, 0.3);

  // 新叙事到来时自动滚动到底部
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [narratives]);

  if (!visible) return null;

  if (!narratives || narratives.length === 0) {
    return (
      <div
        ref={panelRef}
        className="absolute bottom-0 left-0 right-0 z-30"
        style={{
          height: '50vh',
          backgroundColor: theme.sidebar,
          borderTop: `2px solid ${theme.accent}`,
        }}
      >
        <div className="h-full flex flex-col">
          <div className="flex items-center justify-between p-2 border-b" style={{ borderColor: theme.border }}>
            <div className="text-sm font-subtitle font-bold" style={{ color: theme.accent, fontFamily: FONTS.subtitle }}>📜 史官编年</div>
            <button
              onClick={onClose}
              className="w-6 h-6 rounded cursor-pointer flex items-center justify-center"
              style={{ backgroundColor: theme.border, color: theme.textMuted }}
            >
              ✕
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

  // 按回合倒序排列叙事
  const sortedNarratives = [...narratives].sort((a, b) => b.round - a.round);

  return (
    <div
      ref={panelRef}
      className="absolute bottom-0 left-0 right-0 z-30"
      style={{
        height: '50vh',
        backgroundColor: theme.sidebar,
        borderTop: `2px solid ${theme.accent}`,
      }}
    >
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between p-2 border-b" style={{ borderColor: theme.border }}>
          <div className="text-sm font-subtitle font-bold" style={{ color: theme.accent, fontFamily: FONTS.subtitle }}>📜 史官编年</div>
          <button
            onClick={onClose}
            className="w-6 h-6 rounded cursor-pointer flex items-center justify-center"
            style={{ backgroundColor: theme.border, color: theme.textMuted }}
          >
            ✕
          </button>
        </div>
        <div ref={scrollRef} className="flex-1 overflow-y-auto" style={{
          background: "linear-gradient(to bottom, rgba(139, 115, 85, 0.03), transparent)"
        }}>
          {sortedNarratives.map((narrative) => (
            <div key={narrative.round} style={{
              padding: "16px 20px",
              borderBottom: `1px solid ${theme.border}`,
              backgroundColor: narrative.round % 2 === 0 ? "rgba(139, 115, 85, 0.03)" : "transparent"
            }}>
              {/* Round header */}
              <div style={{ fontSize: "1rem", fontWeight: "bold", color: theme.accent, marginBottom: 12, fontFamily: FONTS.title }}>
                📜 第{narrative.round}回 · {narrative.date}
              </div>

              {/* Narrative text - main content, larger and more readable */}
              {narrative.narrative && (
                <div style={{ fontSize: "1rem", lineHeight: 2, color: theme.text, fontFamily: FONTS.body, textAlign: "justify", marginBottom: 12 }}>
                  {narrative.narrative}
                </div>
              )}

              {/* Events - compact list */}
              {narrative.events && narrative.events.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: "0.75rem", color: theme.textMuted, marginBottom: 4 }}>战况纪要</div>
                  {narrative.events.map((event, i) => (
                    <div key={i} style={{ fontSize: "0.85rem", color: theme.text, lineHeight: 1.8, paddingLeft: 12, borderLeft: `2px solid ${theme.border}` }}>
                      {event.type === "collapse" ? "🏛" : event.type === "capital_fallen" ? "🏰" : event.type === "nation_defeated" ? "💀" : event.type === "capture" ? "🚩" : event.type === "battle" ? "⚔️" : "📋"} {event.message}
                    </div>
                  ))}
                </div>
              )}

              {/* Trend - inline badges */}
              {narrative.trend && Object.keys(narrative.trend).length > 0 && (
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {Object.entries(narrative.trend).map(([name, t]: [string, any]) => (
                    <span key={name} style={{ fontSize: "0.75rem", padding: "2px 8px", borderRadius: 4, backgroundColor: `${COUNTRY_COLORS[name] || theme.text}15`, color: COUNTRY_COLORS[name] || theme.text, border: `1px solid ${COUNTRY_COLORS[name] || theme.text}30` }}>
                      {name}: 兵势{(t.military_trend || "").includes("成长") ? "↑" : "↓"} 库储{(t.economy_trend || "").includes("成长") ? "↑" : "↓"}
                    </span>
                  ))}
                </div>
              )}

              {/* Empty state */}
              {(!narrative.events || narrative.events.length === 0) && !narrative.narrative && (
                <div style={{ color: theme.textMuted, fontStyle: "italic", textAlign: "center", padding: 16 }}>
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
