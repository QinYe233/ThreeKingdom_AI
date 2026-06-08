/**
 * 设置面板 - AI模型配置和音频设置
 * 支持多角色独立配置、连接测试、批量复制配置、GSAP动画切换
 */
import { useState, useEffect, useRef, useCallback } from "react";
import { THEME_COLORS, COUNTRY_COLORS, AI_ROLES } from "../../theme";
import { aiApi } from "../../utils/api";
import { useAudioStore } from "../../stores/audioStore";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(useGSAP);

interface ConfigStatus {
  model: string;
  base_url: string;
  has_api_key: boolean;
  temperature: number;
  max_tokens: number;
  streaming?: boolean;
  deep_thinking?: boolean;
  is_valid: boolean;
}

interface SettingsProps {
  onClose: () => void;
  onComplete: () => void;
  theme?: "dark" | "parchment";
  inGame?: boolean;
  onAiSettingsChange?: (streaming: boolean, deepThinking: boolean) => void;
}

type TabType = "ai" | "audio";

/** Toast通知组件 - GSAP驱动的淡入淡出提示 */
function Toast({ message, type, onDone }: { message: string; type: "error" | "success" | "warning"; onDone: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const colors = THEME_COLORS;

  const bgColor = type === "error" ? `${colors.error}20` : type === "warning" ? "#f59e0b20" : `${colors.success}20`;
  const borderColor = type === "error" ? `${colors.error}60` : type === "warning" ? "#f59e0b60" : `${colors.success}60`;
  const textColor = type === "error" ? colors.error : type === "warning" ? "#f59e0b" : colors.success;
  const icon = type === "error" ? "✕" : type === "warning" ? "⚠" : "✓";

  useGSAP(() => {
    const tl = gsap.timeline();
    tl.fromTo(ref.current, { autoAlpha: 0, y: -20, scale: 0.95 }, { autoAlpha: 1, y: 0, scale: 1, duration: 0.3, ease: "back.out(1.2)" });
    tl.to(ref.current, { autoAlpha: 0, y: -10, duration: 0.3, ease: "power2.in", delay: 2.7 });
    tl.call(onDone);
  }, { scope: ref });

  return (
    <div ref={ref} className="fixed top-6 left-1/2 -translate-x-1/2 z-[100] px-5 py-3 rounded-lg shadow-lg flex items-center gap-2 text-sm font-medium"
      style={{ backgroundColor: bgColor, border: `1px solid ${borderColor}`, color: textColor }}>
      <span className="text-base">{icon}</span>
      <span>{message}</span>
    </div>
  );
}

/** 根据角色ID获取对应的势力颜色 */
function getRoleColor(roleId: string): string {
  const role = AI_ROLES.find(r => r.id === roleId);
  if (role && role.countryKey) {
    return COUNTRY_COLORS[role.countryKey] || "#B8860B";
  }
  return "#B8860B";
}

export default function Settings({ onClose, onComplete, inGame, onAiSettingsChange }: SettingsProps) {
  const colors = THEME_COLORS;
  const [activeTab, setActiveTab] = useState<TabType>(inGame ? "audio" : "ai");
  const prevTabRef = useRef<TabType>("ai");
  const containerRef = useRef<HTMLDivElement>(null);
  const tabContentRef = useRef<HTMLDivElement>(null);
  const tabIndicatorRef = useRef<HTMLDivElement>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    return () => { mountedRef.current = false; };
  }, []);

  // Toast 状态
  const [toast, setToast] = useState<{ message: string; type: "error" | "success" | "warning" } | null>(null);

  const showToast = useCallback((message: string, type: "error" | "success" | "warning") => {
    setToast(null);
    // 用 requestAnimationFrame 确保先卸载旧的 toast 再挂新的
    requestAnimationFrame(() => setToast({ message, type }));
  }, []);

  // AI 配置状态
  const [configs, setConfigs] = useState<Record<string, ConfigStatus>>({});
  const [currentRole, setCurrentRole] = useState<string>("wei");
  const [formData, setFormData] = useState({
    model: "",
    api_key: "",
    base_url: "",
    temperature: 0.7,
    max_tokens: 4096,
    streaming: true,
    deep_thinking: true,
  });
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "error" | "success" | "info"; text: string } | null>(null);
  const [testResults, setTestResults] = useState<Record<string, "success" | "fail">>({});

  // 音频设置状态
  const {
    bgmVolume, sfxVolume, playMode, bgmMuted, sfxMuted,
    setBgmVolume, setSfxVolume, setPlayMode, toggleBgmMuted, toggleSfxMuted,
  } = useAudioStore();

  useEffect(() => { fetchStatus(); }, []);

  // 保存后标记，防止角色切换时重置表单数据
  const justSavedRef = useRef(false);

  useEffect(() => {
    if (justSavedRef.current) {
      justSavedRef.current = false;
      return; // Skip reset - we just saved, keep current form data
    }
    const cfg = configs[currentRole];
    if (cfg) {
      setFormData({
        model: cfg.model || "",
        api_key: "",
        base_url: cfg.base_url || "",
        temperature: cfg.temperature ?? 0.7,
        max_tokens: cfg.max_tokens ?? 4096,
        streaming: cfg.streaming ?? true,
        deep_thinking: cfg.deep_thinking ?? true,
      });
    }
    // Don't reset if no config available - keep current form data
  }, [currentRole, configs]);

  // Tab 指示器滑动动画
  const tabKeys: TabType[] = ["ai", "audio"];
  useGSAP(() => {
    const idx = tabKeys.indexOf(activeTab);
    if (tabIndicatorRef.current) {
      gsap.to(tabIndicatorRef.current, {
        x: idx * tabIndicatorRef.current.parentElement!.clientWidth / 2,
        duration: 0.35,
        ease: "power2.out",
      });
    }
  }, { dependencies: [activeTab], scope: containerRef });

  // Tab 内容切换动画
  const switchTab = useCallback((tab: TabType) => {
    if (tab === activeTab) return;
    const direction: number = tabKeys.indexOf(tab) > tabKeys.indexOf(activeTab) ? 1 : -1;
    prevTabRef.current = activeTab;

    if (tabContentRef.current) {
      gsap.to(tabContentRef.current, {
        autoAlpha: 0,
        x: -20 * direction,
        duration: 0.15,
        ease: "power2.in",
        onComplete: () => {
          if (!mountedRef.current) return;
          setActiveTab(tab);
          gsap.fromTo(tabContentRef.current,
            { autoAlpha: 0, x: 20 * direction },
            { autoAlpha: 1, x: 0, duration: 0.25, ease: "power2.out" }
          );
        },
      });
    } else {
      setActiveTab(tab);
    }
  }, [activeTab]);

  // 面板进入动画
  useGSAP(() => {
    gsap.fromTo(containerRef.current,
      { autoAlpha: 0, scale: 0.92, y: 20 },
      { autoAlpha: 1, scale: 1, y: 0, duration: 0.4, ease: "back.out(1.4)" }
    );
  }, { scope: containerRef });

  const fetchStatus = async () => {
    try {
      const data: any = await aiApi.getStatus();
      setConfigs(data.configs || {});
    } catch (e) { console.error(e); }
  };

  const updateForm = (field: string, value: string | number | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setMessage(null);
    // Clear test result for current role since config changed
    setTestResults(prev => {
      const next = { ...prev };
      delete next[currentRole];
      return next;
    });
  };

  const testConnection = async (role: string, useSaved: boolean) => {
    setTesting(role);
    setMessage(null);
    try {
      let data: any;
      if (useSaved) {
        data = await aiApi.testConnectionByRole(role);
      } else {
        if (!formData.api_key && !configs[role]?.has_api_key) {
          showToast("请先填写 API Key", "warning");
          setTesting(null);
          return;
        }
        if (!formData.api_key && configs[role]?.has_api_key) {
          // Fall back to testing saved config
          setTesting(null);
          testConnection(role, true);
          return;
        }
        if (!formData.base_url || !formData.model || !formData.api_key) {
          showToast("请先填写 Base URL、模型名称和 API Key", "warning");
          setTesting(null);
          return;
        }
        // Auto-save before testing
        try {
          const saveBody: Record<string, unknown> = {
            role, model: formData.model, base_url: formData.base_url,
            temperature: formData.temperature, max_tokens: formData.max_tokens,
            streaming: formData.streaming, deep_thinking: formData.deep_thinking,
          };
          if (formData.api_key) { saveBody.api_key = formData.api_key; }
          else if (configs[role]?.has_api_key) { saveBody.keep_existing_key = true; }
          await aiApi.saveConfig(saveBody);
          await fetchStatus();
          justSavedRef.current = true;
          onAiSettingsChange?.(formData.streaming, formData.deep_thinking);
        } catch (e) {
          console.error(e);
        }
        data = await aiApi.testConnection({
          model: formData.model, api_key: formData.api_key, base_url: formData.base_url,
        });
      }
      setTestResults(prev => ({ ...prev, [role]: "success" }));
      setMessage({ type: "success", text: `${AI_ROLES.find(r => r.id === role)?.name || role} 连接测试成功！模型: ${data.model || ""}` });
    } catch (e: any) {
      setTestResults(prev => ({ ...prev, [role]: "fail" }));
      const errText = e?.response?.data?.detail || e?.message || "连接测试失败";
      setMessage({ type: "error", text: errText });
      showToast(errText, "error");
    }
    setTesting(null);
  };

  const copyConfigToAll = async () => {
    // 检查当前角色是否测试通过
    if (testResults[currentRole] !== "success") {
      showToast("请先测试当前角色连接，通过后才能复制", "warning");
      return;
    }
    if (!formData.base_url || !formData.model) {
      showToast("请先填写当前角色的 Base URL 和模型名称", "warning"); return;
    }
    const hasExistingKey = configs[currentRole]?.has_api_key;
    if (!formData.api_key && !hasExistingKey) {
      showToast("请先填写当前角色的 API Key", "warning"); return;
    }
    setLoading(true);
    setMessage(null);

    try {
      // First save the current role's config
      try {
        const currentBody: Record<string, unknown> = {
          role: currentRole, model: formData.model, base_url: formData.base_url,
          temperature: formData.temperature, max_tokens: formData.max_tokens,
          streaming: formData.streaming, deep_thinking: formData.deep_thinking,
        };
        if (formData.api_key) { currentBody.api_key = formData.api_key; }
        else if (hasExistingKey) { currentBody.keep_existing_key = true; }
        await aiApi.saveConfig(currentBody);
      } catch (e) {
        console.error(e);
      }

      // Then copy to other roles
      const otherRoles = AI_ROLES.filter(r => r.id !== currentRole);
      let savedCount = 0;
      for (const role of otherRoles) {
        try {
          const body: Record<string, unknown> = {
            role: role.id, model: formData.model, base_url: formData.base_url,
            temperature: formData.temperature, max_tokens: formData.max_tokens,
            streaming: formData.streaming, deep_thinking: formData.deep_thinking,
          };
          if (formData.api_key) { body.api_key = formData.api_key; }
          else if (hasExistingKey) { body.api_key = "__keep_existing__"; }
          await aiApi.saveConfig(body);
          savedCount++;
        } catch (e) { console.error(e); }
      }
      await fetchStatus();
      justSavedRef.current = true;
      setMessage({ type: "success", text: `已将当前配置复制到 ${savedCount} 个角色` });
    } finally {
      setLoading(false);
    }
  };

  const testAllConnections = async () => {
    setMessage(null);
    const results: Record<string, "success" | "fail"> = {};
    setTestResults({});
    for (const role of AI_ROLES) {
      if (!configs[role.id]?.is_valid) continue;
      setTesting(role.id);
      try {
        await aiApi.testConnectionByRole(role.id);
        results[role.id] = "success";
      } catch { results[role.id] = "fail"; }
      setTestResults({ ...results });
    }
    setTesting(null);
    const failCount = Object.values(results).filter(v => v === "fail").length;
    const successCount = Object.values(results).filter(v => v === "success").length;
    if (failCount === 0 && successCount > 0) {
      setMessage({ type: "success", text: `全部 ${successCount} 个已配置角色连接测试通过！` });
    } else if (failCount > 0) {
      setMessage({ type: "error", text: `${successCount} 个成功，${failCount} 个失败` });
    } else {
      showToast("没有已配置的角色可供测试", "warning");
    }
  };

  const handleStartGame = async () => {
    try {
      const checkData: any = await aiApi.checkConfig();
      if (checkData.all_configured) {
        onComplete();
        onClose();
      } else {
        const unconfigured = AI_ROLES.filter(r => !configs[r.id]?.is_valid).map(r => r.name).join("、");
        showToast(`以下角色未完成配置: ${unconfigured}`, "warning");
      }
    } catch (e) {
      showToast("无法检查配置状态，请确认后端服务正在运行", "error");
    }
  };

  const currentRoleInfo = AI_ROLES.find(r => r.id === currentRole);
  if (!currentRoleInfo) return null;
  const currentConfig = configs[currentRole];
  const hasExistingKey = currentConfig?.has_api_key;
  const configuredCount = AI_ROLES.filter(r => configs[r.id]?.is_valid).length;
  const roleColor = getRoleColor(currentRole);
  const currentTestPassed = testResults[currentRole] === "success";

  const tabs = [
    { key: "ai" as TabType, label: "AI 配置", icon: "🤖" },
    { key: "audio" as TabType, label: "声音", icon: "🎵" },
  ];

  return (
    <>
      {/* Toast 通知 */}
      {toast && <Toast message={toast.message} type={toast.type} onDone={() => setToast(null)} />}

      <div className="fixed inset-0 flex items-center justify-center z-50" style={{ backgroundColor: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }}>
        <div
          ref={containerRef}
          className="rounded-xl w-[720px] flex flex-col shadow-2xl"
          style={{ backgroundColor: colors.card, border: `1px solid ${colors.border}`, height: 580 }}
        >
          {/* 标题栏 */}
          <div className="flex justify-between items-center px-6 py-4 shrink-0" style={{ borderBottom: `1px solid ${colors.border}` }}>
            <h2 className="text-xl font-bold" style={{ color: colors.accent }}>设置</h2>
            <button
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-full cursor-pointer transition-colors duration-200"
              style={{ backgroundColor: "transparent", color: colors.textMuted }}
              onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = colors.border; }}
              onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "transparent"; }}
            >
              ✕
            </button>
          </div>

          {/* Tab 导航 */}
          <div className="relative px-6 pt-3 shrink-0" style={{ borderBottom: `1px solid ${colors.border}` }}>
            <div className="flex">
              {tabs.map(tab => {
                const isAiDisabled = inGame && tab.key === "ai";
                return (
                  <button
                    key={tab.key}
                    onClick={() => {
                      if (isAiDisabled) return;
                      switchTab(tab.key);
                    }}
                    className="flex-1 px-4 py-2.5 cursor-pointer text-sm flex items-center justify-center gap-1.5 transition-colors duration-200"
                    style={{
                      color: isAiDisabled ? colors.textMuted : (activeTab === tab.key ? colors.accent : colors.textMuted),
                      fontWeight: activeTab === tab.key ? 700 : 400,
                      opacity: isAiDisabled ? 0.5 : 1,
                      cursor: isAiDisabled ? "not-allowed" : "pointer",
                    }}
                  >
                    <span>{tab.icon}</span>
                    <span>{tab.label}</span>
                    {tab.key === "ai" && !isAiDisabled && configuredCount > 0 && (
                      <span className="text-xs px-1.5 py-0.5 rounded-full" style={{ backgroundColor: configuredCount === AI_ROLES.length ? `${colors.success}30` : `${colors.accent}30`, color: configuredCount === AI_ROLES.length ? colors.success : colors.accent }}>
                        {configuredCount}/{AI_ROLES.length}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
            <div className="absolute bottom-0 left-6 right-6" style={{ height: 2 }}>
              <div
                ref={tabIndicatorRef}
                className="absolute bottom-0 h-full rounded-full"
                style={{ width: "50%", backgroundColor: colors.accent }}
              />
            </div>
          </div>

          {/* 内容区 — 固定高度 */}
          <div ref={tabContentRef} className="flex-1 overflow-y-auto p-6">
            {/* AI 配置标签页 */}
            {activeTab === "ai" && (
              inGame ? (
                <div className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <div className="text-4xl mb-3">🔒</div>
                    <div className="text-lg font-bold" style={{ color: colors.textMuted }}>局内不可更改 AI 配置</div>
                  </div>
                </div>
              ) : (
              <>
                <div className="text-sm mb-3" style={{ color: colors.textMuted }}>
                  为每个角色分别配置 AI 模型，或使用「复制到其他角色」批量设置
                </div>

                {message && (
                  <div
                    className="mb-4 p-3 rounded text-sm"
                    style={{
                      backgroundColor: message.type === "error" ? `${colors.error}15` : message.type === "info" ? `${colors.accent}15` : `${colors.success}15`,
                      border: `1px solid ${message.type === "error" ? `${colors.error}40` : message.type === "info" ? `${colors.accent}40` : `${colors.success}40`}`,
                      color: message.type === "error" ? colors.error : message.type === "info" ? colors.accent : colors.success,
                    }}
                  >
                    {message.text}
                  </div>
                )}

                <div className="mb-4">
                  <div className="grid grid-cols-4 gap-2">
                    {AI_ROLES.map(role => {
                      const cfg = configs[role.id];
                      const testResult = testResults[role.id];
                      const isActive = currentRole === role.id;
                      const isTestingThis = testing === role.id;
                      const rColor = getRoleColor(role.id);

                      let borderColor = `${rColor}40`;
                      if (testResult === "success") borderColor = "#22c55e";
                      else if (testResult === "fail") borderColor = "#ef4444";
                      else if (cfg?.is_valid) borderColor = rColor;
                      if (isActive) borderColor = rColor;

                      return (
                        <button
                          key={role.id}
                          onClick={() => { setCurrentRole(role.id); setMessage(null); }}
                          className="p-3 rounded-lg cursor-pointer transition-colors duration-200 text-center"
                          style={{
                            backgroundColor: isActive ? `${rColor}20` : colors.input,
                            border: `2px solid ${borderColor}`,
                            boxShadow: isActive ? `0 0 12px ${rColor}30` : "none",
                          }}
                        >
                          <div className="text-base font-bold" style={{ color: rColor }}>{role.name}</div>
                          <div className="text-xs mt-1 truncate" style={{ color: colors.textMuted }}>
                            {isTestingThis ? "⏳ 测试中..." : cfg?.is_valid ? cfg.model : "未配置"}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="mb-3 p-3 rounded-lg text-sm" style={{ backgroundColor: `${roleColor}10`, border: `1px solid ${roleColor}30`, color: colors.textMuted }}>
                  <span style={{ color: roleColor, fontWeight: "bold" }}>{currentRoleInfo.name}</span>：{currentRoleInfo.desc}
                </div>

                <div className="space-y-3">
                  <div>
                    <label className="block text-sm mb-1" style={{ color: colors.textMuted }}>
                      Base URL <span style={{ color: colors.error }}>*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.base_url}
                      onChange={(e) => updateForm("base_url", e.target.value)}
                      placeholder="https://api.openai.com/v1"
                      disabled={loading || !!testing}
                      className="w-full px-3 py-2 rounded-lg border outline-none transition-colors duration-200"
                      style={{ backgroundColor: colors.input, color: colors.text, borderColor: colors.border }}
                      onFocus={(e) => { e.currentTarget.style.borderColor = roleColor; }}
                      onBlur={(e) => { e.currentTarget.style.borderColor = colors.border; }}
                    />
                  </div>

                  <div>
                    <label className="block text-sm mb-1" style={{ color: colors.textMuted }}>
                      模型名称 <span style={{ color: colors.error }}>*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.model}
                      onChange={(e) => updateForm("model", e.target.value)}
                      placeholder="gpt-4o / deepseek-chat / qwen-plus"
                      disabled={loading || !!testing}
                      className="w-full px-3 py-2 rounded-lg border outline-none transition-colors duration-200"
                      style={{ backgroundColor: colors.input, color: colors.text, borderColor: colors.border }}
                      onFocus={(e) => { e.currentTarget.style.borderColor = roleColor; }}
                      onBlur={(e) => { e.currentTarget.style.borderColor = colors.border; }}
                    />
                  </div>

                  <div>
                    <label className="block text-sm mb-1" style={{ color: colors.textMuted }}>
                      API Key <span style={{ color: colors.error }}>*</span>
                      {hasExistingKey && !formData.api_key && (
                        <span style={{ color: colors.success }}> (已配置，留空保持不变)</span>
                      )}
                    </label>
                    <input
                      type="password"
                      value={formData.api_key}
                      onChange={(e) => updateForm("api_key", e.target.value)}
                      placeholder={hasExistingKey ? "已配置，留空保持不变" : "sk-..."}
                      disabled={loading || !!testing}
                      className="w-full px-3 py-2 rounded-lg border outline-none transition-colors duration-200"
                      style={{ backgroundColor: colors.input, color: colors.text, borderColor: colors.border }}
                      onFocus={(e) => { e.currentTarget.style.borderColor = roleColor; }}
                      onBlur={(e) => { e.currentTarget.style.borderColor = colors.border; }}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm mb-1" style={{ color: colors.textMuted }}>
                        Temperature: {formData.temperature}
                      </label>
                      <input
                        type="range" min="0" max="1" step="0.1"
                        value={formData.temperature}
                        onChange={(e) => updateForm("temperature", parseFloat(e.target.value))}
                        disabled={loading || !!testing}
                        className="w-full"
                      />
                    </div>
                    <div>
                      <label className="block text-sm mb-1" style={{ color: colors.textMuted }}>Max Tokens</label>
                      <input
                        type="number"
                        value={formData.max_tokens}
                        onChange={(e) => updateForm("max_tokens", parseInt(e.target.value) || 4096)}
                        disabled={loading || !!testing}
                        className="w-full px-3 py-2 rounded-lg border outline-none transition-colors duration-200"
                        style={{ backgroundColor: colors.input, color: colors.text, borderColor: colors.border }}
                        onFocus={(e) => { e.currentTarget.style.borderColor = roleColor; }}
                        onBlur={(e) => { e.currentTarget.style.borderColor = colors.border; }}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex items-center justify-between p-2.5 rounded-lg" style={{ backgroundColor: colors.input, border: `1px solid ${colors.border}` }}>
                      <span className="text-sm" style={{ color: colors.text }}>流式输出</span>
                      <button
                        onClick={() => updateForm("streaming", !formData.streaming)}
                        disabled={loading || !!testing}
                        className="px-3 py-1 rounded-lg text-sm cursor-pointer transition-colors duration-200"
                        style={{ backgroundColor: formData.streaming ? `${colors.success}20` : `${colors.error}20`, color: formData.streaming ? colors.success : colors.error, border: `1px solid ${formData.streaming ? colors.success : colors.error}40` }}
                      >
                        {formData.streaming ? "开启" : "关闭"}
                      </button>
                    </div>
                    <div className="flex items-center justify-between p-2.5 rounded-lg" style={{ backgroundColor: colors.input, border: `1px solid ${colors.border}` }}>
                      <span className="text-sm" style={{ color: colors.text }}>深度思考</span>
                      <button
                        onClick={() => updateForm("deep_thinking", !formData.deep_thinking)}
                        disabled={loading || !!testing}
                        className="px-3 py-1 rounded-lg text-sm cursor-pointer transition-colors duration-200"
                        style={{ backgroundColor: formData.deep_thinking ? `${colors.success}20` : `${colors.error}20`, color: formData.deep_thinking ? colors.success : colors.error, border: `1px solid ${formData.deep_thinking ? colors.success : colors.error}40` }}
                      >
                        {formData.deep_thinking ? "开启" : "关闭"}
                      </button>
                    </div>
                  </div>
                </div>

                <div className="flex gap-2 mt-4">
                  <button
                    onClick={() => {
                      if (formData.api_key) {
                        testConnection(currentRole, false);
                      } else if (configs[currentRole]?.has_api_key) {
                        testConnection(currentRole, true);
                      } else {
                        showToast("请先填写 API Key", "warning");
                      }
                    }}
                    disabled={loading || !!testing}
                    className="flex-1 px-4 py-2 rounded-lg cursor-pointer disabled:opacity-50 text-sm text-white transition-colors duration-200"
                    style={{ backgroundColor: "#2563eb" }}
                    onMouseEnter={(e) => { if (!e.currentTarget.disabled) e.currentTarget.style.backgroundColor = "#1d4ed8"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "#2563eb"; }}
                  >
                    {testing === currentRole ? "测试中..." : formData.api_key ? "测试当前输入" : "测试已保存配置"}
                  </button>
                  <button
                    onClick={copyConfigToAll}
                    disabled={loading || !!testing || !currentTestPassed}
                    className="flex-1 px-4 py-2 rounded-lg cursor-pointer disabled:opacity-50 text-sm text-white transition-colors duration-200"
                    style={{ backgroundColor: currentTestPassed ? "#7c3aed" : "#555" }}
                    title={!currentTestPassed ? "请先测试当前角色连接" : ""}
                  >
                    {currentTestPassed ? "复制到其他角色" : "需先测试通过"}
                  </button>
                  <button
                    onClick={testAllConnections}
                    disabled={loading || !!testing}
                    className="flex-1 px-4 py-2 rounded-lg cursor-pointer disabled:opacity-50 text-sm text-white transition-colors duration-200"
                    style={{ backgroundColor: "#b45309" }}
                    onMouseEnter={(e) => { if (!e.currentTarget.disabled) e.currentTarget.style.backgroundColor = "#92400e"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "#b45309"; }}
                  >
                    测试全部连接
                  </button>
                </div>
              </>
              )
            )}

            {/* 声音设置标签页 */}
            {activeTab === "audio" && (
              <div className="space-y-6">
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <label className="text-sm font-bold" style={{ color: colors.text }}>背景音乐</label>
                    <button
                      onClick={toggleBgmMuted}
                      className="px-3 py-1 rounded-lg text-sm cursor-pointer transition-colors duration-200"
                      style={{ backgroundColor: bgmMuted ? `${colors.error}20` : `${colors.success}20`, color: bgmMuted ? colors.error : colors.success, border: `1px solid ${bgmMuted ? colors.error : colors.success}40` }}
                    >
                      {bgmMuted ? "已静音" : "开启"}
                    </button>
                  </div>
                  <div className="flex items-center gap-3">
                    <span style={{ color: colors.textMuted }}>🔈</span>
                    <input
                      type="range" min="0" max="1" step="0.01"
                      value={bgmVolume}
                      onChange={(e) => setBgmVolume(parseFloat(e.target.value))}
                      disabled={bgmMuted}
                      className="flex-1"
                    />
                    <span style={{ color: colors.textMuted }}>🔊</span>
                    <span className="w-12 text-right text-sm" style={{ color: colors.text }}>{Math.round(bgmVolume * 100)}%</span>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between items-center mb-3">
                    <label className="text-sm font-bold" style={{ color: colors.text }}>音效</label>
                    <button
                      onClick={toggleSfxMuted}
                      className="px-3 py-1 rounded-lg text-sm cursor-pointer transition-colors duration-200"
                      style={{ backgroundColor: sfxMuted ? `${colors.error}20` : `${colors.success}20`, color: sfxMuted ? colors.error : colors.success, border: `1px solid ${sfxMuted ? colors.error : colors.success}40` }}
                    >
                      {sfxMuted ? "已静音" : "开启"}
                    </button>
                  </div>
                  <div className="flex items-center gap-3">
                    <span style={{ color: colors.textMuted }}>🔈</span>
                    <input
                      type="range" min="0" max="1" step="0.01"
                      value={sfxVolume}
                      onChange={(e) => setSfxVolume(parseFloat(e.target.value))}
                      disabled={sfxMuted}
                      className="flex-1"
                    />
                    <span style={{ color: colors.textMuted }}>🔊</span>
                    <span className="w-12 text-right text-sm" style={{ color: colors.text }}>{Math.round(sfxVolume * 100)}%</span>
                  </div>
                </div>

                <div>
                  <label className="block text-sm mb-3 font-bold" style={{ color: colors.text }}>播放模式</label>
                  <div className="flex gap-2">
                    {[
                      { value: "list_loop" as const, label: "列表循环", icon: "🔁" },
                      { value: "weighted_random" as const, label: "加权随机", icon: "🔀" },
                      { value: "single_loop" as const, label: "单曲循环", icon: "🔂" },
                    ].map(mode => (
                      <button
                        key={mode.value}
                        onClick={() => setPlayMode(mode.value)}
                        className="flex-1 p-3 rounded-lg cursor-pointer transition-colors duration-200 text-center"
                        style={{
                          backgroundColor: playMode === mode.value ? `${colors.accent}15` : colors.input,
                          border: `2px solid ${playMode === mode.value ? colors.accent : colors.border}`,
                          boxShadow: playMode === mode.value ? `0 0 12px ${colors.accent}20` : "none",
                        }}
                      >
                        <div className="text-lg">{mode.icon}</div>
                        <div className="text-xs mt-1" style={{ color: colors.text }}>{mode.label}</div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 底部按钮 */}
          <div className="px-6 py-4 flex gap-3 shrink-0" style={{ borderTop: `1px solid ${colors.border}` }}>
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2.5 rounded-lg cursor-pointer text-sm font-medium transition-colors duration-200"
              style={{ backgroundColor: colors.input, color: colors.text, border: `1px solid ${colors.border}` }}
            >
              关闭
            </button>

            {activeTab === "ai" && configuredCount < AI_ROLES.length && (
              <button
                onClick={onClose}
                className="flex-1 px-4 py-2.5 rounded-lg cursor-pointer text-sm font-medium transition-colors duration-200"
                style={{ backgroundColor: `${colors.accent}20`, color: colors.accent, border: `1px solid ${colors.accent}40` }}
              >
                稍后配置
              </button>
            )}

            {activeTab === "ai" && configuredCount === AI_ROLES.length && (
              <button
                onClick={handleStartGame}
                disabled={loading || !!testing}
                className="flex-1 px-4 py-2.5 rounded-lg cursor-pointer disabled:opacity-50 text-sm font-medium text-white transition-colors duration-200"
                style={{ backgroundColor: colors.success }}
              >
                完成配置，开始游戏
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
