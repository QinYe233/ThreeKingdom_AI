/**
 * 自动播放 Hook
 * 管理自动连续推进AI行动的定时器和状态
 */
import { useState, useCallback, useRef, useEffect } from "react";
import { useGameStore } from "../stores/gameStore";

/**
 * 自动播放Hook
 * @param executeStep - 单步执行函数（执行当前势力AI决策）
 * @returns autoPlay - 是否正在自动播放
 * @returns toggleAutoPlay - 切换自动播放状态
 */
export function useAutoPlay(executeStep: () => Promise<void>) {
  const [autoPlay, setAutoPlay] = useState(false);
  const autoPlayRef = useRef(false);
  const autoPlayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 用ref同步最新状态，避免闭包捕获旧值
  autoPlayRef.current = autoPlay;

  // 分开获取store状态，避免返回新对象导致无限循环
  const initialized = useGameStore(state => state.initialized);
  const pendingCountrySwitch = useGameStore(state => state.pendingCountrySwitch);

  /** 调度下一次自动播放，间隔1秒 */
  const scheduleAutoPlay = useCallback(() => {
    if (autoPlayTimerRef.current) {
      clearTimeout(autoPlayTimerRef.current);
      autoPlayTimerRef.current = null;
    }

    if (!autoPlayRef.current) return;

    autoPlayTimerRef.current = setTimeout(async () => {
      if (!autoPlayRef.current) return;

      await executeStep();

      if (autoPlayRef.current) {
        scheduleAutoPlay();
      }
    }, 1000);
  }, [executeStep]);

  useEffect(() => {
    if (autoPlay && initialized && !pendingCountrySwitch) {
      scheduleAutoPlay();
    } else {
      if (autoPlayTimerRef.current) {
        clearTimeout(autoPlayTimerRef.current);
        autoPlayTimerRef.current = null;
      }
    }

    return () => {
      if (autoPlayTimerRef.current) {
        clearTimeout(autoPlayTimerRef.current);
        autoPlayTimerRef.current = null;
      }
    };
  }, [autoPlay, initialized, pendingCountrySwitch, scheduleAutoPlay]);

  const toggleAutoPlay = useCallback(() => setAutoPlay(prev => !prev), []);

  return { autoPlay, toggleAutoPlay };
}
