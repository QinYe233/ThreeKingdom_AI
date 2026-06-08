// 设置持久化与窗口模式管理

// localStorage 键名
const SETTINGS_KEY = "sanguo_settings";

// 窗口模式类型
export type WindowMode = "windowed" | "borderless" | "fullscreen";

// 播放模式类型
export type PlayMode = "list_loop" | "weighted_random" | "single_loop";

// 持久化设置接口
export interface PersistedSettings {
  windowMode: WindowMode;
  bgmVolume: number;       // 0-1
  sfxVolume: number;       // 0-1
  playMode: PlayMode;
  fadeDuration: number;    // 0-5 秒
  bgmMuted: boolean;
  sfxMuted: boolean;
}

// 默认设置
const DEFAULT_SETTINGS: PersistedSettings = {
  windowMode: "windowed",
  bgmVolume: 0.5,
  sfxVolume: 0.7,
  playMode: "list_loop",
  fadeDuration: 1.5,
  bgmMuted: false,
  sfxMuted: false,
};

// 读取保存的设置
export function loadSettings(): PersistedSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      const merged = { ...DEFAULT_SETTINGS, ...parsed };
      // 验证关键字段类型
      if (typeof merged.bgmVolume !== "number" || isNaN(merged.bgmVolume)) merged.bgmVolume = DEFAULT_SETTINGS.bgmVolume;
      if (typeof merged.sfxVolume !== "number" || isNaN(merged.sfxVolume)) merged.sfxVolume = DEFAULT_SETTINGS.sfxVolume;
      if (typeof merged.fadeDuration !== "number" || isNaN(merged.fadeDuration)) merged.fadeDuration = DEFAULT_SETTINGS.fadeDuration;
      if (typeof merged.bgmMuted !== "boolean") merged.bgmMuted = DEFAULT_SETTINGS.bgmMuted;
      if (typeof merged.sfxMuted !== "boolean") merged.sfxMuted = DEFAULT_SETTINGS.sfxMuted;
      if (!["windowed", "borderless", "fullscreen"].includes(merged.windowMode)) merged.windowMode = DEFAULT_SETTINGS.windowMode;
      if (!["list_loop", "weighted_random", "single_loop"].includes(merged.playMode)) merged.playMode = DEFAULT_SETTINGS.playMode;
      return merged;
    }
  } catch (e) {
    console.error("读取设置失败:", e);
  }
  return DEFAULT_SETTINGS;
}

// 内存缓存，避免频繁 JSON 解析
let settingsCache: PersistedSettings | null = null;

// 保存设置到 localStorage（带防抖）
let saveTimer: ReturnType<typeof setTimeout> | null = null;
export function saveSettings(settings: Partial<PersistedSettings>) {
  try {
    // 更新缓存
    settingsCache = { ...(settingsCache || loadSettings()), ...settings };
    const data = settingsCache;

    // 防抖：100ms 内只写入一次
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(data));
    }, 100);
  } catch (e) {
    console.error("保存设置失败:", e);
  }
}

// 应用窗口模式（使用 Tauri API）
export async function applyWindowMode(mode: WindowMode) {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    const appWindow = getCurrentWindow();

    switch (mode) {
      case "windowed":
        await appWindow.setFullscreen(false);
        await appWindow.setDecorations(true);
        break;
      case "borderless":
        await appWindow.setFullscreen(false);
        await appWindow.setDecorations(false);
        break;
      case "fullscreen":
        await appWindow.setFullscreen(true);
        break;
    }
  } catch (e) {
    // Tauri API 不可用时（浏览器开发模式）静默忽略
    console.log("Tauri API 不可用，跳过窗口模式切换:", e);
  }
}
