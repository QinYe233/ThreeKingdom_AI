import { useEffect, useState, useCallback, useRef, useMemo, memo } from "react";
import MapCanvas from "./components/Map/MapCanvas";
import Settings from "./components/UI/Settings";
import CountryPanel from "./components/UI/CountryPanel";
import BlockDetail from "./components/UI/BlockDetail";
import ThinkingChain from "./components/UI/ThinkingChain";
import HistoryPanel from "./components/UI/HistoryPanel";
import DiplomacyPanel from "./components/UI/DiplomacyPanel";
import ChroniclerPanel from "./components/UI/ChroniclerPanel";
import SaveLoadPanel from "./components/UI/SaveLoadPanel";
import { useGameStore } from "./stores/gameStore";
import type { Block, ThinkingRecord, DiplomaticEvent } from "./types/game";
import { THEME_COLORS, COUNTRY_COLORS, COUNTRY_ORDER } from "./theme";
import { mapApi, gameApi, aiApi } from "./utils/api";

const Header = memo(function Header({
  gameState,
  currentActingCountry,
  isThinking,
  isProcessing,
  autoPlay,
  showHistory,
  showSaveLoad,
  showDiplomacy,
  showChronicler,
  theme,
  onToggleHistory,
  onToggleSaveLoad,
  onToggleDiplomacy,
  onToggleChronicler,
  onToggleAutoPlay,
  onNextAction,
}: {
  gameState: any;
  currentActingCountry: string;
  isThinking: boolean;
  isProcessing: boolean;
  autoPlay: boolean;
  showHistory: boolean;
  showSaveLoad: boolean;
  showDiplomacy: boolean;
  showChronicler: boolean;
  theme: any;
  onToggleHistory: () => void;
  onToggleSaveLoad: () => void;
  onToggleDiplomacy: () => void;
  onToggleChronicler: () => void;
  onToggleAutoPlay: () => void;
  onNextAction: () => void;
}) {
  return (
    <header className="border-b px-4 py-2 flex items-center justify-between z-30" style={{ backgroundColor: theme.header, borderColor: theme.border }}>
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-title" style={{ color: theme.accent }}>千秋弈</h1>
        {gameState && (
          <span className="text-sm" style={{ color: theme.textMuted }}>
            第{gameState.round}回合 · {gameState.timeline.year}年{gameState.timeline.month}月
          </span>
        )}
        <span
          className="text-sm px-2 py-0.5 rounded animate-pulse"
          style={{ color: "#fff", backgroundColor: COUNTRY_COLORS[currentActingCountry] || theme.accent }}
        >
          {isThinking ? `💭 ${currentActingCountry}思考中` : `▶ ${currentActingCountry}待命`}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={onToggleHistory}
          className="px-3 py-1.5 rounded text-sm cursor-pointer transition-all duration-200"
          style={{ backgroundColor: showHistory ? theme.accent : theme.border, color: showHistory ? "#fff" : theme.text }}
        >
          历史
        </button>
        <button
          onClick={onToggleDiplomacy}
          className="px-3 py-1.5 rounded text-sm cursor-pointer transition-all duration-200"
          style={{ backgroundColor: showDiplomacy ? theme.accent : theme.border, color: showDiplomacy ? "#fff" : theme.text }}
        >
          外交
        </button>
        <button
          onClick={onToggleChronicler}
          className="px-3 py-1.5 rounded text-sm cursor-pointer transition-all duration-200"
          style={{ backgroundColor: showChronicler ? theme.accent : theme.border, color: showChronicler ? "#fff" : theme.text }}
        >
          史官
        </button>
        <button
          onClick={onToggleSaveLoad}
          className="px-3 py-1.5 rounded text-sm cursor-pointer transition-all duration-200"
          style={{ backgroundColor: showSaveLoad ? theme.accent : theme.border, color: showSaveLoad ? "#fff" : theme.text }}
        >
          存档
        </button>
        <button
          onClick={onToggleAutoPlay}
          className="px-3 py-1.5 rounded text-sm cursor-pointer transition-all duration-200"
          style={{
            backgroundColor: autoPlay ? "#dc2626" : theme.border,
            color: autoPlay ? "#fff" : theme.text
          }}
        >
          {autoPlay ? "停止" : "自动"}
        </button>
        <button
          onClick={onNextAction}
          disabled={isProcessing || autoPlay}
          className="px-4 py-1.5 text-white rounded cursor-pointer disabled:opacity-50 text-sm transition-all duration-200 hover:opacity-80"
          style={{ backgroundColor: theme.accent }}
        >
          {isProcessing ? "处理中..." : `推进: ${currentActingCountry}`}
        </button>
      </div>
    </header>
  );
});

