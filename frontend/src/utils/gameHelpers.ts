/**
 * 游戏辅助函数
 * 提供行动摘要生成和势力切换逻辑
 */
import { COUNTRY_ORDER } from "../constants";

/** 根据行动类型和参数生成中文摘要文本 */
export function generateActionSummary(action: string, params: Record<string, any>, result: Record<string, any>): string {
  if (action === "attack") {
    const from = params.from || "?";
    const to = params.to || "?";
    const troops = params.troops || 0;
    if (result.battle_result?.block_captured) {
      return `⚔ 攻占${to}（从${from}出兵${troops}）`;
    }
    return `⚔ 进攻${to}受挫（从${from}出兵${troops}）`;
  }
  if (action === "recruit") {
    const block = params.block || "?";
    const recruited = result.troops_recruited || 0;
    return `🗡 于${block}征兵${recruited}`;
  }
  if (action === "tax") {
    const gold = result.gold_earned || 0;
    return `💰 征税得金${gold}`;
  }
  if (action === "develop") {
    const block = params.block || "?";
    const inc = result.manpower_increase || 0;
    return `🏗 发展${block}（人力+${inc}）`;
  }
  if (action === "move") {
    const from = params.from || "?";
    const to = params.to || "?";
    const troops = params.troops || 0;
    return `➡ 调兵${troops}从${from}至${to}`;
  }
  if (action === "harass") {
    const to = params.to || "?";
    return `🏹 骚扰${to}`;
  }
  if (action === "declare_emperor") {
    return `👑 称帝！`;
  }
  if (action === "move_capital") {
    return `🏛 迁都至${params.new_capital || "?"}`;
  }
  return "";
}

/** 获取下一个未灭亡的势力（按COUNTRY_ORDER循环） */
export function getNextActiveCountry(currentCountry: string, countries: Record<string, any> | undefined | null): string {
  const currentIndex = COUNTRY_ORDER.indexOf(currentCountry);
  for (let i = 1; i <= COUNTRY_ORDER.length; i++) {
    const candidate = COUNTRY_ORDER[(currentIndex + i) % COUNTRY_ORDER.length];
    if (countries && countries[candidate]?.is_defeated) {
      continue;
    }
    return candidate;
  }
  return currentCountry;
}
