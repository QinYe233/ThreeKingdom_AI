/**
 * 游戏状态管理 - Zustand Store
 * 管理游戏初始化、SSE流式AI决策、势力切换、回合推进等核心状态
 */
import { create } from "zustand";
import gsap from "gsap";
import type { GameState, Block, General, Narrative, BattleResult, ThinkingRecord } from "../types/game";
import { gameApi, saveApi } from "../utils/api";
import { fetchSSE } from "../utils/sse";
import { COUNTRY_ORDER } from "../constants";
import { generateActionSummary, getNextActiveCountry } from "../utils/gameHelpers";

interface AIResult {
  country: string;
  goal: string;
  actions_executed: number;
  results: any[];
}

interface GameStore {
  initialized: boolean;
  gameState: GameState | null;
  selectedBlock: string | null;
  blocksData: Record<string, Block>;
  relations: Record<string, any>;
  narrative: Narrative | null;
  narratives: Narrative[];
  generals: General[];
  history: any[];
  battleResults: BattleResult[];
  aiResults: AIResult[];
  thinkingRecords: ThinkingRecord[];
  currentActingCountry: string;
  lastActingCountry: string;
  isThinking: boolean;
  currentThinking: string;
  currentContent: string;
  isProcessing: boolean;
  currentActions: string[];
  pendingCountrySwitch: boolean;
  completedCountryName: string | null;
  abortController: AbortController | null;

  initGame: () => Promise<void>;
  fetchState: () => Promise<void>;
  fetchBlocksData: () => Promise<void>;
  fetchRelations: () => Promise<void>;
  fetchGenerals: () => Promise<void>;
  fetchNarrative: () => Promise<void>;
  nextRound: () => Promise<Narrative | null>;
  executeNextCountryStreaming: () => Promise<AIResult | null>;
  completeCountrySwitch: () => void;
  selectBlock: (name: string) => void;
  loadSave: (saveId: string) => Promise<void>;
  abortSSE: () => void;
}

// 历史记录保留上限
const MAX_NARRATIVES = 50;
const MAX_THINKING_RECORDS = 100;
const MAX_AI_RESULTS = 20;
const FIRST_COUNTRY = COUNTRY_ORDER[0];

