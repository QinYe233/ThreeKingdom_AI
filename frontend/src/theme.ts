/**
 * 视觉主题配置 - 古卷纸风格
 * 包含颜色、字体、纹理效果、组件样式、地图颜色、势力颜色等
 */

// 主色调 - 古卷纸暖色系
export const THEME_COLORS = {
  bg: "#e8dccb",                    // Warm aged paper - main background
  header: "#d4c8b5",                 // Darker parchment brown - headers
  sidebar: "#d9d0c7",                 // Slightly lighter than header - sidebars
  text: "#3d2b1f",                    // Dark brown-ink - primary text
  textMuted: "#6b5b4f",              // Muted brown - secondary text
  border: "#b8a888",                    // Subtle parchment border - borders
  accent: "#8b4513",                   // Traditional Chinese red - highlights
  card: "#f5f0dc",                    // Lighter paper for cards - card backgrounds
  input: "#f8f5e8",                    // Slightly lighter than card - input backgrounds
  success: "#1a6f4a",                // Traditional green - success states
  error: "#c53030",                   // Vermilion red - error states
  warning: "#d97706",                // Golden yellow - warning states
};

export type ThemeColors = typeof THEME_COLORS;

// 字体配置 - 书法/宋体/楷体
export const FONTS = {
  title: "Ma Shan Zheng, SimSun, serif",    // 马善正楷 - Traditional calligraphy for titles
  subtitle: "STSong, serif",                  // 宋体 - Song dynasty style for subtitles
  body: "KaiTi, serif",                     // 楷体 - Kai style for body text
};

export const FONT_SIZES = {
  title: "1.5rem",      // Large titles
  subtitle: "1.125rem",  // Subtitles
  body: "0.875rem",    // Body text
  caption: "0.75rem",    // Captions
};

// 古卷纸纹理效果 - CSS渐变实现
export const PARCHMENT_EFFECTS = {
  // Main background with aged spots
  background: `
    linear-gradient(135deg,
      transparent 95%,
      rgba(139, 115, 85, 0.03) 100%
    ),
    radial-gradient(ellipse at center,
      transparent 0%,
      rgba(139, 115, 85, 0.05) 100%
    )
  `,

  // Scroll-style panel edges (traditional scroll ends)
  scrollEdges: `
    inset 0 0 4px 0 rgba(139, 115, 85, 0.1),
    inset 0 4px 0 4px rgba(139, 115, 85, 0.1)
  `,

  // Scroll gradient (fade effect like scroll ends)
  scrollGradient: `
    linear-gradient(to bottom,
      transparent 0%,
      rgba(139, 115, 85, 0.15) 15%,
      transparent 15%,
      transparent 85%,
      rgba(139, 115, 85, 0.15) 100%
    )
  `,

  // Paper shadow effect (aged paper depth)
  paperShadow: `
    0 4px 12px rgba(61, 43, 31, 0.15),
    inset 0 1px 3px rgba(255, 255, 255, 0.1)
  `,

  // Traditional red seal effect for important items
  redSeal: `
    0 2px 4px rgba(197, 48, 48, 0.3),
    inset 0 -1px 2px rgba(248, 108, 107, 0.3)
  `,
};

// 组件级样式预设
export const COMPONENT_STYLES = {
  // Scroll-style panel backgrounds
  scrollPanel: {
    background: `linear-gradient(to bottom,
      ${THEME_COLORS.bg} 0%,
      ${THEME_COLORS.card} 2%,
      ${THEME_COLORS.bg} 5%
    )`,
    borderLeft: "3px solid rgba(139, 115, 85, 0.6)",
    borderRight: "3px solid rgba(139, 115, 85, 0.6)",
    boxShadow: "0 4px 12px rgba(61, 43, 31, 0.15)",
  },

  // Card effect
  card: {
    background: THEME_COLORS.card,
    border: `1px solid rgba(139, 115, 85, 0.3)`,
    boxShadow: PARCHMENT_EFFECTS.paperShadow,
    borderRadius: "4px",
  },

  // Button styles
  button: {
    background: THEME_COLORS.accent,
    color: "#ffffff",
    border: `1px solid rgba(139, 115, 85, 0.2)`,
    boxShadow: "inset 0 1px 2px rgba(0, 0, 0, 0.1)",
    transition: "background-color 0.2s ease, box-shadow 0.2s ease",
  },
  buttonHover: {
    background: "#a55830", // Darker red
    boxShadow: "inset 0 1px 2px rgba(0, 0, 0, 0.2)",
  },

  // Input styles
  input: {
    background: THEME_COLORS.input,
    border: `1px solid ${THEME_COLORS.border}`,
    color: THEME_COLORS.text,
    boxShadow: "inset 0 0 2px rgba(139, 115, 85, 0.05)",
  },

  // Divider styles
  divider: {
    background: `linear-gradient(to right,
      transparent 0%,
      rgba(139, 115, 85, 0.2) 50%,
      transparent 100%
    )`,
    height: "1px",
  },
};

// 地图底色配置
export const MAP_COLORS = {
  base: "#f0e6d3",                    // Very light parchment - map base
  water: "#d4c8b5",                  // Muted brown - water areas
  gridLines: "rgba(139, 115, 85, 0.08)",  // Very subtle - grid overlay
  agedSpots: "rgba(139, 115, 85, 0.05)",  // Random aged spots - texture
  selectionBorder: "#8b4513",        // Traditional red - selection highlight
  selectionFill: "rgba(139, 115, 85, 0.3)",  // Aged paper - selection fill
  hoverBorder: "#b8a888",            // Subtle parchment - hover effect
  hoverFill: "rgba(139, 115, 85, 0.2)",  // Light parchment - hover fill
};

// 势力主色（用于标签、徽章等简单场景）
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

// 势力色组（用于地图绘制，包含填充/描边/首都星标三色）
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

// 从 constants.ts 重新导出，保持向后兼容
export { COUNTRY_ORDER, AI_ROLES, SPECIALIZATION_LABELS, GOAL_LABELS, ANIMATION_DURATION, SPEED_OPTIONS, OWNER_NAMES, getRelationStatus, getActionPointColor, getOrderMoraleColor } from "./constants";
