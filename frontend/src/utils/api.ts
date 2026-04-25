import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error("API Error:", error);
    throw error;
  }
);

export default api;

export const gameApi = {
  initGame: () => api.post("/game/init"),
  getState: () => api.get("/game/state"),
  getBlocks: (country?: string) => api.get("/game/blocks", { params: { country } }),
  getBlock: (name: string) => api.get(`/game/blocks/${name}`),
  getCountry: (name: string) => api.get(`/game/countries/${name}`),
  executeAction: (data: any) => api.post("/game/action", data),
  sendMessage: (data: any) => api.post("/game/message", data),
  nextRound: () => api.post("/game/next-round"),
  getFog: (country: string) => api.get(`/game/fog/${country}`),
  getNarrative: () => api.get("/game/narrative"),
  getGenerals: (aliveOnly = true) => api.get("/game/generals", { params: { alive_only: aliveOnly } }),
  getRelations: () => api.get("/game/relations"),
  getMemories: (country: string) => api.get(`/game/memories/${country}`),
  getHistory: (limit = 50) => api.get("/game/history", { params: { limit } }),
};

export const mapApi = {
  getGeoJSON: () => api.get("/map/geojson"),
  getBlocksSummary: () => api.get("/map/blocks-summary"),
};

export const aiApi = {
  getStatus: () => api.get("/ai/status"),
  checkConfig: () => api.get("/ai/check"),
  testConnection: (data: any) => api.post("/ai/test-connection", data),
  saveConfig: (data: any) => api.post("/ai/config", data),
  thinkAndAct: (country: string) => api.post(`/ai/think-and-act/${country}`),
};

export const saveApi = {
  list: () => api.get("/save/list"),
  manual: (data?: any) => api.post("/save/manual", data),
  load: (saveId: string) => api.post(`/save/load/${saveId}`),
  delete: (saveId: string) => api.delete(`/save/${saveId}`),
};
