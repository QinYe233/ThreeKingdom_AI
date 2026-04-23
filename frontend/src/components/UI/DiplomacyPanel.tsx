import { memo, useRef, useEffect } from "react";
import type { ThemeColors } from "../../theme";
import { COUNTRY_COLORS, getRelationStatus } from "../../theme";

interface DiplomaticEvent {
  round: number;
  from_country: string;
  to_country: string;
  event_type: string;
  content: string;
  visibility: string;
}

interface DiplomacyPanelProps {
  show: boolean;
  relations: Record<string, any>;
  diplomaticEvents: DiplomaticEvent[];
  theme: ThemeColors;
}

const DiplomacyPanel = memo(function DiplomacyPanel({
  show,
  relations,
  diplomaticEvents,
  theme
}: DiplomacyPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [diplomaticEvents]);

  if (!show) return null;

  return (
    <div
      className="absolute bottom-0 left-0 right-0 z-30 transition-transform duration-300"
      style={{
        transform: show ? 'translateY(0)' : 'translateY(100%)',
        height: '35vh',
        backgroundColor: theme.sidebar,
        borderTop: `2px solid ${theme.accent}`,
      }}
    >
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between p-2 border-b" style={{ borderColor: theme.border }}>
          <div className="text-sm font-subtitle font-bold" style={{ color: theme.accent }}>🤝 外交关系</div>
          <button
            onClick={() => {}}
            className="w-6 h-6 rounded cursor-pointer flex items-center justify-center"
            style={{ backgroundColor: theme.border, color: theme.textMuted }}
          >
            ▼
          </button>
        </div>
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-2">
          <div className="mb-3">
            <div className="text-xs font-bold mb-2" style={{ color: theme.textMuted }}>当前关系状态</div>
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(relations).map(([key, rel]: [string, any]) => {
                const status = getRelationStatus(rel);
                return (
                  <div
                    key={key}
                    className="p-2 rounded text-center"
                    style={{ backgroundColor: theme.bg }}
                  >
                    <div className="flex items-center justify-center gap-1 mb-1">
                      <span style={{ color: COUNTRY_COLORS[rel.country_a] || theme.text, fontWeight: "bold" }}>
                        {rel.country_a}
                      </span>
                      <span style={{ color: theme.textMuted }}>-</span>
                      <span style={{ color: COUNTRY_COLORS[rel.country_b] || theme.text, fontWeight: "bold" }}>
                        {rel.country_b}
                      </span>
                    </div>
                    <div className="text-xs font-bold" style={{ color: status.color }}>
                      {status.text}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
          
          {diplomaticEvents.length > 0 && (
            <div>
              <div className="text-xs font-bold mb-2" style={{ color: theme.textMuted }}>外交事件记录</div>
              {diplomaticEvents.slice(-10).reverse().map((event, i) => (
                <div
                  key={i}
                  className="p-2 rounded mb-1"
                  style={{ backgroundColor: theme.bg }}
                >
                  <div className="flex items-center justify-between text-xs">
                    <span>
                      <span style={{ color: COUNTRY_COLORS[event.from_country] || theme.text, fontWeight: "bold" }}>
                        {event.from_country}
                      </span>
                      <span style={{ color: theme.textMuted }}> → </span>
                      <span style={{ color: COUNTRY_COLORS[event.to_country] || theme.text, fontWeight: "bold" }}>
                        {event.to_country}
                      </span>
                    </span>
                    <span style={{ color: theme.textMuted }}>第{event.round}回</span>
                  </div>
                  <div className="text-xs mt-1" style={{ color: theme.text }}>
                    {event.content}
                  </div>
                  <div className="text-xs mt-0.5" style={{ color: theme.textMuted }}>
                    {event.visibility === "public" ? "📢 公开" : "🔒 秘密"}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

export default DiplomacyPanel;
