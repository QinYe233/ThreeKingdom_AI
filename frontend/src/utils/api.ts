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
  getBlocks: (country?: string) => api.get("/blocks", { params: { country } }),
  getBlock: (name: string) => api.get(`/blocks/${name}`),
  getCountry: (name: string) => api.get(`/countries/${name}`),
  executeAction: (data: any) => api.post("/game/action", data),
  sendMessage: (data: any) => api.post("/message", data),
  nextRound: () => api.post("/game/next-round"),
  getFog: (country: string) => api.get(`/fog/${country}`),
  getNarrative: () => api.get("/narrative"),
  getGenerals: (aliveOnly = true) => api.get("/generals", { params: { alive_only: aliveOnly } }),
  getRelations: () => api.get("/relations"),
  getMemories: (country: string) => api.get(`/memories/${country}`),
  getHistory: (limit = 50) => api.get("/history", { params: { limit } }),
};

export const mapApi = {
  getGeoJSON: () => api.get("/map/geojson", { baseURL: API_BASE }),
  getBlocksSummary: () => api.get("/map/blocks-summary", { baseURL: API_BASE }),
};
