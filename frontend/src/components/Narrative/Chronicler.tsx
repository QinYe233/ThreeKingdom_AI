import type { Narrative } from "../../types/game";
import { COUNTRY_COLORS } from "../../theme";

interface ChroniclerProps {
  narratives: Narrative[];
}

export default function Chronicler({ narratives }: ChroniclerProps) {
  if (!narratives || narratives.length === 0) {
    return (
      <div className="p-4 text-center text-sm font-body" style={{ color: "#6b7280" }}>
        等待史官记录...
      </div>
    );
  }

  const sortedNarratives = [...narratives].sort((a, b) => b.round - a.round);

  return (
    <div className="h-full flex flex-col">
      <div className="p-3 border-b" style={{ borderColor: "inherit" }}>
        <div className="text-sm font-subtitle font-bold">史官编年</div>
        <div className="text-xs mt-1" style={{ color: "#6b7280" }}>共 {narratives.length} 回合记录</div>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
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
              <div className="text-xs text-center" style={{ color: "#6b7280" }}>
                是岁无事，天下太平。
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
