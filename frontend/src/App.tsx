/**
 * 应用主组件 - 千秋弈三国策略游戏
 * 管理游戏初始化、SSE流式AI决策、自动播放、面板切换等核心流程
 */
import { useEffect, useState, useCallback, useMemo, memo } from "react";
import MapCanvas from "./components/Map/MapCanvas";
import Settings from "./components/UI/Settings";
import CountryPanel from "./components/UI/CountryPanel";
import BlockDetail from "./components/UI/BlockDetail";
import ThinkingChain from "./components/UI/ThinkingChain";
import HistoryPanel from "./components/UI/HistoryPanel";
import ChroniclerPanel from "./components/UI/ChroniclerPanel";
import SaveLoadPanel from "./components/UI/SaveLoadPanel";
import SplashScreen from "./components/UI/SplashScreen";
import InstructionsPanel from "./components/UI/InstructionsPanel";
import MusicPlayer from "./components/UI/MusicPlayer";
import { BreatheButton } from "./components/UI/BreatheButton";
import { useGameStore } from "./stores/gameStore";
import { useAudioStore } from "./stores/audioStore";
import { useAutoPlay } from "./hooks/useAutoPlay";
import { useMapAnimations } from "./hooks/useMapAnimations";
import { usePanelAnimation } from "./hooks/usePanelAnimation";
import type { ThinkingRecord } from "./types/game";
import { THEME_COLORS, COUNTRY_COLORS, COUNTRY_ORDER } from "./theme";
import { aiApi, mapApi, saveApi } from "./utils/api";
import { initApiBase } from "./utils/apiBase";

