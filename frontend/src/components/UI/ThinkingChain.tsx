import { memo, useRef, useEffect, useState, useMemo } from "react";
import type { ThemeColors } from "../../theme";
import { COUNTRY_COLORS, FONTS } from "../../theme";

interface ThinkingChainProps {
  currentRound: number;
  currentActingCountry: string;
  pendingCountrySwitch: boolean;
  completedCountryName: string | null;
  isThinking: boolean;
  isProcessing: boolean;
  currentThinking: string;
  currentContent: string;
  currentActions: any[];
  currentRecord: any;
  theme: ThemeColors;
}

const ThinkingChain = memo(function ThinkingChain({
  currentRound,
  currentActingCountry,
  pendingCountrySwitch,
  completedCountryName,
  isThinking,
  isProcessing,
  currentThinking,
  currentContent,
  currentActions,
  currentRecord,
  theme,
}: ThinkingChainProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const lastContentLengthRef = useRef(0);

  const displayContent = useMemo(() => {
    if (!currentContent) return "";
    return currentContent;
  }, [currentContent]);

  const displayThinking = useMemo(() => {
    if (!currentThinking) return "";
    return currentThinking;
  }, [currentThinking]);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      const el = scrollRef.current;
      const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
      if (isNearBottom || currentContent.length !== lastContentLengthRef.current) {
        el.scrollTop = el.scrollHeight;
      }
    }
    lastContentLengthRef.current = currentContent.length;
  }, [currentContent, currentThinking, autoScroll]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const el = scrollRef.current;
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    setAutoScroll(isNearBottom);
  };

  const isWorking = isThinking || isProcessing;
  const isDone = pendingCountrySwitch && !isThinking && !isProcessing;
  const countryColor = COUNTRY_COLORS[currentActingCountry] || theme.accent;

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: theme.sidebar }}>
      <div className="flex items-center justify-between px-3 py-2 border-b" style={{ borderColor: theme.border }}>
        <div className="flex items-center gap-2">
          <span className="text-sm font-subtitle font-bold" style={{ color: countryColor, fontFamily: FONTS.subtitle }}>
            {currentActingCountry}国决策
          </span>
          <span className="text-xs" style={{ color: theme.textMuted }}>
            第{currentRound}回
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isWorking && (
            <span className="text-xs px-2 py-0.5 rounded animate-pulse" style={{ backgroundColor: countryColor + "30", color: countryColor }}>
              思考中...
            </span>
          )}
          {isDone && (
            <span className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: theme.success + "30", color: theme.success }}>
              决策完成
            </span>
          )}
        </div>
      </div>

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-3 py-2"
        style={{ fontSize: "13px", lineHeight: 1.7 }}
      >
        {displayThinking && (
          <div className="mb-3">
            <div className="text-xs font-bold mb-1" style={{ color: theme.textMuted }}>💭 思考</div>
            <div className="pl-2 border-l-2" style={{ borderColor: countryColor + "40", color: theme.textMuted, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
              {displayThinking}
            </div>
          </div>
        )}

        {displayContent && (
          <div className="mb-3">
            <div className="text-xs font-bold mb-1" style={{ color: theme.text }}>📋 决策</div>
            <div style={{ color: theme.text, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
              {displayContent}
            </div>
          </div>
        )}

        {currentActions.length > 0 && (
          <div className="mb-3">
            <div className="text-xs font-bold mb-1" style={{ color: theme.text }}>⚔ 行动</div>
            <div className="space-y-1">
              {currentActions.map((action: any, idx: number) => (
                <div
                  key={`${action.type}-${idx}`}
                  className="px-2 py-1 rounded text-xs"
                  style={{ backgroundColor: theme.bg, color: theme.text }}
                >
                  {action.type === "attack" && `⚔ 进攻：${action.from || "?"} → ${action.to || "?"} (${action.troops || "?"}兵)`}
                  {action.type === "recruit" && `👥 征兵：${action.block || "?"} (+${action.troops || "?"}兵)`}
                  {action.type === "develop" && `🏗 发展：${action.block || "?"}`}
                  {action.type === "tax" && `💰 征税`}
                  {action.type === "move" && `🔄 调兵：${action.from || "?"} → ${action.to || "?"} (${action.troops || "?"}兵)`}
                  {action.type === "harass" && `🏹 骚扰：${action.to || "?"}`}
                  {!["attack", "recruit", "develop", "tax", "move", "harass"].includes(action.type) && `${action.type}: ${JSON.stringify(action)}`}
                </div>
              ))}
            </div>
          </div>
        )}

        {!isWorking && !isDone && !displayContent && !displayThinking && (
          <div className="flex items-center justify-center h-full">
            <span className="text-sm" style={{ color: theme.textMuted }}>
              等待{currentActingCountry}国决策...
            </span>
          </div>
        )}
      </div>
    </div>
  );
}, (prev, next) => {
  if (prev.currentRound !== next.currentRound) return false;
  if (prev.currentActingCountry !== next.currentActingCountry) return false;
  if (prev.isThinking !== next.isThinking) return false;
  if (prev.isProcessing !== next.isProcessing) return false;
  if (prev.pendingCountrySwitch !== next.pendingCountrySwitch) return false;
  if (prev.currentActions !== next.currentActions) return false;
  if (prev.currentContent.length !== next.currentContent.length) return false;
  if (prev.currentThinking.length !== next.currentThinking.length) return false;
  return true;
});

export default ThinkingChain;
