import { useState, useEffect } from "react";
import { THEME_COLORS } from "../../theme";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

interface RoleInfo {
  name: string;
  description: string;
}

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

export default function Settings({ onClose, onComplete }: SettingsProps) {
  const colors = THEME_COLORS;
  const [roles, setRoles] = useState<Record<string, RoleInfo>>({});
  const [configs, setConfigs] = useState<Record<string, ConfigStatus>>({});
  const [currentRole, setCurrentRole] = useState<string>("wei");
  const [formData, setFormData] = useState({
    model: "",
    api_key: "",
    base_url: "",
    temperature: 0.7,
    max_tokens: 2000,
  });
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [connectionTested, setConnectionTested] = useState(false);
  const [message, setMessage] = useState<{ type: "error" | "success"; text: string } | null>(null);

  useEffect(() => {
    fetchStatus();
  }, []);

  useEffect(() => {
    if (configs[currentRole]) {
      const cfg = configs[currentRole];
      setFormData({
        model: cfg.model || "",
        api_key: cfg.api_key || "",
        base_url: cfg.base_url || "",
        temperature: cfg.temperature || 0.7,
        max_tokens: cfg.max_tokens || 2000,
      });
    }
  }, [currentRole, configs]);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/ai/status`);
      const data = await res.json();
      setRoles(data.roles || {});
      setConfigs(data.configs || {});
      if (data.configs && !currentRole) {
        setCurrentRole(Object.keys(data.configs)[0] || "wei");
      }
    } catch (e) {
      console.error(e);
      setMessage({ type: "error", text: "无法加载配置状态" });
    }
  };

  const updateForm = (field: string, value: string | number) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setMessage(null);
    setConnectionTested(false);
  };

  const testConnection = async () => {
    if (!formData.base_url) {
      setMessage({ type: "error", text: "请输入Base URL" });
      return;
    }
    if (!formData.model) {
      setMessage({ type: "error", text: "请输入模型名称" });
      return;
    }
    if (!formData.api_key) {
      setMessage({ type: "error", text: "请输入API Key" });
      return;
    }

    setTesting(true);
    setMessage(null);

    try {
      const res = await fetch(`${API_BASE}/ai/test-connection`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: formData.model,
          api_key: formData.api_key,
          base_url: formData.base_url,
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setMessage({ type: "success", text: "连接测试成功！" });
        setConnectionTested(true);
      } else {
        setMessage({ type: "error", text: data.detail || "连接测试失败" });
        setConnectionTested(false);
      }
    } catch (e) {
      setMessage({ type: "error", text: "连接测试失败" });
      setConnectionTested(false);
    }
    setTesting(false);
  };

  const saveConfig = async () => {
    if (!formData.base_url) {
      setMessage({ type: "error", text: "请输入Base URL" });
      return;
    }
    if (!formData.model) {
      setMessage({ type: "error", text: "请输入模型名称" });
      return;
    }
    if (!formData.api_key && !configs[currentRole]?.has_api_key) {
      setMessage({ type: "error", text: "请输入API Key" });
      return;
    }
    
    if (formData.api_key && !connectionTested) {
      setMessage({ type: "error", text: "请先测试连接" });
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const body: any = {
        role: currentRole,
        model: formData.model,
        base_url: formData.base_url,
        temperature: formData.temperature,
        max_tokens: formData.max_tokens,
      };

      if (formData.api_key) {
        body.api_key = formData.api_key;
      } else if (configs[currentRole]?.has_api_key) {
        body.api_key = "__keep_existing__";
      }

      const res = await fetch(`${API_BASE}/ai/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await res.json();
      if (res.ok) {
        setMessage({ type: "success", text: `${roles[currentRole]?.name || currentRole}配置已保存` });
        setConnectionTested(false);
        await fetchStatus();
      } else {
        setMessage({ type: "error", text: data.detail || "保存失败" });
      }
    } catch (e) {
      setMessage({ type: "error", text: "保存失败" });
    }
    setLoading(false);
  };

  const handleComplete = async () => {
    const checkRes = await fetch(`${API_BASE}/ai/check`);
    const checkData = await checkRes.json();
    if (checkData.all_configured) {
      onComplete();
      onClose();
    } else {
      const unconfigured = Object.entries(configs)
        .filter(([_, cfg]) => !cfg.is_valid)
        .map(([role, _]) => roles[role]?.name || role)
        .join("、");
      setMessage({ type: "error", text: `以下角色未完成配置: ${unconfigured}` });
    }
  };

  const roleInfo = roles[currentRole];
  const currentConfig = configs[currentRole];

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div
        className="rounded-lg p-6 w-[600px] max-h-[90vh] overflow-y-auto"
        style={{ backgroundColor: colors.card, border: `1px solid ${colors.border}` }}
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold" style={{ color: colors.accent }}>AI 配置</h2>
          <button onClick={onClose} className="text-2xl cursor-pointer" style={{ color: colors.textMuted }}>×</button>
        </div>

        {message && (
          <div
            className="mb-4 p-3 rounded text-sm"
            style={{
              backgroundColor: message.type === "error" ? `${colors.error}20` : `${colors.success}20`,
              border: `1px solid ${message.type === "error" ? colors.error : colors.success}`,
              color: message.type === "error" ? colors.error : colors.success,
            }}
          >
            {message.text}
          </div>
        )}

        <div className="mb-4">
          <div className="flex gap-2 flex-wrap">
            {Object.entries(roles).map(([id, info]) => (
              <button
                key={id}
                onClick={() => { setCurrentRole(id); setMessage(null); setConnectionTested(false); }}
                className="px-4 py-2 rounded text-sm cursor-pointer transition-colors"
                style={{
                  backgroundColor: currentRole === id ? colors.accent : colors.input,
                  color: currentRole === id ? "#fff" : colors.text,
                  border: `1px solid ${colors.border}`,
                }}
              >
                {info.name}
                {configs[id]?.is_valid && <span className="ml-1">✓</span>}
              </button>
            ))}
          </div>
        </div>

        {roleInfo && (
          <div className="mb-4 p-3 rounded text-sm" style={{ backgroundColor: colors.input, color: colors.textMuted }}>
            {roleInfo.description}
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm mb-1" style={{ color: colors.textMuted }}>
              Base URL <span style={{ color: colors.error }}>*</span>
            </label>
            <input
              type="text"
              value={formData.base_url}
              onChange={(e) => updateForm("base_url", e.target.value)}
              placeholder="https://api.openai.com/v1"
              disabled={loading || testing}
              className="w-full px-3 py-2 rounded border"
              style={{ backgroundColor: colors.input, color: colors.text, borderColor: colors.border }}
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
              placeholder="gpt-4o"
              disabled={loading || testing}
              className="w-full px-3 py-2 rounded border"
              style={{ backgroundColor: colors.input, color: colors.text, borderColor: colors.border }}
            />
          </div>

          <div>
            <label className="block text-sm mb-1" style={{ color: colors.textMuted }}>
              API Key <span style={{ color: colors.error }}>*</span>
              {currentConfig?.has_api_key && !formData.api_key && (
                <span style={{ color: colors.success }}> (已配置)</span>
              )}
            </label>
            <input
              type="password"
              value={formData.api_key}
              onChange={(e) => updateForm("api_key", e.target.value)}
              placeholder={currentConfig?.has_api_key ? "已配置，留空保持不变" : "sk-..."}
              disabled={loading || testing}
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
                disabled={loading || testing}
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-sm mb-1" style={{ color: colors.textMuted }}>Max Tokens</label>
              <input
                type="number"
                value={formData.max_tokens}
                onChange={(e) => updateForm("max_tokens", parseInt(e.target.value) || 2000)}
                disabled={loading || testing}
                className="w-full px-3 py-2 rounded border"
                style={{ backgroundColor: colors.input, color: colors.text, borderColor: colors.border }}
              />
            </div>
          </div>
        </div>

        <div className="flex gap-2 mt-6">
          <button
            onClick={testConnection}
            disabled={loading || testing || !formData.api_key}
            className="flex-1 px-4 py-2 bg-blue-700 hover:bg-blue-600 text-white rounded cursor-pointer disabled:opacity-50"
          >
            {testing ? "测试中..." : "测试连接"}
          </button>
          <button
            onClick={saveConfig}
            disabled={loading || testing}
            className="flex-1 px-4 py-2 text-white rounded cursor-pointer disabled:opacity-50"
            style={{ backgroundColor: colors.accent }}
          >
            {loading ? "保存中..." : "保存配置"}
          </button>
        </div>

        <div className="mt-4 pt-4" style={{ borderTop: `1px solid ${colors.border}` }}>
          <button
            onClick={handleComplete}
            disabled={loading || testing}
            className="w-full px-4 py-2 bg-green-700 hover:bg-green-600 text-white rounded cursor-pointer disabled:opacity-50"
          >
            完成设置
          </button>
        </div>
      </div>
    </div>
  );
}