export const useGameStore = create<GameStore>((set, get) => ({
  initialized: false,
  gameState: null,
  selectedBlock: null,
  blocksData: {},
  relations: {},
  narrative: null,
  narratives: [],
  generals: [],
  history: [],
  battleResults: [],
  aiResults: [],
  thinkingRecords: [],
  currentActingCountry: FIRST_COUNTRY,
  lastActingCountry: FIRST_COUNTRY,
  isThinking: false,
  currentThinking: "",
  currentContent: "",
  isProcessing: false,
  currentActions: [],
  pendingCountrySwitch: false,
  completedCountryName: null,
  abortController: null,

  /** 初始化游戏 - 调用后端初始化接口，并行加载所有基础数据 */
  initGame: async () => {
    await gameApi.initGame();
    set({
      initialized: true,
      narratives: [],
      thinkingRecords: [],
      currentActingCountry: FIRST_COUNTRY,
      pendingCountrySwitch: false,
      completedCountryName: null,
      isProcessing: false,
      isThinking: false,
    });
    await Promise.all([
      get().fetchState(),
      get().fetchGenerals(),
      get().fetchBlocksData(),
      get().fetchRelations(),
    ]);
  },

  fetchState: async () => {
    const data = await gameApi.getState() as any;
    set({ gameState: data });
  },

  fetchBlocksData: async () => {
    try {
      const data = await gameApi.getBlocks() as any;
      set({ blocksData: data.blocks || {} });
    } catch (e) {
      console.error(e);
    }
  },

  fetchRelations: async () => {
    try {
      const data = await gameApi.getRelations() as any;
      set({ relations: data });
    } catch (e) {
      console.error(e);
    }
  },

  fetchGenerals: async () => {
    try {
      const data = await gameApi.getGenerals(true) as any;
      set({ generals: data.generals || [] });
    } catch (e) {
      console.error(e);
    }
  },

  fetchNarrative: async () => {
    try {
      const data = await gameApi.getNarrative() as any;
      set({ narrative: data });
    } catch (e) {
      console.error(e);
    }
  },

  /** 推进下一回合 - 重置当前势力为第一个，获取史官叙事 */
  nextRound: async (): Promise<Narrative | null> => {
    try {
      const data: any = await gameApi.nextRound();
      set((state) => {
        const newNarratives = data.narrative ? [...state.narratives, data.narrative] : state.narratives;
        return {
          narrative: data.narrative,
          narratives: newNarratives.slice(-MAX_NARRATIVES),
          currentActingCountry: FIRST_COUNTRY,
          pendingCountrySwitch: false,
          completedCountryName: null,
          isProcessing: false,
          isThinking: false,
          currentThinking: "",
          currentContent: "",
          currentActions: [],
        };
      });
      await Promise.all([
        get().fetchState(),
        get().fetchGenerals(),
        get().fetchRelations(),
      ]);
      return data.narrative;
    } catch (e) {
      console.error("nextRound failed:", e);
      return null;
    }
  },

  /**
   * 执行当前势力的SSE流式AI决策
   * 通过GSAP ticker节流合并高频chunk更新，避免级联重渲染
   * 低频事件（thinking_end、action）立即刷新
   */
  executeNextCountryStreaming: async (): Promise<AIResult | null> => {
    const { currentActingCountry, gameState, isProcessing } = get();
    if (!gameState || isProcessing) return null;

    const actingCountry = currentActingCountry;
    const currentRound = gameState.round;

    const controller = new AbortController();
    set({ isProcessing: true, isThinking: true, currentThinking: "", currentContent: "", currentActions: [], abortController: controller });

    let result: AIResult | null = null;
    let thinking = "";
    let content = "";
    const actions: string[] = [];

    // SSE节流：用GSAP ticker合并高频chunk更新，避免逐chunk set导致级联重渲染
    let pendingUpdate: Record<string, any> | null = null;
    const flushUpdate = () => {
      if (pendingUpdate) {
        set(pendingUpdate);
        pendingUpdate = null;
      }
    };
    gsap.ticker.add(flushUpdate);

    try {
      const results: any[] = [];

      await fetchSSE<any>(
        `/ai/think-and-act/${encodeURIComponent(actingCountry)}`,
        (data) => {
          if (data.type === "thinking") {
            thinking += data.content || "";
            pendingUpdate = { ...pendingUpdate, currentThinking: thinking };
          } else if (data.type === "content") {
            content += data.content || "";
            pendingUpdate = { ...pendingUpdate, currentContent: content };
          } else if (data.type === "thinking_end") {
            thinking = data.thinking || thinking;
            content = data.content || content;
            // thinking_end 是低频事件，立即刷新，并清空 pending 避免覆盖
            pendingUpdate = null;
            gsap.ticker.remove(flushUpdate);
            set({ currentThinking: thinking, currentContent: content, isThinking: false });
            gsap.ticker.add(flushUpdate);
          } else if (data.type === "action") {
            const summary = generateActionSummary(data.action, data.parameters || {}, data.result || {});
            if (summary) {
              actions.push(summary);
              // action 是低频事件，立即刷新，并清空 pending 避免覆盖
              pendingUpdate = null;
              gsap.ticker.remove(flushUpdate);
              set({ currentActions: [...actions] });
              gsap.ticker.add(flushUpdate);
            }

            results.push({
              action: data.action,
              parameters: data.parameters,
              result: data.result,
            });

            if (data.action === "attack" && data.result?.battle_result?.block_captured) {
              get().fetchState();
            }
          } else if (data.type === "end") {
            result = {
              country: data.country,
              goal: "",
              actions_executed: data.actions_executed,
              results: data.results || results,
            };
          }
        },
        { method: "POST", signal: controller.signal }
      );
    } catch (e) {
      // SSE 被中止时不推进游戏状态
      const aborted = e instanceof DOMException && e.name === "AbortError";
      if (!aborted) {
        console.error("executeNextCountryStreaming error:", e);
      }
    } finally {
      gsap.ticker.remove(flushUpdate);
      flushUpdate(); // 确保最后的 pending 数据被刷新
    }

    // 仅在未被中止时推进游戏状态
    const wasAborted = get().abortController === null && result === null;
    if (!wasAborted) {
      set((state) => {
        const existingRecord = state.thinkingRecords.find(
          r => r.round === currentRound && r.country === actingCountry
        );

        if (existingRecord) {
          return {
            thinkingRecords: state.thinkingRecords.map(r =>
              r.round === currentRound && r.country === actingCountry
                ? { ...r, thinking, content, actions: [...r.actions, ...actions] }
                : r
            ),
          };
        }

        return {
          thinkingRecords: [...state.thinkingRecords, {
            round: currentRound,
            country: actingCountry,
            thinking,
            content,
            actions,
          }].slice(-MAX_THINKING_RECORDS),
        };
      });

      set((state) => {
        const newAiResults = result ? [...state.aiResults.filter(r => r.country !== actingCountry), result] : state.aiResults;
        return {
          aiResults: newAiResults.slice(-MAX_AI_RESULTS),
          pendingCountrySwitch: true,
          completedCountryName: actingCountry,
          lastActingCountry: actingCountry,
        };
      });

      await Promise.all([
        get().fetchState(),
        get().fetchBlocksData(),
      ]);
    }

    set({ isProcessing: false, isThinking: false });
    return result;
  },

  /** 完成势力切换 - 将当前势力切换到下一个未灭亡的势力 */
  completeCountrySwitch: () => {
    const { completedCountryName, currentActingCountry } = get();
    const fromCountry = completedCountryName || currentActingCountry;
    const nextCountry = getNextActiveCountry(fromCountry, get().gameState?.countries);

    set({
      currentActingCountry: nextCountry,
      currentThinking: "",
      currentContent: "",
      currentActions: [],
      pendingCountrySwitch: false,
      completedCountryName: null,
    });
  },

  selectBlock: (name: string) => set({ selectedBlock: name }),

  /** 中止当前SSE请求 */
  abortSSE: () => {
    const { abortController } = get();
    if (abortController) {
      abortController.abort();
      set({ abortController: null, isProcessing: false, isThinking: false });
    }
  },

  /** 加载存档 - 中止SSE、重置状态、重新加载所有数据 */
  loadSave: async (saveId: string) => {
    // Abort any ongoing SSE before loading
    get().abortSSE();

    await saveApi.load(saveId);
    set({
      initialized: true,
      narratives: [],
      thinkingRecords: [],
      currentActingCountry: FIRST_COUNTRY,
      pendingCountrySwitch: false,
      completedCountryName: null,
      isProcessing: false,
      isThinking: false,
      currentThinking: "",
      currentContent: "",
      currentActions: [],
    });
    await Promise.all([
      get().fetchState(),
      get().fetchGenerals(),
      get().fetchBlocksData(),
      get().fetchRelations(),
    ]);
  },
}));
