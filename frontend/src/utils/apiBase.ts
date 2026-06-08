/**
 * API基础地址管理
 * Tauri生产模式通过invoke从Rust端获取动态端口，浏览器开发模式使用环境变量或默认值
 */

import api from "./api";

let resolvedBase: string | null = null;

/** 异步解析API基础地址，优先Tauri命令，回退到环境变量 */
async function resolveApiBase(): Promise<string> {
  // 优先使用已缓存的结果
  if (resolvedBase) return resolvedBase;

  // 尝试从 Tauri command 获取
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    const base = await invoke<string>("get_api_base");
    resolvedBase = base;
    return base;
  } catch {
    // 非 Tauri 环境
  }

  // 回退到环境变量或默认值
  const fallback = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
  resolvedBase = fallback;
  return fallback;
}

/** 同步获取当前API基础地址（可能返回初始值，建议先调用initApiBase） */
export function getApiBase(): string {
  return resolvedBase || import.meta.env.VITE_API_URL || "http://localhost:8000/api";
}

// 保持向后兼容的 const 导出（模块加载时的初始值，不随 initApiBase 更新）
export const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

/** 异步初始化：应用启动时调用一次，更新axios的baseURL */
export async function initApiBase(): Promise<string> {
  const base = await resolveApiBase();
  resolvedBase = base;
  // 直接导入 api 模块更新 baseURL（静态导入，避免 Vite 警告）
  api.defaults.baseURL = base;
  return base;
}
