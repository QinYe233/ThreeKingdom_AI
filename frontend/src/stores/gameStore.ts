import { create, createSelector } from "zustand";
import type { GameState, Country, Block, General, Relation, Narrative, BattleResult } from "../types/game";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

interface AIResult {
  country: string;
  goal: string;
  actions_executed: number;
  results: any[];
}

interface ThinkingRecord {
  round: number;
  country: string;
  thinking: string;
  content: string;
  actions: string[];
}

interface GameStore {
  initialized: boolean;
  gameState: GameState | null;
  selectedBlock: string | null;
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

  initGame: () => Promise<void>;
  fetchState: () => Promise<void>;
  fetchBlocks: (country?: string) => Promise<Record<string, Block>>;
  fetchGenerals: () => Promise<void>;
  fetchNarrative: () => Promise<void>;
  nextRound: () => Promise<Narrative | null>;
  executeNextCountry: () => Promise<AIResult | null>;
  executeNextCountryStreaming: () => Promise<AIResult | null>;
  completeCountrySwitch: () => void;
  selectBlock: (name: string) => void;
}

const COUNTRY_ORDER = ["魏", "蜀", "吴"];
const MAX_NARRATIVES = 50;
const MAX_THINKING_RECORDS = 100;
const MAX_AI_RESULTS = 20;

// Optimized selectors to prevent unnecessary re-renders
export const selectGameState = createSelector(
  (state: GameStore) => state,
  (state) => state.gameState
);

export const selectCountries = createSelector(
  (state: GameStore) => state.gameState,
  (gameState) => gameState?.countries || {}
);

export const selectBlocks = createSelector(
  (state: GameStore) => state.gameState,
  (gameState) => gameState?.blocks || {}
);

export const selectCurrentRound = createSelector(
  (state: GameStore) => state.gameState,
  (gameState) => gameState?.round || 0
);