const InitScreen = memo(function InitScreen({
  theme,
  initLoading,
  showSettings,
  showSaveLoad,
  onInit,
  onShowSettings,
  onShowSaveLoad,
  onCloseSettings,
  onCloseSaveLoad,
}: {
  theme: any;
  initLoading: boolean;
  showSettings: boolean;
  showSaveLoad: boolean;
  onInit: () => void;
  onShowSettings: () => void;
  onShowSaveLoad: () => void;
  onCloseSettings: () => void;
  onCloseSaveLoad: () => void;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: theme.bg }}>
      <div className="text-center space-y-8">
        <h1 className="text-5xl font-title" style={{ color: theme.accent, letterSpacing: "0.1em" }}>
          千秋弈·群雄逐鹿
        </h1>
        <div className="flex flex-col gap-4 items-center">
          <button
            onClick={onInit}
            disabled={initLoading}
            className="btn-breathe px-12 py-4 text-white text-xl rounded-lg cursor-pointer disabled:opacity-50 transition-all duration-300 hover:scale-105 font-subtitle"
            style={{ backgroundColor: theme.accent, minWidth: 200 }}
          >
            {initLoading ? "初始化中..." : "开始"}
          </button>
          <button
            onClick={onShowSettings}
            disabled={initLoading}
            className="btn-breathe px-12 py-3 text-lg rounded-lg cursor-pointer transition-all duration-300 hover:scale-105 disabled:opacity-50 font-subtitle"
            style={{ backgroundColor: theme.border, color: theme.text, minWidth: 200 }}
          >
            设置
          </button>
          <button
            onClick={onShowSaveLoad}
            disabled={initLoading}
            className="btn-breathe px-12 py-3 text-lg rounded-lg cursor-pointer transition-all duration-300 hover:scale-105 disabled:opacity-50 font-subtitle"
            style={{ backgroundColor: theme.border, color: theme.text, minWidth: 200 }}
          >
            存档
          </button>
        </div>
        {initLoading && (
          <div style={{ color: theme.textMuted }} className="font-body">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: theme.accent }}></div>
            <p className="mt-2">正在初始化游戏世界，请稍候...</p>
          </div>
        )}
      </div>
      {showSettings && (
        <Settings
          onClose={onCloseSettings}
          onComplete={() => {}}
        />
      )}
      {showSaveLoad && (
        <SaveLoadPanel
          show={showSaveLoad}
          onClose={onCloseSaveLoad}
          theme={theme}
        />
      )}
    </div>
  );
});

