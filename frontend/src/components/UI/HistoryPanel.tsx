import { memo, useRef, useEffect } from "react";
import type { ThemeColors } from "../../theme";
import type { ThinkingRecord } from "../../types/game";
import { COUNTRY_COLORS } from "../../theme";

interface HistoryPanelProps {
  show: boolean;
  thinkingRecords: ThinkingRecord[];
  selectedRecord: ThinkingRecord | null;
  onSelectRecord: (record: ThinkingRecord | null) => void;
  theme: ThemeColors;
}

const HistoryPanel = memo(function HistoryPanel({
  show,
  thinkingRecords,
  selectedRecord,
  onSelectRecord,
  theme
}: HistoryPanelProps) {
  const sortedRecords = [...thinkingRecords].sort((a, b) => b.round - a.round);

  if (!show) return null;

  return (
    <div
      className="absolute bottom-0 left-0 right-0 z-30 transition-transform duration-300"
      style={{
        transform: show ? 'translateY(0)' : 'translateY(100%)',
        height: '40vh',
        backgroundColor: theme.sidebar,
        borderTop: `2px solid ${theme.accent}`,
      }}
    >
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between p-2 border-b" style={{ borderColor: theme.border }}>
          <div className="text-sm font-subtitle font-bold" style={{ color: theme.accent }}>📚 历史记录</div>
          <button
            onClick={() => onSelectRecord(null)}
            className="w-6 h-6 rounded cursor-pointer flex items-center justify-center"
            style={{ backgroundColor: theme.border, color: theme.textMuted }}
          >
            ▼
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {selectedRecord ? (
            <div className="p-3 rounded" style={{ backgroundColor: theme.bg }}>
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-bold" style={{ color: COUNTRY_COLORS[selectedRecord.country] || theme.accent }}>
                  第{selectedRecord.round}回 · {selectedRecord.country}
                </div>
                <button
                  onClick={() => onSelectRecord(null)}
                  className="text-xs px-2 py-1 rounded cursor-pointer"
                  style={{ backgroundColor: theme.border, color: theme.textMuted }}
                >
                  返回
                </button>
              </div>
              {selectedRecord.thinking && (
                <div className="mb-3">
                  <div className="text-xs font-bold mb-1" style={{ color: "#7c3aed" }}>💭 深度思考</div>
                  <div className="text-xs whitespace-pre-wrap leading-relaxed" style={{ color: "#5b21b6" }}>
                    {selectedRecord.thinking}
                  </div>
                </div>
              )}
              {selectedRecord.content && (
                <div className="mb-3">
                  <div className="text-xs font-bold mb-1" style={{ color: theme.accent }}>📋 决策输出</div>
                  <div className="text-xs whitespace-pre-wrap leading-relaxed" style={{ color: theme.text }}>
                    {selectedRecord.content}
                  </div>
                </div>
              )}
              {selectedRecord.actions.length > 0 && (
                <div>
                  <div className="text-xs font-bold mb-1" style={{ color: "#059669" }}>⚡ 执行行为</div>
                  {selectedRecord.actions.map((a, i) => (
                    <div key={i} className="text-xs leading-relaxed" style={{ color: "#047857" }}>
                      {a}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-1">
              {sortedRecords.map((record, i) => (
                <div
                  key={i}
                  className="p-2 rounded cursor-pointer hover:opacity-80 transition-opacity"
                  style={{ backgroundColor: theme.bg }}
                  onClick={() => onSelectRecord(record)}
                >
                  <div className="flex items-center justify-between">
                    <span style={{ color: COUNTRY_COLORS[record.country] || theme.accent, fontWeight: "bold" }}>
                      第{record.round}回 · {record.country}
                    </span>
                    <span style={{ color: theme.textMuted, fontSize: 10 }}>
                      {record.actions.length}个行动
                    </span>
                  </div>
                  {record.actions.length > 0 && (
                    <div className="mt-1 text-xs truncate" style={{ color: theme.textMuted }}>
                      {record.actions[0]}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

export default HistoryPanel;