export const useGameStore = create<GameStore>((set, get) => ({
  initialized: false,
  gameState: null,
  selectedBlock: null,
  narrative: null,
  narratives: [],
  generals: [],
  history: [],
  battleResults: [],
  aiResults: [],
  thinkingRecords: [],
  currentActingCountry: "魏",
  lastActingCountry: "魏",
  isThinking: false,
  currentThinking: "",
  currentContent: "",
  isProcessing: false,
  currentActions: [],
  pendingCountrySwitch: false,
  completedCountryName: null,

  initGame: async () => {
    const res = await fetch(`${API_BASE}/game/init`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to initialize game");
    set({ 
      initialized: true, 
      narratives: [], 
      thinkingRecords: [], 
      currentActingCountry: "魏",
      pendingCountrySwitch: false,
      completedCountryName: null,
      isProcessing: false,
      isThinking: false,
    });
    await get().fetchState();
    await get().fetchGenerals();
  },

  fetchState: async () => {
    const res = await fetch(`${API_BASE}/game/state`);
    const data = await res.json();
    set({ gameState: data });
  },

  fetchBlocks: async (country?: string): Promise<Record<string, Block>> => {
    const url = country ? `${API_BASE}/game/blocks?country=${encodeURIComponent(country)}` : `${API_BASE}/game/blocks`;
    const res = await fetch(url);
    const data = await res.json();
    return data.blocks || {};
  },

  fetchGenerals: async () => {
    const res = await fetch(`${API_BASE}/game/generals?alive_only=true`);
    const data = await res.json();
    set({ generals: data.generals || [] });
  },

  fetchNarrative: async () => {
    const res = await fetch(`${API_BASE}/game/narrative`);
    const data = await res.json();
    set({ narrative: data });
  },

  nextRound: async (): Promise<Narrative | null> => {
    const res = await fetch(`${API_BASE}/game/next-round`, { method: "POST" });
    if (!res.ok) {
      console.error("nextRound failed:", res.status, await res.text());
      return null;
    }
    const data = await res.json();
    set((state) => {
      const newNarratives = data.narrative ? [...state.narratives, data.narrative] : state.narratives;
      return {
        narrative: data.narrative,
        narratives: newNarratives.slice(-MAX_NARRATIVES),
        currentActingCountry: "魏",
      };
    });
    await get().fetchState();
    await get().fetchGenerals();
    return data.narrative;
  },

  executeNextCountry: async (): Promise<AIResult | null> => {
    const { currentActingCountry, gameState, isProcessing } = get();
    if (!gameState || isProcessing) return null;

    set({ isProcessing: true });

    const actingCountry = currentActingCountry;
    let result: AIResult | null = null;

    try {
      const res = await fetch(`${API_BASE}/game/ai-turn/${encodeURIComponent(actingCountry)}`, { method: "POST" });
      if (!res.ok) {
        console.error("executeNextCountry failed:", res.status);
        set({ isProcessing: false });
        return null;
      }
      const data = await res.json();
      result = data;

      const actionSummaries: string[] = [];
      if (data.results) {
        for (const r of data.results) {
          const action = r.action;
          const params = r.parameters || {};
          const rResult = r.result || {};
          if (action === "attack") {
            const from = params.from || "?";
            const to = params.to || "?";
            const troops = params.troops || 0;
            if (rResult.battle_result?.block_captured) {
              actionSummaries.push(`⚔ 攻占${to}（从${from}出兵${troops}）`);
            } else {
              actionSummaries.push(`⚔ 进攻${to}受挫（从${from}出兵${troops}）`);
            }
          } else if (action === "recruit") {
            const block = params.block || "?";
            const recruited = rResult.troops_recruited || 0;
            actionSummaries.push(`🗡 于${block}征兵${recruited}`);
          } else if (action === "tax") {
            const gold = rResult.gold_earned || 0;
            actionSummaries.push(`💰 征税得金${gold}`);
          } else if (action === "develop") {
            const block = params.block || "?";
            const inc = rResult.manpower_increase || 0;
            actionSummaries.push(`🏗 发展${block}（人力+${inc}）`);
          } else if (action === "move") {
            const from = params.from || "?";
            const to = params.to || "?";
            const troops = params.troops || 0;
            actionSummaries.push(`➡ 调兵${troops}从${from}至${to}`);
          } else if (action === "harass") {
            const to = params.to || "?";
            actionSummaries.push(`🏹 骚扰${to}`);
          } else if (action === "declare_emperor") {
            actionSummaries.push(`👑 称帝！`);
          } else if (action === "move_capital") {
            actionSummaries.push(`🏛 迁都至${params.new_capital || "?"}`);
          }
        }
      }

      const currentRound = gameState.round;
      const existingRecord = get().thinkingRecords.find(
        r => r.round === currentRound && r.country === actingCountry
      );

      if (actionSummaries.length > 0) {
        if (existingRecord) {
          set((state) => ({
            thinkingRecords: state.thinkingRecords.map(r =>
              r.round === currentRound && r.country === actingCountry
                ? { ...r, actions: [...r.actions, ...actionSummaries] }
                : r
            ),
          }));
        } else {
          set((state) => ({
            thinkingRecords: [...state.thinkingRecords, {
              round: currentRound,
              country: actingCountry,
              thinking: "",
              content: "",
              actions: actionSummaries,
            }],
          }));
        }
      }

      const currentIndex = COUNTRY_ORDER.indexOf(actingCountry);
      const nextIndex = (currentIndex + 1) % COUNTRY_ORDER.length;
      const nextCountry = COUNTRY_ORDER[nextIndex];

      set({
        aiResults: [...get().aiResults.filter(r => r.country !== actingCountry), data],
        currentActingCountry: nextCountry,
        lastActingCountry: actingCountry,
        currentThinking: "",
        currentContent: "",
        currentActions: [],
      });

      await get().fetchState();
    } catch (e) {
      console.error("executeNextCountry error:", e);
    }

    set({ isProcessing: false });
    return result;
  },

  executeNextCountryStreaming: async (): Promise<AIResult | null> => {
    const { currentActingCountry, gameState, isProcessing } = get();
    if (!gameState || isProcessing) return null;

    const actingCountry = currentActingCountry;
    const currentRound = gameState.round;

    set({ isProcessing: true, isThinking: true, currentThinking: "", currentContent: "", currentActions: [] });

    let result: AIResult | null = null;

    try {
      const res = await fetch(`${API_BASE}/ai/think-and-act/${encodeURIComponent(actingCountry)}`, { method: "POST" });
      const reader = res.body?.getReader();
      if (!reader) {
        set({ isProcessing: false, isThinking: false });
        return null;
      }

      const decoder = new TextDecoder();
      let thinking = "";
      let content = "";
      const actions: string[] = [];
      const results: any[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value, { stream: true });
        const lines = text.split("\n");

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;

          try {
            const data = JSON.parse(jsonStr);

            if (data.type === "thinking") {
              thinking += data.content || "";
              set({ currentThinking: thinking });
            } else if (data.type === "content") {
              content += data.content || "";
              set({ currentContent: content });
            } else if (data.type === "thinking_end") {
              thinking = data.thinking || thinking;
              content = data.content || content;
              set({ currentThinking: thinking, currentContent: content, isThinking: false });
            } else if (data.type === "action") {
              const action = data.action;
              const params = data.parameters || {};
              const rResult = data.result || {};
              let actionSummary = "";

              if (action === "attack") {
                const from = params.from || "?";
                const to = params.to || "?";
                const troops = params.troops || 0;
                if (rResult.battle_result?.block_captured) {
                  actionSummary = `⚔ 攻占${to}（从${from}出兵${troops}）`;
                } else {
                  actionSummary = `⚔ 进攻${to}受挫（从${from}出兵${troops}）`;
                }
              } else if (action === "recruit") {
                const block = params.block || "?";
                const recruited = rResult.troops_recruited || 0;
                actionSummary = `🗡 于${block}征兵${recruited}`;
              } else if (action === "tax") {
                const gold = rResult.gold_earned || 0;
                actionSummary = `💰 征税得金${gold}`;
              } else if (action === "develop") {
                const block = params.block || "?";
                const inc = rResult.manpower_increase || 0;
                actionSummary = `🏗 发展${block}（人力+${inc}）`;
              } else if (action === "move") {
                const from = params.from || "?";
                const to = params.to || "?";
                const troops = params.troops || 0;
                actionSummary = `➡ 调兵${troops}从${from}至${to}`;
              } else if (action === "harass") {
                const to = params.to || "?";
                actionSummary = `🏹 骚扰${to}`;
              } else if (action === "declare_emperor") {
                actionSummary = `👑 称帝！`;
              } else if (action === "move_capital") {
                actionSummary = `🏛 迁都至${params.new_capital || "?"}`;
              }

              if (actionSummary) {
                actions.push(actionSummary);
                set({ currentActions: [...actions] });
              }

              results.push({
                action,
                parameters: params,
                result: rResult,
              });

              if (action === "attack" && rResult.battle_result?.block_captured) {
                await get().fetchState();
              }
            } else if (data.type === "end") {
              result = {
                country: data.country,
                goal: "",
                actions_executed: data.actions_executed,
                results: data.results || results,
              };
            }
          } catch {}
        }
      }

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

      const currentIndex = COUNTRY_ORDER.indexOf(actingCountry);
      const nextIndex = (currentIndex + 1) % COUNTRY_ORDER.length;
      const nextCountry = COUNTRY_ORDER[nextIndex];

      set((state) => {
        const newAiResults = result ? [...state.aiResults.filter(r => r.country !== actingCountry), result] : state.aiResults;
        return {
          aiResults: newAiResults.slice(-MAX_AI_RESULTS),
          pendingCountrySwitch: true,
          completedCountryName: actingCountry,
          lastActingCountry: actingCountry,
        };
      });

      await get().fetchState();
    } catch (e) {
      console.error("executeNextCountryStreaming error:", e);
    }

    set({ isProcessing: false, isThinking: false });
    return result;
  },

  completeCountrySwitch: () => {
    const { currentActingCountry, completedCountryName } = get();
    const currentIndex = COUNTRY_ORDER.indexOf(completedCountryName || currentActingCountry);
    const nextIndex = (currentIndex + 1) % COUNTRY_ORDER.length;
    const nextCountry = COUNTRY_ORDER[nextIndex];

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
}));
