import { useState, useEffect } from "react";
import { THEME_COLORS, COUNTRY_COLORS, AI_ROLES } from "../../theme";
import { aiApi } from "../../utils/api";

interface ConfigStatus {
  model: string;
  base_url: string;
  has_api_key: boolean;
  temperature: number;
  max_tokens: number;
  is_valid: boolean;
}

interface SettingsProps {
  onClose: () => void;
  onComplete: () => void;
  theme?: "dark" | "parchment";
}

function getRoleColor(roleId: string): string {
  const role = AI_ROLES.find(r => r.id === roleId);
  if (role && role.countryKey) {
    return COUNTRY_COLORS[role.countryKey] || "#B8860B";
  }
  return "#B8860B";
}

export default function Settings({ onClose, onComplete }: SettingsProps) {
  const colors = THEME_COLORS;
  const [configs, setConfigs] = useState<Record<string, ConfigStatus>>({});
  const [currentRole, setCurrentRole] = useState<string>("wei");
  const [formData, setFormData] = useState({
    model: "",
    api_key: "",
    base_url: "",
    temperature: 0.7,
    max_tokens: 4096,
  });
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "error" | "success" | "info"; text: string } | null>(null);
  const [testResults, setTestResults] = useState<Record<string, "success" | "fail">>({});
  const [apiLoaded, setApiLoaded] = useState(false);

  useEffect(() => {
    fetchStatus();
  }, []);

  useEffect(() => {
    const cfg = configs[currentRole];
    if (cfg) {
      setFormData({
        model: cfg.model || "",
        api_key: "",
        base_url: cfg.base_url || "",
        temperature: cfg.temperature || 0.7,
        max_tokens: cfg.max_tokens || 4096,
      });
    } else {
      setFormData({ model: "", api_key: "", base_url: "", temperature: 0.7, max_tokens: 4096 });
    }
  }, [currentRole, configs]);

  const fetchStatus = async () => {
    try {
      const data: any = await aiApi.getStatus();
      setConfigs(data.configs || {});
      setApiLoaded(true);
    } catch (e) {
      console.error(e);
      setApiLoaded(true);
    }
  };

  const updateForm = (field: string, value: string | number) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setMessage(null);
  };

  const testConnection = async (role: string, useSaved: boolean) => {
    setTesting(role);
    setMessage(null);

    try {
      let data: any;
      if (useSaved) {
        data = await aiApi.testConnectionByRole(role);
      } else {
        if (!formData.base_url || !formData.model || !formData.api_key) {
          setMessage({ type: "error", text: "请先填写 Base URL、模型名称和 API Key" });
          setTesting(null);
          return;
        }
        data = await aiApi.testConnection({
          model: formData.model,
          api_key: formData.api_key,
          base_url: formData.base_url,
        });
      }

      setTestResults(prev => ({ ...prev, [role]: "success" }));
      setMessage({ type: "success", text: `${AI_ROLES.find(r => r.id === role)?.name || role} 连接测试成功！模型: ${data.model || ""}` });
    } catch (e: any) {
      setTestResults(prev => ({ ...prev, [role]: "fail" }));
      const detail = e?.response?.data?.detail || e?.message || "连接测试失败";
      setMessage({ type: "error", text: detail });
    }
    setTesting(null);
  };

  const saveConfig = async (role: string) => {
    if (!formData.base_url) {
      setMessage({ type: "error", text: "请输入 Base URL" });
      return;
    }
    if (!formData.model) {
      setMessage({ type: "error", text: "请输入模型名称" });
      return;
    }

    const hasExistingKey = configs[role]?.has_api_key;
    if (!formData.api_key && !hasExistingKey) {
      setMessage({ type: "error", text: "请输入 API Key" });
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const body: Record<string, unknown> = {
        role,
        model: formData.model,
        base_url: formData.base_url,
        temperature: formData.temperature,
        max_tokens: formData.max_tokens,
      };

      if (formData.api_key) {
        body.api_key = formData.api_key;
      } else if (hasExistingKey) {
        body.api_key = "__keep_existing__";
      }

      await aiApi.saveConfig(body);
      setMessage({ type: "success", text: `${AI_ROLES.find(r => r.id === role)?.name || role} 配置已保存` });
      await fetchStatus();
    } catch (e: any) {
      const detail = e?.response?.data?.detail || "保存失败";
      setMessage({ type: "error", text: detail });
    }
    setLoading(false);
  };

  const copyConfigToAll = async () => {
    if (!formData.base_url || !formData.model) {
      setMessage({ type: "error", text: "请先填写当前角色的 Base URL 和模型名称" });
      return;
    }

    const hasExistingKey = configs[currentRole]?.has_api_key;
    if (!formData.api_key && !hasExistingKey) {
      setMessage({ type: "error", text: "请先填写当前角色的 API Key" });
      return;
    }

    setLoading(true);
    setMessage(null);

    const otherRoles = AI_ROLES.filter(r => r.id !== currentRole);
    let savedCount = 0;

    for (const role of otherRoles) {
      try {
        const body: Record<string, unknown> = {
          role: role.id,
          model: formData.model,
          base_url: formData.base_url,
          temperature: formData.temperature,
          max_tokens: formData.max_tokens,
        };

        if (formData.api_key) {
          body.api_key = formData.api_key;
        } else if (hasExistingKey) {
          body.api_key = "__keep_existing__";
        }

        await aiApi.saveConfig(body);
        savedCount++;
      } catch (e) {
        console.error(e);
      }
    }

    await fetchStatus();
    setMessage({ type: "success", text: `已将当前配置复制到 ${savedCount} 个角色` });
    setLoading(false);
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
      } catch {
        results[role.id] = "fail";
      }
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
      setMessage({ type: "error", text: "没有已配置的角色可供测试" });
    }
  };

  const handleComplete = async () => {
    try {
      const checkData: any = await aiApi.checkConfig();
      if (checkData.all_configured) {
        onComplete();
        onClose();
      } else {
        const unconfigured = AI_ROLES
          .filter(r => !configs[r.id]?.is_valid)
          .map(r => r.name)
          .join("、");
        setMessage({ type: "error", text: `以下角色未完成配置: ${unconfigured}` });
      }
    } catch (e) {
      setMessage({ type: "error", text: "无法检查配置状态，请确认后端服务正在运行" });
    }
  };

  const currentRoleInfo = AI_ROLES.find(r => r.id === currentRole)!;
  const currentConfig = configs[currentRole];
  const hasExistingKey = currentConfig?.has_api_key;
  const configuredCount = AI_ROLES.filter(r => configs[r.id]?.is_valid).length;
  const roleColor = getRoleColor(currentRole);

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div
        className="rounded-lg p-6 w-[680px] max-h-[92vh] overflow-y-auto"
        style={{ backgroundColor: colors.card, border: `1px solid ${colors.border}` }}
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold" style={{ color: colors.accent }}>AI 模型配置</h2>
          <div className="text-sm" style={{ color: colors.textMuted }}>
            已配置 {configuredCount}/{AI_ROLES.length}
          </div>
        </div>

        {message && (
          <div
            className="mb-4 p-3 rounded text-sm"
            style={{
              backgroundColor: message.type === "error" ? `${colors.error}20` : message.type === "info" ? `${colors.accent}20` : `${colors.success}20`,
              border: `1px solid ${message.type === "error" ? colors.error : message.type === "info" ? colors.accent : colors.success}`,
              color: message.type === "error" ? colors.error : message.type === "info" ? colors.accent : colors.success,
            }}
          >
            {message.text}
          </div>
        )}

        <div className="mb-4">
          <div className="text-sm mb-2" style={{ color: colors.textMuted }}>
            点击下方角色标签，为每个角色分别配置 AI 模型（可使用不同模型和 API 提供商）
          </div>
          <div className="grid grid-cols-4 gap-2">
            {AI_ROLES.map(role => {
              const cfg = configs[role.id];
              const testResult = testResults[role.id];
              const isActive = currentRole === role.id;
              const isTestingThis = testing === role.id;
              const rColor = getRoleColor(role.id);

              let borderStyle = `2px solid ${rColor}40`;
              if (testResult === "success") borderStyle = "2px solid #22c55e";
              else if (testResult === "fail") borderStyle = "2px solid #ef4444";
              else if (cfg?.is_valid) borderStyle = `2px solid ${rColor}`;
              if (isActive) borderStyle = `2px solid ${rColor}`;

              return (
                <button
                  key={role.id}
                  onClick={() => { setCurrentRole(role.id); setMessage(null); }}
                  className="p-3 rounded cursor-pointer transition-all text-center"
                  style={{
                    backgroundColor: isActive ? `${rColor}30` : colors.input,
                    border: borderStyle,
                  }}
                >
                  <div className="text-base font-bold" style={{ color: rColor }}>{role.name}</div>
                  <div className="text-xs mt-1 truncate" style={{ color: colors.textMuted }}>
                    {isTestingThis ? "⏳ 测试中..." :
                     cfg?.is_valid ? cfg.model :
                     "未配置"}
                  </div>
                  <div className="text-xs mt-1">
                    {cfg?.is_valid ? (
                      testResult === "success" ? <span style={{ color: "#22c55e" }}>✓ 连接正常</span> :
                      testResult === "fail" ? <span style={{ color: "#ef4444" }}>✗ 连接失败</span> :
                      <span style={{ color: rColor }}>✓ 已配置</span>
                    ) : (
                      <span style={{ color: colors.textMuted }}>○ 待配置</span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="mb-3 p-3 rounded text-sm" style={{ backgroundColor: `${roleColor}10`, border: `1px solid ${roleColor}40`, color: colors.textMuted }}>
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
              className="w-full px-3 py-2 rounded border"
              style={{ backgroundColor: colors.input, color: colors.text, borderColor: colors.border }}
            />
            <div className="text-xs mt-1 flex gap-4" style={{ color: colors.textMuted }}>
              <span>OpenAI: https://api.openai.com/v1</span>
              <span>DeepSeek: https://api.deepseek.com</span>
            </div>
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
              className="w-full px-3 py-2 rounded border"
              style={{ backgroundColor: colors.input, color: colors.text, borderColor: colors.border }}
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
              className="w-full px-3 py-2 rounded border"
              style={{ backgroundColor: colors.input, color: colors.text, borderColor: colors.border }}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm mb-1" style={{ color: colors.textMuted }}>
                Temperature: {formData.temperature}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
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
                className="w-full px-3 py-2 rounded border"
                style={{ backgroundColor: colors.input, color: colors.text, borderColor: colors.border }}
              />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 mt-4">
          <button
            onClick={() => testConnection(currentRole, false)}
            disabled={loading || !!testing || !formData.api_key}
            className="px-4 py-2 bg-blue-700 hover:bg-blue-600 text-white rounded cursor-pointer disabled:opacity-50 text-sm"
          >
            {testing === currentRole ? "测试中..." : "测试当前输入"}
          </button>
          <button
            onClick={() => testConnection(currentRole, true)}
            disabled={loading || !!testing || !hasExistingKey}
            className="px-4 py-2 bg-teal-700 hover:bg-teal-600 text-white rounded cursor-pointer disabled:opacity-50 text-sm"
          >
            {testing === currentRole ? "测试中..." : "测试已保存配置"}
          </button>
          <button
            onClick={() => saveConfig(currentRole)}
            disabled={loading || !!testing}
            className="px-4 py-2 text-white rounded cursor-pointer disabled:opacity-50 text-sm"
            style={{ backgroundColor: roleColor }}
          >
            {loading ? "保存中..." : `保存 ${currentRoleInfo.name} 配置`}
          </button>
          <button
            onClick={copyConfigToAll}
            disabled={loading || !!testing}
            className="px-4 py-2 bg-purple-700 hover:bg-purple-600 text-white rounded cursor-pointer disabled:opacity-50 text-sm"
          >
            {loading ? "复制中..." : "复制到其他角色"}
          </button>
        </div>

        <div className="flex gap-2 mt-3">
          <button
            onClick={testAllConnections}
            disabled={loading || !!testing}
            className="flex-1 px-4 py-2 bg-amber-700 hover:bg-amber-600 text-white rounded cursor-pointer disabled:opacity-50 text-sm"
          >
            测试全部连接
          </button>
        </div>

        <div className="mt-4 pt-4" style={{ borderTop: `1px solid ${colors.border}` }}>
          <button
            onClick={handleComplete}
            disabled={loading || !!testing}
            className="w-full px-4 py-2 bg-green-700 hover:bg-green-600 text-white rounded cursor-pointer disabled:opacity-50"
          >
            完成设置
          </button>
        </div>
      </div>
    </div>
  );
}
