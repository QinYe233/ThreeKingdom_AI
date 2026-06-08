/**
 * 存档管理面板 - 手动存档、读取、删除
 * AI执行中禁止加载存档，操作带音效反馈
 */
import { useState, useEffect, useRef, memo } from "react";
import type { ThemeColors } from "../../theme";
import { saveApi } from "../../utils/api";
import { useGameStore } from "../../stores/gameStore";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { playClickSound } from "../../utils/AudioManager";

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

const SaveLoadPanel = memo(function SaveLoadPanel({
  show,
  onClose,
  theme
}: SaveLoadPanelProps) {
  const { loadSave: storeLoadSave } = useGameStore();
  const [saves, setSaves] = useState<SaveInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSave, setSelectedSave] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [saveDescription, setSaveDescription] = useState("");
  const [saveMessage, setSaveMessage] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  // 消息自动消失（3秒）
  useEffect(() => {
    if (saveMessage) {
      const timer = setTimeout(() => setSaveMessage(""), 3000);
      return () => clearTimeout(timer);
    }
  }, [saveMessage]);

  // 面板进入动画
  useGSAP(() => {
    if (show && containerRef.current) {
      gsap.fromTo(containerRef.current,
        { autoAlpha: 0, scale: 0.92, y: 20 },
        { autoAlpha: 1, scale: 1, y: 0, duration: 0.4, ease: "back.out(1.4)" }
      );
    }
  }, { dependencies: [show], scope: containerRef });

  useEffect(() => {
    if (show) {
      fetchSaves();
    }
  }, [show]);

  const fetchSaves = async () => {
    try {
      setLoading(true);
      const data: any = await saveApi.list();
      setSaves(data);
    } catch (e) {
      console.error("Failed to fetch saves:", e);
      setSaveMessage("获取存档列表失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  const createManualSave = async () => {
    playClickSound();
    try {
      setLoading(true);
      setSaveMessage("");

      const data: any = await saveApi.manual({
        name: saveDescription || undefined,
        description: saveDescription || undefined
      });

      if (data.save_id) {
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

  /** 加载存档 - AI执行中禁止操作 */
  const loadSave = async (saveId: string) => {
    playClickSound();
    // Don't load during AI processing
    const { isProcessing } = useGameStore.getState();
    if (isProcessing) {
      setSaveMessage("AI正在执行中，请等待完成后再加载存档");
      return;
    }

    try {
      setLoading(true);
      setSaveMessage("");

      await storeLoadSave(saveId);
      setSaveMessage("存档加载成功！");
      onClose();
    } catch (e) {
      console.error("Failed to load save:", e);
      setSaveMessage("存档加载失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  const deleteSave = async (saveId: string) => {
    playClickSound();
    try {
      setLoading(true);
      setSaveMessage("");

      const data: any = await saveApi.delete(saveId);

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

  const handleClose = () => {
    playClickSound();
    onClose();
  };

  if (!show) return null;

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: "rgba(61, 43, 31, 0.85)" }}
    >
      <div ref={containerRef} className="rounded-lg p-6" style={{
        width: "650px",
        maxWidth: "90vw",
        backgroundColor: theme.card,
        border: `2px solid ${theme.border}`,
        boxShadow: "0 8px 32px rgba(61, 43, 31, 0.4)"
      }}>
        {/* Header */}
        <div className="flex items-center justify-between mb-5 pb-4 border-b-2"
          style={{ borderColor: theme.border }}
        >
          <div className="text-xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
            <span>📜</span>
            <span>存档管理</span>
            <span className="text-sm font-normal ml-2" style={{ color: theme.textMuted }}>
              (上限 {saves.length}/20)
            </span>
          </div>
          <button
            onClick={handleClose}
            className="w-8 h-8 rounded-full flex items-center justify-center hover:opacity-80 transition-opacity"
            style={{ backgroundColor: theme.border, color: theme.textMuted }}
          >
            ✕
          </button>
        </div>

        {/* Message */}
        {saveMessage && (
          <div className="mb-4 p-3 rounded"
            style={{
              backgroundColor: saveMessage.includes("成功") ? "rgba(26, 111, 19, 0.15)" : "rgba(197, 48, 48, 0.15)",
              border: `1px solid ${saveMessage.includes("成功") ? theme.success : theme.error}`,
              color: saveMessage.includes("成功") ? theme.success : theme.error
            }}
          >
            {saveMessage}
          </div>
        )}

        {/* Manual Save Section */}
        <div className="mb-5 p-4 rounded" style={{ backgroundColor: theme.bg, border: `1px solid ${theme.border}` }}>
          <div className="text-sm mb-2 font-medium" style={{ color: theme.text }}>
            创建新存档
          </div>
          <div className="flex gap-3">
            <input
              type="text"
              value={saveDescription}
              onChange={(e) => setSaveDescription(e.target.value)}
              placeholder="输入存档描述（可选）..."
              className="flex-1 px-4 py-2.5 rounded text-sm"
              disabled={loading}
              style={{
                backgroundColor: theme.input,
                border: `1px solid ${theme.border}`,
                color: theme.text
              }}
            />
            <button
              onClick={createManualSave}
              disabled={loading}
              className="px-6 py-2.5 rounded text-sm font-medium text-white disabled:opacity-50 hover:opacity-90 transition-opacity"
              style={{ backgroundColor: theme.accent }}
            >
              {loading ? "保存中..." : "保存"}
            </button>
          </div>
        </div>

        {/* Save List */}
        <div className="mb-2 text-sm font-medium" style={{ color: theme.textMuted }}>
          存档列表
        </div>
        <div className="overflow-y-auto rounded" style={{ maxHeight: "320px", backgroundColor: theme.bg }}>
          {loading ? (
            <div className="text-center py-10" style={{ color: theme.textMuted }}>
              加载中...
            </div>
          ) : saves.length === 0 ? (
            <div className="text-center py-10" style={{ color: theme.textMuted }}>
              暂无存档
            </div>
          ) : (
            <div className="divide-y" style={{ borderColor: theme.border }}>
              {saves.map((save) => {
                const type = formatSaveType(save.metadata);
                const isSelected = selectedSave === save.save_id;
                return (
                  <div
                    key={save.save_id}
                    className={`p-4 cursor-pointer transition-all hover:opacity-90 ${
                      isSelected ? "ring-2 ring-inset" : ""
                    }`}
                    style={{
                      backgroundColor: isSelected ? theme.card : "transparent",
                      borderColor: isSelected ? theme.accent : "transparent"
                    }}
                    onClick={() => { playClickSound(); setSelectedSave(save.save_id); }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <span className="text-xs px-2 py-1 rounded font-medium"
                          style={{ backgroundColor: type.color, color: "#fff" }}
                        >
                          {type.text}
                        </span>
                        <span className="font-bold" style={{ color: theme.text }}>
                          第 {save.round} 回
                        </span>
                        {save.description && (
                          <span className="text-sm" style={{ color: theme.textMuted }}>
                            - {save.description}
                          </span>
                        )}
                      </div>
                      <span className="text-xs" style={{ color: theme.textMuted }}>
                        {formatTimestamp(save.timestamp)}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={(e) => { e.stopPropagation(); loadSave(save.save_id); }}
                        disabled={loading}
                        className="px-4 py-1.5 rounded text-xs font-medium text-white disabled:opacity-50 hover:opacity-90 transition-opacity"
                        style={{ backgroundColor: theme.success }}
                      >
                        读取
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); playClickSound(); setSelectedSave(save.save_id); setShowDeleteConfirm(true); }}
                        disabled={loading}
                        className="px-4 py-1.5 rounded text-xs font-medium text-white disabled:opacity-50 hover:opacity-90 transition-opacity"
                        style={{ backgroundColor: theme.error }}
                      >
                        删除
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Delete Confirmation */}
        {showDeleteConfirm && selectedSave && (
          <div className="mt-4 p-4 rounded"
            style={{ backgroundColor: theme.error + "20", border: `1px solid ${theme.error}` }}
          >
            <div className="text-sm mb-3" style={{ color: theme.text }}>
              确认删除此存档？此操作不可恢复。
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => { playClickSound(); setShowDeleteConfirm(false); }}
                className="px-4 py-2 rounded text-sm font-medium hover:opacity-80 transition-opacity"
                style={{ backgroundColor: theme.border, color: theme.text }}
              >
                取消
              </button>
              <button
                onClick={() => selectedSave && deleteSave(selectedSave)}
                className="px-4 py-2 rounded text-sm font-medium text-white hover:opacity-80 transition-opacity"
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
});

export default SaveLoadPanel;
