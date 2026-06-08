/**
 * 地图动画管理 Hook
 * 将AI行动结果转换为地图上的可视化动画（征兵、进攻、征税、发展）
 * 并收集外交事件
 */
import { useState, useCallback } from "react";
import type { DiplomaticEvent } from "../types/game";

/** 地图动画数据结构 */
export interface MapAnimation {
  type: string;
  block?: string;
  from?: string;
  to?: string;
  success?: boolean;
  country: string;
  value?: number;
  timestamp: number;
}

/**
 * 地图动画管理Hook
 * @returns mapAnimations - 当前活跃的动画列表
 * @returns diplomaticEvents - 外交事件列表
 * @returns generateAnimations - 根据AI行动结果生成动画
 */
export function useMapAnimations() {
  const [mapAnimations, setMapAnimations] = useState<MapAnimation[]>([]);
  const [diplomaticEvents, setDiplomaticEvents] = useState<DiplomaticEvent[]>([]);

  /** 根据AI行动结果生成地图动画，5秒后自动清除 */
  const generateAnimations = useCallback((result: any, country: string, currentRound: number) => {
    if (!result || !result.results) return;

    const newAnimations: MapAnimation[] = [];
    for (const r of result.results) {
      if (r.action === "recruit" && r.parameters?.block) {
        newAnimations.push({
          type: "recruit",
          block: r.parameters.block,
          value: r.result?.troops_recruited || 0,
          country,
          timestamp: Date.now(),
        });
      } else if (r.action === "attack" && r.parameters?.from && r.parameters?.to) {
        newAnimations.push({
          type: "attack",
          from: r.parameters.from,
          to: r.parameters.to,
          success: r.result?.battle_result?.block_captured || false,
          country,
          timestamp: Date.now(),
        });
      } else if (r.action === "tax") {
        newAnimations.push({
          type: "tax",
          country,
          value: r.result?.gold_earned || 0,
          timestamp: Date.now(),
        });
      } else if (r.action === "develop" && r.parameters?.block) {
        newAnimations.push({
          type: "develop",
          block: r.parameters.block,
          value: r.result?.manpower_increase || 0,
          country,
          timestamp: Date.now(),
        });
      } else if (r.action === "send_message") {
        const event: DiplomaticEvent = {
          round: currentRound,
          from_country: country,
          to_country: r.parameters?.to_country || "",
          event_type: "外交信函",
          content: r.parameters?.content || "",
          visibility: r.parameters?.visibility || "private",
        };
        setDiplomaticEvents(prev => [...prev, event].slice(-200));
      }
    }
    if (newAnimations.length > 0) {
      setMapAnimations(prev => [...prev, ...newAnimations]);
      setTimeout(() => {
        setMapAnimations(prev => prev.filter(a => Date.now() - a.timestamp < 5000));
      }, 5000);
    }
  }, []);

  return { mapAnimations, diplomaticEvents, generateAnimations };
}
