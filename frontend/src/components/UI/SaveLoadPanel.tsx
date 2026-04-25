import { useState, useEffect } from "react";
import type { ThemeColors } from "../../theme";

interface SaveInfo {
  save_id: string;
  timestamp: string;
  round: number;
  metadata: {
    manual: boolean;
    autosave: boolean;
    player_country: string | null;
  };
  description?: string;
}

interface SaveLoadPanelProps {
  show: boolean;
  onClose: () => void;
  theme: ThemeColors;
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

const SaveLoadPanel = function SaveLoadPanel({
  show,
  onClose,
  theme
}: SaveLoadPanelProps) {
  const [saves, setSaves] = useState<SaveInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSave, setSelectedSave] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [saveDescription, setSaveDescription] = useState("");
  const [saveMessage, setSaveMessage] = useState("");

  useEffect(() => {
    if (show) {
      fetchSaves();
    }
  }, [show]);

  const fetchSaves = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/save/list`);
      const data = await res.json();
      setSaves(data);
    } catch (e) {
      console.error("Failed to fetch saves:", e);
      setSaveMessage("获取存档列表失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  const createManualSave = async () => {
    try {
      setLoading(true);
      setSaveMessage("");

      const res = await fetch(`${API_BASE}/save/manual`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: saveDescription || undefined,
          description: saveDescription || undefined
        }),
      });
      const data = await res.json();

      if (data.success) {
        setSaveMessage("存档创建成功！");
        await fetchSaves();
        setSaveDescription("");
      } else {
        setSaveMessage("存档创建失败");
      }
    } catch (e) {
      console.error("Failed to create save:", e);
      setSaveMessage("存档创建失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  const loadSave = async (saveId: string) => {
    try {
      setLoading(true);
      setSaveMessage("");

      const res = await fetch(`${API_BASE}/save/load/${saveId}`, {
        method: "POST"
      });
      const data = await res.json();

      if (data.success) {
        setSaveMessage("存档加载成功，页面将重新加载...");
        setTimeout(() => {
          window.location.reload();
        }, 500);
      } else {
        setSaveMessage("存档加载失败");
      }
    } catch (e) {
      console.error("Failed to load save:", e);
      setSaveMessage("存档加载失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  const deleteSave = async (saveId: string) => {
    try {
      setLoading(true);
      setSaveMessage("");

      const res = await fetch(`${API_BASE}/save/${saveId}`, {
        method: "DELETE"
      });
      const data = await res.json();

      if (data.deleted) {
        setSaveMessage("存档删除成功");
        await fetchSaves();
        setShowDeleteConfirm(false);
        setSelectedSave(null);
      } else {
        setSaveMessage("存档删除失败");
      }
    } catch (e) {
      console.error("Failed to delete save:", e);
      setSaveMessage("存档删除失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('zh-CN');
  };

  const formatSaveType = (metadata: any) => {
    if (metadata.autosave) return { text: "自动", color: theme.warning };
    if (metadata.manual) return { text: "手动", color: theme.success };
    return { text: "未知", color: theme.text };
  };

  if (!show) return null;

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: "rgba(61, 43, 31, 0.8)" }}
    >
      <div className="rounded-lg p-6" style={{
        width: "600px",
        backgroundColor: theme.card,
        border: `2px solid ${theme.border}`,
        boxShadow: "0 8px 24px rgba(61, 43, 31, 0.3)"
      }}>
        {/* Header */}
        <div className="flex items-center justify-between mb-6 pb-4 border-b-2"
          style={{ borderColor: theme.border }}
        >
          <div className="text-lg font-bold" style={{ color: theme.text }}>
            📜 存档管理
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center"
            style={{ backgroundColor: theme.border, color: theme.textMuted }}
          >
            ✕
          </button>
        </div>

        {/* Save Message */}
        {saveMessage && (
          <div className="mb-4 p-3 rounded"
            style={{
              backgroundColor: saveMessage.includes("成功") ? "rgba(26, 111, 19, 0.1)" : "rgba(197, 48, 48, 0.1)",
              border: `1px solid ${saveMessage.includes("成功") ? theme.success : theme.error}`,
              color: saveMessage.includes("成功") ? theme.text : theme.error
            }}
          >
            {saveMessage}
          </div>
        )}

        {/* Manual Save */}
        <div className="mb-6">
          <div className="text-sm mb-2" style={{ color: theme.textMuted }}>
            手动存档
          </div>
          <div className="flex gap-2 mb-2">
            <input
              type="text"
              value={saveDescription}
              onChange={(e) => setSaveDescription(e.target.value)}
              placeholder="存档描述（可选）..."
              className="flex-1 px-3 py-2 rounded text-sm"
              disabled={loading}
              style={{
                backgroundColor: theme.input,
                border: `1px solid ${theme.border}`,
                color: theme.text
              }}
            />
            <button
              onClick={createManualSave}
              disabled={loading || !saveDescription.trim()}
              className="px-4 py-2 rounded text-sm text-white disabled:opacity-50"
              style={{ backgroundColor: theme.accent }}
            >
              {loading ? "保存中..." : "保存"}
            </button>
          </div>
        </div>

        {/* Save List */}
        <div className="flex-1 overflow-y-auto" style={{ maxHeight: "300px" }}>
          {loading ? (
            <div className="text-center py-8" style={{ color: theme.textMuted }}>
              加载中...
            </div>
          ) : saves.length === 0 ? (
            <div className="text-center py-8" style={{ color: theme.textMuted }}>
              暂无存档
            </div>
          ) : (
            saves.map((save) => (
              <div
                key={save.save_id}
                className={`p-3 mb-2 rounded border cursor-pointer transition-all ${
                  selectedSave === save.save_id ? "ring-2 ring-offset-1" : ""
                }`}
                style={{
                  backgroundColor: theme.bg,
                  borderColor: selectedSave === save.save_id ? theme.accent : theme.border,
                  borderWidth: selectedSave === save.save_id ? "2px" : "1px"
                }}
                onClick={() => setSelectedSave(save.save_id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2 mb-1">
                    {(() => {
                      const type = formatSaveType(save.metadata);
                      return (
                        <span className="text-xs px-1 py-0.5 rounded"
                          style={{ backgroundColor: type.color, color: "#fff" }}
                        >
                          {type.text}
                        </span>
                      );
                    })()}
                    <span className="text-sm font-bold" style={{ color: theme.text }}>
                      第{save.round}回
                    </span>
                  </div>
                  {save.description && (
                    <div className="text-xs mb-1" style={{ color: theme.textMuted }}>
                      {save.description}
                    </div>
                  )}
                  <div className="text-xs" style={{ color: theme.textMuted }}>
                    {formatTimestamp(save.timestamp)}
                  </div>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      loadSave(save.save_id);
                    }}
                    disabled={loading}
                    className="px-3 py-1 rounded text-xs text-white disabled:opacity-50"
                    style={{ backgroundColor: theme.success }}
                  >
                    读取
                  </button>
                  {!save.metadata.autosave && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowDeleteConfirm(true);
                      }}
                      disabled={loading}
                      className="px-3 py-1 rounded text-xs text-white disabled:opacity-50"
                      style={{ backgroundColor: theme.error }}
                    >
                      删除
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Delete Confirmation */}
        {showDeleteConfirm && selectedSave && (
          <div className="mt-4 p-3 rounded"
            style={{ backgroundColor: theme.error + "20", border: `1px solid ${theme.error}` }}
          >
            <div className="text-sm mb-2" style={{ color: theme.text }}>
              确认删除存档"{selectedSave}"？此操作不可恢复。
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-3 py-1 rounded text-xs"
                style={{ backgroundColor: theme.border, color: theme.text }}
              >
                取消
              </button>
              <button
                onClick={() => selectedSave && deleteSave(selectedSave)}
                className="px-3 py-1 rounded text-xs text-white"
                style={{ backgroundColor: theme.error }}
              >
                确认删除
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SaveLoadPanel;
