export type MapTheme = "dark" | "parchment";

export const COUNTRY_COLORS: Record<string, string> = {
  "魏": "#5470a6",
  "蜀": "#c44e52",
  "吴": "#56a67b",
  neutral: "#b0b0b0",
  "公孙度": "#8b7355",
  "士燮": "#cd853f",
  "南中": "#8b4513",
  "山越": "#6b8e23",
  "凉州": "#d2691e",
};

export const COUNTRY_COLOR_SETS: Record<string, { fill: string; stroke: string; star: string }> = {
  "魏": { fill: "#4a6fa5", stroke: "#3d5a80", star: "#6b8fc7" },
  "蜀": { fill: "#a54657", stroke: "#8b3a4a", star: "#d46a7a" },
  "吴": { fill: "#4a8f5c", stroke: "#3a7a4a", star: "#6ab87a" },
  neutral: { fill: "#7a7a7a", stroke: "#5a5a5a", star: "#9a9a9a" },
  "公孙度": { fill: "#8b7355", stroke: "#6b5340", star: "#ab9375" },
  "士燮": { fill: "#b8860b", stroke: "#8b6914", star: "#d8a62b" },
  "南中": { fill: "#8b4513", stroke: "#6b3510", star: "#ab6533" },
  "山越": { fill: "#6b8e23", stroke: "#556b2f", star: "#8bae43" },
  "凉州": { fill: "#cd853f", stroke: "#a0522d", star: "#eda55f" },
};

export const THEME_NAMES: Record<MapTheme, string> = {
  dark: "夜间模式",
  parchment: "历史质感",
};

export const THEME_COLORS: Record<MapTheme, ThemeColors> = {
  dark: {
    bg: "#0d1117",
    header: "#161b22",
    sidebar: "#161b22",
    text: "#e6edf3",
    textMuted: "#8b949e",
    border: "#30363d",
    accent: "#f59e0b",
    card: "#21262d",
    input: "#0d1117",
    success: "#34d399",
    error: "#f87171",
    warning: "#fbbf24",
  },
  parchment: {
    bg: "#c9b896",
    header: "#b8a888",
    sidebar: "#b8a888",
    text: "#3d3428",
    textMuted: "#5a4d3a",
    border: "#8b7355",
    accent: "#8b4513",
    card: "#d4c4a8",
    input: "#e8dcc8",
    success: "#16a34a",
    error: "#dc2626",
    warning: "#ca8a04",
  },
};

export const THEME_BACKGROUNDS: Record<MapTheme, string> = {
  dark: "#0d1117",
  parchment: "#c9b896",
};

export interface ThemeColors {
  bg: string;
  header: string;
  sidebar: string;
  text: string;
  textMuted: string;
  border: string;
  accent: string;
  card: string;
  input: string;
  success: string;
  error: string;
  warning: string;
}

export const OWNER_NAMES: Record<string, string> = {
  neutral: "中立",
  "魏": "魏",
  "蜀": "蜀",
  "吴": "吴",
  "公孙度": "公孙度",
  "士燮": "士燮",
  "南中": "南中",
  "山越": "山越",
  "凉州": "凉州",
};

export const COUNTRY_ORDER = ["魏", "蜀", "吴"];

export const ANIMATION_DURATION = 2500;

export const SPEED_OPTIONS = [
  { value: 5000, label: "慢速" },
  { value: 3000, label: "正常" },
  { value: 1500, label: "快速" },
  { value: 800, label: "极速" },
];

export const getRelationStatus = (rel: { at_war: boolean; is_allied: boolean; trust: number; grudge: number }) => {
  if (rel.at_war) return { text: "⚔️ 交战", color: "#ef4444" };
  if (rel.is_allied) return { text: "🤝 同盟", color: "#34d399" };
  if (rel.trust > 0.5) return { text: "😊 友善", color: "#60a5fa" };
  if (rel.grudge > 0.3) return { text: "😤 仇怨", color: "#f97316" };
  return { text: "😐 中立", color: "#9ca3af" };
};

export const getActionPointColor = (ap: number) => {
  if (ap > 3) return { bg: "rgba(52,211,153,0.2)", text: "#34d399" };
  if (ap > 0) return { bg: "rgba(251,191,36,0.2)", text: "#fbbf24" };
  return { bg: "rgba(239,68,68,0.2)", text: "#ef4444" };
};

export const getOrderMoraleColor = (value: number) => {
  if (value >= 60) return "#16a34a";
  if (value >= 30) return "#ca8a04";
  return "#dc2626";
};

export interface ThinkingRecord {
  round: number;
  country: string;
  thinking: string;
  content: string;
  actions: string[];
}
