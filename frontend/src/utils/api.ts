/**
 * API客户端 - 基于axios封装
 * 统一管理游戏、地图、AI、存档等所有后端接口
 */
import axios from "axios";
import { API_BASE } from "./apiBase";

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

// 响应拦截器：自动解包data，统一错误处理
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error("API Error:", error);
    throw error;
  }
);

/** URL编码辅助函数 */
function enc(val: string): string {
  return encodeURIComponent(val);
}

export default api;

// 游戏相关接口
export const gameApi = {
  initGame: () => api.post("/game/init"),
  getState: () => api.get("/game/state"),
  getBlocks: (country?: string) => api.get("/game/blocks", { params: { country } }),
  getBlock: (name: string) => api.get(`/game/blocks/${enc(name)}`),
  getCountry: (name: string) => api.get(`/game/countries/${enc(name)}`),
  executeAction: (data: any) => api.post("/game/action", data),
  sendMessage: (data: any) => api.post("/game/message", data),
  nextRound: () => api.post("/game/next-round"),
  getFog: (country: string) => api.get(`/game/fog/${enc(country)}`),
  getNarrative: () => api.get("/game/narrative"),
  getGenerals: (aliveOnly = true) => api.get("/game/generals", { params: { alive_only: aliveOnly } }),
  getRelations: () => api.get("/game/relations"),
  getMemories: (country: string) => api.get(`/game/memories/${enc(country)}`),
  getHistory: (limit = 50) => api.get("/game/history", { params: { limit } }),
  aiTurn: (country: string) => api.post(`/game/ai-turn/${enc(country)}`),
};

// 地图相关接口
export const mapApi = {
  getGeoJSON: () => api.get("/map/geojson"),
  getBlocksSummary: () => api.get("/map/blocks-summary"),
};

// AI相关接口
export const aiApi = {
  getStatus: () => api.get("/ai/status"),
  checkConfig: () => api.get("/ai/check"),
  testConnection: (data: any) => api.post("/ai/test-connection", data),
  testConnectionByRole: (role: string) => api.post(`/ai/test-connection/${enc(role)}`),
  saveConfig: (data: any) => api.post("/ai/config", data),
  thinkAndAct: (country: string) => api.post(`/ai/think-and-act/${enc(country)}`),
};

// 存档相关接口
export const saveApi = {
  list: () => api.get("/save/list"),
  manual: (data?: any) => api.post("/save/manual", data),
  autosave: () => api.post("/save/autosave"),
  load: (saveId: string) => api.post(`/save/load/${enc(saveId)}`),
  delete: (saveId: string) => api.delete(`/save/${enc(saveId)}`),
  count: () => api.get("/save/count"),
};