export default function App() {
  const {
    initialized,
    gameState,
    selectedBlock,
    narratives,
    thinkingRecords,
    currentActingCountry,
    isThinking,
    isProcessing,
    currentThinking,
    currentContent,
    currentActions,
    pendingCountrySwitch,
    completedCountryName,
    initGame,
    nextRound,
    executeNextCountryStreaming,
    completeCountrySwitch,
    selectBlock,
  } = useGameStore();

  const [geojson, setGeojson] = useState<any>(null);
  const [blocksData, setBlocksData] = useState<Record<string, Block>>({});
  const [initLoading, setInitLoading] = useState(false);
  const [autoPlay, setAutoPlay] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showSaveLoad, setShowSaveLoad] = useState(false);
  const [showNoConfigWarning, setShowNoConfigWarning] = useState(false);
  const [leftSidebarHidden, setLeftSidebarHidden] = useState(false);
  const [mapAnimations, setMapAnimations] = useState<any[]>([]);
  const [showChronicler, setShowChronicler] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showDiplomacy, setShowDiplomacy] = useState(false);
  const [relations, setRelations] = useState<Record<string, any>>({});
  const [diplomaticEvents, setDiplomaticEvents] = useState<DiplomaticEvent[]>([]);
  const [selectedHistoryRecord, setSelectedHistoryRecord] = useState<ThinkingRecord | null>(null);

  const autoPlayRef = useRef(false);
  const autoPlayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  autoPlayRef.current = autoPlay;

  const theme = THEME_COLORS;

  useEffect(() => {
    mapApi.getGeoJSON()
      .then(setGeojson)
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (initialized) {
      fetchBlocksData();
      fetchRelations();
    }
  }, [initialized, gameState?.round]);

  const fetchBlocksData = useCallback(async () => {
    try {
      const data: any = await gameApi.getBlocks();
      setBlocksData(data.blocks || {});
    } catch (e) {
      console.error(e);
    }
  }, []);

  const fetchRelations = useCallback(async () => {
    try {
      const data: any = await gameApi.getRelations();
      setRelations(data);
    } catch (e) {
      console.error(e);
    }
  }, []);

  // Memoized computed values to prevent unnecessary recalculations
  const currentRound = useMemo(() => gameState?.round || 0, [gameState]);
  const currentRecord = useMemo(() => thinkingRecords.find(r => r.round === currentRound && r.country === currentActingCountry), [thinkingRecords, currentRound, currentActingCountry]);
  const selectedBlockData = useMemo(() => selectedBlock ? blocksData[selectedBlock] : null, [selectedBlock, blocksData]);

  const handleInit = useCallback(async () => {
    setInitLoading(true);
    try {
      const configData: any = await aiApi.checkConfig();

      if (!configData.all_configured) {
        setShowNoConfigWarning(true);
        setInitLoading(false);
        return;
      }

      await initGame();
      await fetchBlocksData();
    } catch (e) {
      console.error(e);
      try {
        await initGame();
        await fetchBlocksData();
      } catch (e2) {
        console.error(e2);
      }
    }
    setInitLoading(false);
  }, [initGame, fetchBlocksData]);

  const generateAnimations = useCallback((result: any, country: string) => {
    if (!result || !result.results) return;

    const newAnimations: any[] = [];
    for (const r of result.results) {
      if (r.action === "recruit" && r.parameters?.block) {
        newAnimations.push({
          type: "recruit",
          block: r.parameters.block,
          value: r.result?.troops_recruited || 0,
          country,
          timestamp: Date.now(),
        });
      } else if (r.action === "attack" && r.parameters?.from && r.parameters?.to) {
        newAnimations.push({
          type: "attack",
          from: r.parameters.from,
          to: r.parameters.to,
          success: r.result?.battle_result?.block_captured || false,
          country,
          timestamp: Date.now(),
        });
      } else if (r.action === "tax") {
        newAnimations.push({
          type: "tax",
          country,
          value: r.result?.gold_earned || 0,
          timestamp: Date.now(),
        });
      } else if (r.action === "develop" && r.parameters?.block) {
        newAnimations.push({
          type: "develop",
          block: r.parameters.block,
          value: r.result?.manpower_increase || 0,
          country,
          timestamp: Date.now(),
        });
      } else if (r.action === "send_message") {
        const event: DiplomaticEvent = {
          round: gameState?.round || 1,
          from_country: country,
          to_country: r.parameters?.to_country || "",
          event_type: "外交信函",
          content: r.parameters?.content || "",
          visibility: r.parameters?.visibility || "private",
        };
        setDiplomaticEvents(prev => [...prev, event]);
      }
    }
    if (newAnimations.length > 0) {
      setMapAnimations(prev => [...prev, ...newAnimations]);
      setTimeout(() => {
        setMapAnimations(prev => prev.filter(a => Date.now() - a.timestamp < 5000));
      }, 5000);
    }
  }, [gameState?.round]);

  const isLastActiveCountry = useCallback((country: string, countries: Record<string, any> | undefined) => {
    if (!countries) return country === COUNTRY_ORDER[COUNTRY_ORDER.length - 1];
    const activeCountries = COUNTRY_ORDER.filter(c => {
      const cData = countries[c];
      return cData && !cData.is_defeated;
    });
    if (activeCountries.length === 0) return true;
    return country === activeCountries[activeCountries.length - 1];
  }, []);

  const handleNextAction = useCallback(async () => {
    const state = useGameStore.getState();
    if (state.isProcessing || state.pendingCountrySwitch) return;

    const actingCountry = state.currentActingCountry;
    const result = await executeNextCountryStreaming();

    generateAnimations(result, actingCountry);
    await fetchBlocksData();

    if (isLastActiveCountry(actingCountry, state.gameState?.countries)) {
      await nextRound();
      await fetchRelations();
    } else {
      completeCountrySwitch();
    }
  }, [executeNextCountryStreaming, nextRound, generateAnimations, fetchBlocksData, fetchRelations, isLastActiveCountry, completeCountrySwitch]);

  const scheduleAutoPlay = useCallback(() => {
    if (autoPlayTimerRef.current) {
      clearTimeout(autoPlayTimerRef.current);
      autoPlayTimerRef.current = null;
    }

    if (!autoPlayRef.current) return;

    autoPlayTimerRef.current = setTimeout(async () => {
      if (!autoPlayRef.current) return;

      const state = useGameStore.getState();
      if (state.isProcessing || state.pendingCountrySwitch) {
        if (autoPlayRef.current) {
          scheduleAutoPlay();
        }
        return;
      }

      const actingCountry = state.currentActingCountry;
      const result = await executeNextCountryStreaming();

      generateAnimations(result, actingCountry);
      await fetchBlocksData();

      if (isLastActiveCountry(actingCountry, state.gameState?.countries)) {
        await nextRound();
        await fetchRelations();
      } else {
        completeCountrySwitch();
      }

      if (autoPlayRef.current) {
        scheduleAutoPlay();
      }
    }, 1000);
  }, [executeNextCountryStreaming, nextRound, generateAnimations, fetchBlocksData, fetchRelations, isLastActiveCountry, completeCountrySwitch]);

  useEffect(() => {
    if (autoPlay && initialized && !pendingCountrySwitch) {
      scheduleAutoPlay();
    } else {
      if (autoPlayTimerRef.current) {
        clearTimeout(autoPlayTimerRef.current);
        autoPlayTimerRef.current = null;
      }
    }

    return () => {
      if (autoPlayTimerRef.current) {
        clearTimeout(autoPlayTimerRef.current);
        autoPlayTimerRef.current = null;
      }
    };
  }, [autoPlay, initialized, pendingCountrySwitch, scheduleAutoPlay]);

  if (!initialized) {
    return (
      <InitScreen
        theme={theme}
        initLoading={initLoading}
        showSettings={showSettings}
        showSaveLoad={showSaveLoad}
        onInit={handleInit}
        onShowSettings={() => setShowSettings(true)}
        onShowSaveLoad={() => setShowSaveLoad(true)}
        onCloseSettings={() => setShowSettings(false)}
        onCloseSaveLoad={() => setShowSaveLoad(false)}
      />
    );
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: theme.bg }}>
      <Header
        gameState={gameState}
        currentActingCountry={currentActingCountry}
        isThinking={isThinking}
        isProcessing={isProcessing}
        autoPlay={autoPlay}
        showHistory={showHistory}
        showSaveLoad={showSaveLoad}
        showDiplomacy={showDiplomacy}
        showChronicler={showChronicler}
        theme={theme}
        onToggleHistory={() => setShowHistory(prev => !prev)}
        onToggleSaveLoad={() => setShowSaveLoad(prev => !prev)}
        onToggleDiplomacy={() => setShowDiplomacy(prev => !prev)}
        onToggleChronicler={() => setShowChronicler(prev => !prev)}
        onToggleAutoPlay={() => setAutoPlay(prev => !prev)}
        onNextAction={handleNextAction}
      />

      <div className="flex-1 relative overflow-hidden">
        <div className="absolute inset-0">
          {geojson && (
            <MapCanvas
              geojson={geojson}
              blocksData={blocksData}
              countriesData={gameState?.countries}
              selectedBlock={selectedBlock}
              onSelectBlock={selectBlock}
              animations={mapAnimations}
            />
          )}
        </div>

        <div
          className="absolute top-0 left-0 h-full z-20 transition-transform duration-300"
          style={{
            transform: leftSidebarHidden ? 'translateX(-400px)' : 'translateX(0)',
            width: 400,
          }}
        >
          <ThinkingChain
            currentRound={currentRound}
            currentActingCountry={currentActingCountry}
            pendingCountrySwitch={pendingCountrySwitch}
            completedCountryName={completedCountryName}
            isThinking={isThinking}
            isProcessing={isProcessing}
            currentThinking={currentThinking}
            currentContent={currentContent}
            currentActions={currentActions}
            currentRecord={currentRecord}
            theme={theme}
          />
          <button
            onClick={() => setLeftSidebarHidden(true)}
            className="absolute top-1 right-1 z-10 w-5 h-5 rounded text-xs cursor-pointer"
            style={{ backgroundColor: theme.border, color: theme.textMuted }}
          >
            ◀
          </button>
        </div>

        {leftSidebarHidden && (
          <div
            className="absolute top-1/2 left-0 -translate-y-1/2 z-20 w-6 h-12 flex items-center justify-center cursor-pointer rounded-r"
            style={{ backgroundColor: theme.sidebar }}
            onClick={() => setLeftSidebarHidden(false)}
          >
            <span style={{ color: theme.textMuted, fontSize: 12 }}>▶</span>
          </div>
        )}

        <div
          className="absolute top-0 right-0 h-full z-20"
          style={{
            width: 280,
          }}
        >
          <div className="h-full flex flex-col" style={{ backgroundColor: theme.sidebar, borderLeft: `1px solid ${theme.border}` }}>
            {gameState && (
              <CountryPanel
                countries={gameState.countries}
                currentActingCountry={currentActingCountry}
                theme={theme}
              />
            )}

            <div className="border-b" style={{ borderColor: theme.border }}>
              <div className="px-3 py-2 text-sm font-subtitle font-bold" style={{ color: theme.text }}>区块详情</div>
              <div className="px-3 pb-3">
                <BlockDetail
                  block={selectedBlockData}
                  blockName={selectedBlock || ""}
                  theme={theme}
                />
              </div>
            </div>
          </div>
        </div>

        <HistoryPanel
          show={showHistory}
          thinkingRecords={thinkingRecords}
          selectedRecord={selectedHistoryRecord}
          onSelectRecord={setSelectedHistoryRecord}
          onClose={() => setShowHistory(false)}
          theme={theme}
        />

        <SaveLoadPanel
          show={showSaveLoad}
          onClose={() => setShowSaveLoad(false)}
          theme={theme}
        />

        <DiplomacyPanel
          show={showDiplomacy}
          relations={relations}
          diplomaticEvents={diplomaticEvents}
          onClose={() => setShowDiplomacy(false)}
          theme={theme}
        />

        <ChroniclerPanel
          show={showChronicler}
          narratives={narratives}
          onClose={() => setShowChronicler(false)}
          theme={theme}
        />
      </div>

      {showNoConfigWarning && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="rounded-lg p-6 w-[440px]" style={{ backgroundColor: theme.sidebar, border: `1px solid ${theme.accent}` }}>
            <h3 className="text-lg font-bold mb-4" style={{ color: theme.accent }}>AI 配置不完整</h3>
            <p className="mb-2 text-sm" style={{ color: theme.text }}>
              以下角色的 AI 模型尚未配置，将使用规则引擎自动决策：
            </p>
            <p className="mb-4 text-sm font-bold" style={{ color: theme.accent }}>
              {[...COUNTRY_ORDER, "史官"].join("、")}
            </p>
            <p className="mb-4 text-sm" style={{ color: theme.textMuted }}>
              你可以先开始游戏，之后在设置中补全配置。未配置的角色会使用内置规则进行决策。
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setShowNoConfigWarning(false)}
                className="flex-1 px-4 py-2 rounded cursor-pointer"
                style={{ backgroundColor: theme.border, color: theme.text }}
              >
                关闭
              </button>
              <button
                onClick={() => {
                  setShowNoConfigWarning(false);
                  setShowSettings(true);
                }}
                className="flex-1 px-4 py-2 text-white rounded cursor-pointer"
                style={{ backgroundColor: theme.accent }}
              >
                前往设置
              </button>
              <button
                onClick={async () => {
                  setShowNoConfigWarning(false);
                  setInitLoading(true);
                  try {
                    await initGame();
                    await fetchBlocksData();
                  } catch (e) {
                    console.error(e);
                  }
                  setInitLoading(false);
                }}
                className="flex-1 px-4 py-2 bg-green-700 hover:bg-green-600 text-white rounded cursor-pointer"
              >
                直接开始
              </button>
            </div>
          </div>
        </div>
      )}

      {showSettings && (
        <Settings
          onClose={() => setShowSettings(false)}
          onComplete={() => {}}
        />
      )}
    </div>
  );
}
