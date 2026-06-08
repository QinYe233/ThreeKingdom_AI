/**
 * 业务常量 - 与视觉主题无关的游戏逻辑常量
 * 包括势力顺序、AI角色、专精/目标标签、动画配置、工具函数等
 */

// 势力行动顺序
export const COUNTRY_ORDER = ["魏", "蜀", "吴"];

// AI 角色配置
export const AI_ROLES = [
  { id: "wei", name: "魏国", countryKey: "魏", desc: "控制曹操势力，以统一天下为目标" },
  { id: "shu", name: "蜀国", countryKey: "蜀", desc: "控制刘备势力，以兴复汉室为目标" },
  { id: "wu", name: "吴国", countryKey: "吴", desc: "控制孙权势力，以保境安民为目标" },
  { id: "chronicler", name: "史官", countryKey: "", desc: "记录游戏历史，撰写叙事文本" },
];

// 专精标签
export const SPECIALIZATION_LABELS: Record<string, string> = {
  farming: "农垦",
  trade: "商贸",
  fortress: "堡垒",
};

// 目标标签
export const GOAL_LABELS: Record<string, string> = {
  expand: "扩张",
  defend: "防御",
  revenge: "复仇",
  stabilize: "稳定",
  declare_emperor: "称帝",
};

// 动画持续时间
export const ANIMATION_DURATION = 2500;

// 速度选项
export const SPEED_OPTIONS = [
  { value: 5000, label: "慢速" },
  { value: 3000, label: "正常" },
  { value: 1500, label: "快速" },
  { value: 800, label: "极速" },
];

// 势力名称映射
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

// 游戏工具函数
/** 根据外交数据判断两国关系状态，返回显示文本和颜色 */
export const getRelationStatus = (rel: { at_war: boolean; is_allied: boolean; trust: number; grudge: number }) => {
  if (rel.at_war) return { text: "⚔️ 交战", color: "#ef4444" };
  if (rel.is_allied) return { text: "🤝 同盟", color: "#34d399" };
  if (rel.trust > 0.5) return { text: "😊 友善", color: "#60a5fa" };
  if (rel.grudge > 0.3) return { text: "😤 仇怨", color: "#f97316" };
  return { text: "😐 中立", color: "#9ca3af" };
};

/** 根据行动点数返回对应颜色（绿/黄/红） */
export const getActionPointColor = (ap: number) => {
  if (ap > 3) return { bg: "rgba(26, 111, 19, 0.2)", text: "#1a6f4a" };
  if (ap > 0) return { bg: "rgba(217, 145, 53, 0.2)", text: "#d97706" };
  return { bg: "rgba(197, 48, 48, 0.2)", text: "#c53030" };
};

/** 根据秩序/士气值返回对应颜色（绿/黄/红） */
export const getOrderMoraleColor = (value: number) => {
  if (value >= 60) return "#1a6f4a";
  if (value >= 30) return "#d97706";
  return "#c53030";
};
