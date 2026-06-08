/**
 * SSE（Server-Sent Events）工具
 * 手动解析SSE流，支持多行data字段累积和空行分隔的事件边界
 */
import { getApiBase } from "./apiBase";

export interface SSEOptions {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
}

/**
 * 发起SSE请求并逐事件回调
 * 使用ReadableStream手动解析，按SSE规范累积data行，空行触发事件派发
 */
export async function fetchSSE<T>(
  path: string,
  onEvent: (data: T) => void,
  options: SSEOptions = {}
): Promise<void> {
  const url = `${getApiBase()}${path}`;
  const res = await fetch(url, {
    method: options.method || "GET",
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
    body: options.body ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  });

  if (!res.ok) {
    throw new Error(`SSE request failed: ${res.status} ${res.statusText}`);
  }

  const reader = res.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = "";

  // SSE规范：累积data行，空行表示事件结束
  let dataBuffer = "";

  /** 处理累积的data字段，解析JSON并回调 */
  const processEvent = () => {
    if (dataBuffer) {
      const jsonStr = dataBuffer.trim();
      if (jsonStr) {
        try {
          const data = JSON.parse(jsonStr);
          onEvent(data);
        } catch (e) {
          console.error("SSE parse error:", e);
        }
      }
      dataBuffer = "";
    }
  };

  while (true) {
    if (options.signal?.aborted) break;

    const { done, value } = await reader.read();
    if (done) {
      // 流结束，处理缓冲区中剩余的数据
      if (buffer.trim()) {
        const lines = buffer.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            dataBuffer += line.slice(6);
          }
        }
      }
      processEvent();
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    // 保留最后一行（可能是不完整的行）到缓冲区
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        // 累积多行data字段（SSE规范）
        dataBuffer += line.slice(6);
      } else if (line.trim() === "") {
        // 空行表示事件结束，派发累积的数据
        processEvent();
      }
      // 忽略其他SSE字段（event:, id:, retry:, 注释行）
    }
  }
}