/** 顶部导航栏 - 显示回合信息、当前势力状态及操作按钮 */
const Header = memo(function Header({
  gameState,
  currentActingCountry,
  isThinking,
  isProcessing,
  autoPlay,
  showHistory,
  showSaveLoad,
  showChronicler,
  theme,
  onToggleHistory,
  onToggleSaveLoad,
  onToggleChronicler,
  onToggleAutoPlay,
  onNextAction,
  onShowInstructions,
  onShowSettings,
  onReturnToMenu,
}: {
  gameState: any;
  currentActingCountry: string;
  isThinking: boolean;
  isProcessing: boolean;
  autoPlay: boolean;
  showHistory: boolean;
  showSaveLoad: boolean;
  showChronicler: boolean;
  theme: any;
  onToggleHistory: () => void;
  onToggleSaveLoad: () => void;
  onToggleChronicler: () => void;
  onToggleAutoPlay: () => void;
  onNextAction: () => void;
  onShowInstructions: () => void;
  onShowSettings: () => void;
  onReturnToMenu: () => void;
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
        <MusicPlayer />
        <button
          onClick={onShowSettings}
          className="px-3 py-1.5 rounded text-sm cursor-pointer transition-colors duration-200"
          style={{ backgroundColor: theme.border, color: theme.text }}
        >
          设置
        </button>
        <button
          onClick={onReturnToMenu}
          className="px-3 py-1.5 rounded text-sm cursor-pointer transition-colors duration-200"
          style={{ backgroundColor: theme.border, color: theme.text }}
        >
          返回
        </button>
        <button
          onClick={onShowInstructions}
          className="px-3 py-1.5 rounded text-sm cursor-pointer transition-colors duration-200"
          style={{ backgroundColor: theme.border, color: theme.text }}
        >
          说明
        </button>
        <button
          onClick={onToggleHistory}
          className="px-3 py-1.5 rounded text-sm cursor-pointer transition-colors duration-200"
          style={{ backgroundColor: showHistory ? theme.accent : theme.border, color: showHistory ? "#fff" : theme.text }}
        >
          历史
        </button>
        <button
          onClick={onToggleChronicler}
          className="px-3 py-1.5 rounded text-sm cursor-pointer transition-colors duration-200"
          style={{ backgroundColor: showChronicler ? theme.accent : theme.border, color: showChronicler ? "#fff" : theme.text }}
        >
          史官
        </button>
        <button
          onClick={onToggleSaveLoad}
          className="px-3 py-1.5 rounded text-sm cursor-pointer transition-colors duration-200"
          style={{ backgroundColor: showSaveLoad ? theme.accent : theme.border, color: showSaveLoad ? "#fff" : theme.text }}
        >
          存档
        </button>
        <button
          onClick={onToggleAutoPlay}
          className="px-3 py-1.5 rounded text-sm cursor-pointer transition-colors duration-200"
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

/** 初始化界面 - 游戏开始前的主菜单 */
const InitScreen = memo(function InitScreen({
  theme,
  initLoading,
  showSettings,
  showSaveLoad,
  showInstructions,
  onInit,
  onShowSettings,
  onShowSaveLoad,
  onShowInstructions,
  onCloseSettings,
  onCloseSaveLoad,
  onCloseInstructions,
  onExit,
}: {
  theme: any;
  initLoading: boolean;
  showSettings: boolean;
  showSaveLoad: boolean;
  showInstructions: boolean;
  onInit: () => void;
  onShowSettings: () => void;
  onShowSaveLoad: () => void;
  onShowInstructions: () => void;
  onCloseSettings: () => void;
  onCloseSaveLoad: () => void;
  onCloseInstructions: () => void;
  onExit: () => void;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: theme.bg }}>
      <div className="text-center space-y-8">
        <h1 className="text-5xl font-title" style={{ color: theme.accent, letterSpacing: "0.1em" }}>
          千秋弈·群雄逐鹿
        </h1>
        <div className="flex flex-col gap-4 items-center">
          <BreatheButton
            onClick={onInit}
            disabled={initLoading}
            className="px-12 py-4 text-white text-xl rounded-lg cursor-pointer disabled:opacity-50 font-subtitle"
            style={{ backgroundColor: theme.accent, minWidth: 200 }}
          >
            {initLoading ? "初始化中..." : "开始"}
          </BreatheButton>
          <BreatheButton
            onClick={onShowSettings}
            disabled={initLoading}
            className="px-12 py-3 text-lg rounded-lg cursor-pointer disabled:opacity-50 font-subtitle"
            style={{ backgroundColor: theme.border, color: theme.text, minWidth: 200 }}
          >
            设置
          </BreatheButton>
          <BreatheButton
            onClick={onShowSaveLoad}
            disabled={initLoading}
            className="px-12 py-3 text-lg rounded-lg cursor-pointer disabled:opacity-50 font-subtitle"
            style={{ backgroundColor: theme.border, color: theme.text, minWidth: 200 }}
          >
            存档
          </BreatheButton>
          <BreatheButton
            onClick={onShowInstructions}
            disabled={initLoading}
            className="px-12 py-3 text-lg rounded-lg cursor-pointer disabled:opacity-50 font-subtitle"
            style={{ backgroundColor: theme.border, color: theme.text, minWidth: 200 }}
          >
            说明
          </BreatheButton>
          <BreatheButton
            onClick={onExit}
            disabled={initLoading}
            className="px-12 py-3 text-lg rounded-lg cursor-pointer disabled:opacity-50 font-subtitle"
            style={{ backgroundColor: theme.border, color: theme.textMuted, minWidth: 200 }}
          >
            退出
          </BreatheButton>
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
      <InstructionsPanel
        show={showInstructions}
        onClose={onCloseInstructions}
      />
    </div>
  );
});

export default function App() {
  const [splashComplete, setSplashComplete] = useState(false);
  // 低频变化的状态，直接从 store 解构
  const {
    initialized,
    gameState,
    selectedBlock,
    narratives,
    thinkingRecords,
    pendingCountrySwitch,
    initGame,
    nextRound,
    executeNextCountryStreaming,
    completeCountrySwitch,
    selectBlock,
    blocksData,
    fetchBlocksData,
    fetchRelations,
  } = useGameStore();

  // 高频变化的 SSE 状态，使用独立选择器避免过度重渲染
  const currentActingCountry = useGameStore(state => state.currentActingCountry);
  const isThinking = useGameStore(state => state.isThinking);
  const isProcessing = useGameStore(state => state.isProcessing);
  const currentThinking = useGameStore(state => state.currentThinking);
  const currentContent = useGameStore(state => state.currentContent);
  const currentActions = useGameStore(state => state.currentActions);

  // 音频系统
  const { play, initAudio } = useAudioStore();

  const [geojson, setGeojson] = useState<any>(null);
  const [initLoading, setInitLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showSaveLoad, setShowSaveLoad] = useState(false);
  const [showNoConfigWarning, setShowNoConfigWarning] = useState(false);
  const [showInstructions, setShowInstructions] = useState(false);
  const [leftSidebarHidden, setLeftSidebarHidden] = useState(false);
  const leftSidebarAnim = usePanelAnimation(!leftSidebarHidden, "left", 400, 0.3);
  const [showChronicler, setShowChronicler] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [selectedHistoryRecord, setSelectedHistoryRecord] = useState<ThinkingRecord | null>(null);
  const [aiSettings, setAiSettings] = useState({ streaming: true, deepThinking: true });
  const [returningToMenu, setReturningToMenu] = useState(false);

  // 从服务端获取AI设置（流式输出、深度思考），用于控制左侧面板显示
  useEffect(() => {
    (async () => {
      try {
        const data: any = await aiApi.getStatus();
        const configs = data.configs || {};
        // Use the first configured role's settings as default, or fallback to true
        const firstConfig = Object.values(configs)[0] as any;
        if (firstConfig) {
          setAiSettings({
            streaming: firstConfig.streaming ?? true,
            deepThinking: firstConfig.deep_thinking ?? true,
          });
        }
      } catch (e) {
        // Silently fallback to defaults
      }
    })();
  }, []);

  // useCallback 包裹 Header 回调，避免内联函数破坏 memo
  const toggleHistory = useCallback(() => setShowHistory(prev => !prev), []);
  const toggleSaveLoad = useCallback(() => setShowSaveLoad(prev => !prev), []);
  const toggleChronicler = useCallback(() => setShowChronicler(prev => !prev), []);
  const openInstructions = useCallback(() => setShowInstructions(true), []);
  const openSettings = useCallback(() => setShowSettings(true), []);

  /** 返回主菜单 - 中止SSE、自动存档、重置游戏状态 */
  const handleReturnToMenu = useCallback(async () => {
    if (isProcessing) {
      useGameStore.getState().abortSSE();
    }
    setReturningToMenu(true);
    let autosaveFailed = false;
    try {
      await saveApi.autosave();
    } catch (e) {
      console.error("Autosave failed:", e);
      autosaveFailed = true;
    }
    // Wait 1 second after save completes
    await new Promise(resolve => setTimeout(resolve, 1000));
    if (autosaveFailed) {
      console.warn("⚠️ Autosave failed — game state will be reset but the latest progress may not have been saved.");
    }
    // Reset game state
    useGameStore.setState({
      initialized: false,
      gameState: null,
      blocksData: {},
      narratives: [],
      thinkingRecords: [],
      currentActingCountry: COUNTRY_ORDER[0],
      pendingCountrySwitch: false,
      completedCountryName: null,
      isProcessing: false,
      isThinking: false,
    });
    setReturningToMenu(false);
  }, [isProcessing]);

  const theme = THEME_COLORS;

  // 地图动画
  const { mapAnimations, generateAnimations } = useMapAnimations();

  // 判断是否为最后一个活跃势力
  const isLastActiveCountry = useCallback((country: string, countries: Record<string, any> | undefined) => {
    if (!countries) return country === COUNTRY_ORDER[COUNTRY_ORDER.length - 1];
    const activeCountries = COUNTRY_ORDER.filter(c => {
      const cData = countries[c];
      return cData && !cData.is_defeated;
    });
    if (activeCountries.length === 0) return true;
    return country === activeCountries[activeCountries.length - 1];
  }, []);

  /** 统一执行步骤：执行当前势力AI → 生成动画 → 切换势力或推进回合 */
  const executeStep = useCallback(async () => {
    const state = useGameStore.getState();
    if (state.isProcessing || state.pendingCountrySwitch) return;

    const actingCountry = state.currentActingCountry;
    const result = await executeNextCountryStreaming();

    generateAnimations(result, actingCountry, state.gameState?.round || 1);

    if (isLastActiveCountry(actingCountry, state.gameState?.countries)) {
      await nextRound();
    } else {
      completeCountrySwitch();
    }
  }, [executeNextCountryStreaming, nextRound, generateAnimations, isLastActiveCountry, completeCountrySwitch]);

  // 自动播放
  const { autoPlay, toggleAutoPlay } = useAutoPlay(executeStep);

  // 初始化 API 地址（Tauri 环境下从 Rust 端获取动态端口）
  useEffect(() => {
    initApiBase().catch(console.error);
  }, []);

  // 加载 GeoJSON
  useEffect(() => {
    mapApi.getGeoJSON()
      .then(setGeojson)
      .catch(console.error);
  }, []);

  // 回合变化时刷新数据
  useEffect(() => {
    if (initialized) {
      fetchBlocksData();
      fetchRelations();
    }
  }, [initialized, gameState?.round, fetchBlocksData, fetchRelations]);

  // Memoized computed values
  const currentRound = useMemo(() => gameState?.round || 0, [gameState]);
  const selectedBlockData = useMemo(() => selectedBlock ? blocksData[selectedBlock] : null, [selectedBlock, blocksData]);

  const handleInit = useCallback(async () => {
    setInitLoading(true);
    try {
      const configData: any = await aiApi.checkConfig();

      if (!configData.all_configured) {
        setShowNoConfigWarning(true);
        return;
      }

      await initGame();
    } catch (e) {
      console.error(e);
      try {
        await initGame();
      } catch (e2) {
        console.error(e2);
      }
    } finally {
      setInitLoading(false);
    }
  }, [initGame]);

  // 启动画面完成后初始化音频并播放背景音乐
  useEffect(() => {
    if (splashComplete) {
      initAudio();
      play();
    }
  }, [splashComplete, initAudio, play]);

  // 启动画面
  const handleSplashComplete = useCallback(() => setSplashComplete(true), []);
  if (!splashComplete) {
    return <SplashScreen onComplete={handleSplashComplete} />;
  }

  // 退出游戏（Tauri环境调用Rust命令，浏览器环境关闭窗口）
  const handleExit = async () => {
    try {
      // 通过 Tauri command 直接退出：stop_backend() + std::process::exit(0)
      const { invoke } = await import("@tauri-apps/api/core");
      await invoke("exit_app");
    } catch {
      // 非 Tauri 环境（浏览器开发模式）
      window.close();
    }
  };

  if (!initialized) {
    return (
      <InitScreen
        theme={theme}
        initLoading={initLoading}
        showSettings={showSettings}
        showSaveLoad={showSaveLoad}
        showInstructions={showInstructions}
        onInit={handleInit}
        onShowSettings={() => setShowSettings(true)}
        onShowSaveLoad={() => setShowSaveLoad(true)}
        onShowInstructions={() => setShowInstructions(true)}
        onCloseSettings={() => setShowSettings(false)}
        onCloseSaveLoad={() => setShowSaveLoad(false)}
        onCloseInstructions={() => setShowInstructions(false)}
        onExit={handleExit}
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
        showChronicler={showChronicler}
        theme={theme}
        onToggleHistory={toggleHistory}
        onToggleSaveLoad={toggleSaveLoad}
        onToggleChronicler={toggleChronicler}
        onToggleAutoPlay={toggleAutoPlay}
        onNextAction={executeStep}
        onShowInstructions={openInstructions}
        onShowSettings={openSettings}
        onReturnToMenu={handleReturnToMenu}
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

        {aiSettings.streaming && aiSettings.deepThinking && (
        <div
          ref={leftSidebarAnim.panelRef}
          className="absolute top-0 left-0 h-full z-20"
          style={{
            width: 400,
          }}
        >
          <ThinkingChain
            currentRound={currentRound}
            currentActingCountry={currentActingCountry}
            pendingCountrySwitch={pendingCountrySwitch}
            isThinking={isThinking}
            isProcessing={isProcessing}
            currentThinking={currentThinking}
            currentContent={currentContent}
            currentActions={currentActions}
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
        )}

        {aiSettings.streaming && aiSettings.deepThinking && leftSidebarHidden && (
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
                  } catch (e) {
                    console.error(e);
                  } finally {
                    setInitLoading(false);
                  }
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
          inGame={true}
          onAiSettingsChange={(streaming, deepThinking) => setAiSettings({ streaming, deepThinking })}
        />
      )}

      <InstructionsPanel
        show={showInstructions}
        onClose={() => setShowInstructions(false)}
      />

      {returningToMenu && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="text-white text-lg">正在保存当前存档...</div>
        </div>
      )}
    </div>
  );
}
