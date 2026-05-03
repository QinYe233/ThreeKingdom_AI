import { create } from "zustand";
import type { GameState, Block, General, Narrative, BattleResult, ThinkingRecord } from "../types/game";
import { gameApi } from "../utils/api";
import { API_BASE } from "../utils/apiBase";
import { COUNTRY_ORDER } from "../theme";
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

const MAX_NARRATIVES = 50;
const MAX_THINKING_RECORDS = 100;
const MAX_AI_RESULTS = 20;
const FIRST_COUNTRY = COUNTRY_ORDER[0];

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
  currentActingCountry: FIRST_COUNTRY,
  lastActingCountry: FIRST_COUNTRY,
  isThinking: false,
  currentThinking: "",
  currentContent: "",
  isProcessing: false,
  currentActions: [],
  pendingCountrySwitch: false,
  completedCountryName: null,

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
    await get().fetchState();
    await get().fetchGenerals();
  },

  fetchState: async () => {
    const data = await gameApi.getState() as any;
    set({ gameState: data });
  },

  fetchBlocks: async (country?: string): Promise<Record<string, Block>> => {
    const data = await gameApi.getBlocks(country) as any;
    return data.blocks || {};
  },

  fetchGenerals: async () => {
    const data = await gameApi.getGenerals(true) as any;
    set({ generals: data.generals || [] });
  },

  fetchNarrative: async () => {
    const data = await gameApi.getNarrative() as any;
    set({ narrative: data });
  },

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
      await get().fetchState();
      await get().fetchGenerals();
      return data.narrative;
    } catch (e) {
      console.error("nextRound failed:", e);
      return null;
    }
  },

  executeNextCountry: async (): Promise<AIResult | null> => {
    const { currentActingCountry, gameState, isProcessing } = get();
    if (!gameState || isProcessing) return null;

    set({ isProcessing: true });

    const actingCountry = currentActingCountry;
    let result: AIResult | null = null;

    try {
      const data: any = await gameApi.aiTurn(actingCountry);
      result = data;

      const actionSummaries: string[] = [];
      if (data.results) {
        for (const r of data.results) {
          const summary = generateActionSummary(r.action, r.parameters || {}, r.result || {});
          if (summary) actionSummaries.push(summary);
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

      const nextCountry = getNextActiveCountry(actingCountry, get().gameState?.countries);

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
              const summary = generateActionSummary(data.action, data.parameters || {}, data.result || {});
              if (summary) {
                actions.push(summary);
                set({ currentActions: [...actions] });
              }

              results.push({
                action: data.action,
                parameters: data.parameters,
                result: data.result,
              });

              if (data.action === "attack" && data.result?.battle_result?.block_captured) {
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
          } catch (e) {
            console.error("SSE parse error:", e);
          }
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
}));
