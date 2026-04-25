import { memo, useRef, useEffect } from "react";
import type { ThemeColors } from "../../theme";
import { COUNTRY_COLORS } from "../../theme";

interface ThinkingChainProps {
  currentRound: number;
  currentActingCountry: string;
  isThinking: boolean;
  isProcessing: boolean;
  thinkingComplete: boolean;
  currentThinking: string;
  currentContent: string;
  currentActions: string[];
  currentRecord: any;
  theme: ThemeColors;
  pendingCountrySwitch?: boolean;
  completedCountryName?: string | null;
}

const ThinkingChain = memo(function ThinkingChain({
  currentRound,
  currentActingCountry,
  isThinking,
  isProcessing,
  thinkingComplete,
  currentThinking,
  currentContent,
  currentActions,
  currentRecord,
  theme,
  pendingCountrySwitch,
  completedCountryName
}: ThinkingChainProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [currentThinking, currentContent, currentActions]);

  const displayCountry = pendingCountrySwitch ? (completedCountryName || currentActingCountry) : currentActingCountry;
  const isDecisionComplete = thinkingComplete || pendingCountrySwitch;

  return (
    <div className="h-full flex flex-col" style={{ backgroundColor: theme.sidebar, borderRight: `1px solid ${theme.border}` }}>
      <div className="p-3 border-b" style={{ borderColor: theme.border }}>
        <div className="text-sm font-subtitle font-bold" style={{ color: theme.text }}>策略思考链</div>
        <div className="text-xs mt-1 font-body" style={{ color: theme.textMuted }}>实时观察AI决策过程</div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
        {(isThinking || isProcessing || isDecisionComplete) && (
          <div 
            className="p-3 rounded transition-opacity duration-500" 
            style={{ 
              backgroundColor: theme.bg,
              opacity: isDecisionComplete ? 0.7 : 1
            }}
          >
            <div className="text-xs mb-2 font-bold" style={{ color: COUNTRY_COLORS[displayCountry] || theme.accent }}>
              第{currentRound}回 · {displayCountry} {isDecisionComplete ? "决策完成" : "正在决策"}
            </div>
            {currentThinking && (
              <div className="mb-3">
                <div className="text-xs font-bold mb-1" style={{ color: "#7c3aed" }}>💭 深度思考</div>
                <div className="text-xs whitespace-pre-wrap leading-relaxed" style={{ color: "#5b21b6" }}>
                  {currentThinking}
                </div>
              </div>
            )}
            {currentContent && (
              <div className="mb-3">
                <div className="text-xs font-bold mb-1" style={{ color: theme.accent }}>📋 决策输出</div>
                <div className="text-xs whitespace-pre-wrap leading-relaxed" style={{ color: theme.text }}>
                  {currentContent}
                </div>
              </div>
            )}
            {currentActions && currentActions.length > 0 && (
              <div>
                <div className="text-xs font-bold mb-1" style={{ color: "#059669" }}>⚡ 执行行为</div>
                {currentActions.map((a, i) => (
                  <div key={i} className="text-xs leading-relaxed" style={{ color: "#047857" }}>
                    {a}
                  </div>
                ))}
              </div>
            )}
            {!currentThinking && !currentContent && (!currentActions || currentActions.length === 0) && !isDecisionComplete && (
              <div className="text-xs" style={{ color: theme.textMuted }}>
                <span className="animate-pulse">●</span> 等待AI响应...
              </div>
            )}
          </div>
        )}

        {!isThinking && !isProcessing && !thinkingComplete && currentRecord && (
          <div className="p-3 rounded" style={{ backgroundColor: theme.bg }}>
            <div className="text-xs mb-2 font-bold" style={{ color: COUNTRY_COLORS[currentRecord.country] || theme.accent }}>
              第{currentRecord.round}回 · {currentRecord.country}
            </div>
            {currentRecord.thinking && (
              <div className="mb-3">
                <div className="text-xs font-bold mb-1" style={{ color: "#7c3aed" }}>💭 深度思考</div>
                <div className="text-xs whitespace-pre-wrap leading-relaxed" style={{ color: "#5b21b6" }}>
                  {currentRecord.thinking}
                </div>
              </div>
            )}
            {currentRecord.content && (
              <div className="mb-3">
                <div className="text-xs font-bold mb-1" style={{ color: theme.accent }}>📋 决策输出</div>
                <div className="text-xs whitespace-pre-wrap leading-relaxed" style={{ color: theme.text }}>
                  {currentRecord.content}
                </div>
              </div>
            )}
            {currentRecord.actions.length > 0 && (
              <div>
                <div className="text-xs font-bold mb-1" style={{ color: "#059669" }}>⚡ 执行行为</div>
                {currentRecord.actions.map((a: string, i: number) => (
                  <div key={i} className="text-xs leading-relaxed" style={{ color: "#047857" }}>
                    {a}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {!isThinking && !isProcessing && !thinkingComplete && !currentRecord && (
          <div className="text-xs text-center py-8" style={{ color: theme.textMuted }}>
            点击"推进"或"自动"开始游戏
          </div>
        )}
      </div>
    </div>
  );
});

export default ThinkingChain;
