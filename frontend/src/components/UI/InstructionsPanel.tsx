import { useEffect, useRef, useState } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { THEME_COLORS } from "../../theme";

interface InstructionsPanelProps {
  show: boolean;
  onClose: () => void;
}

/**
 * 游戏说明面板 - 展示游戏流程、操作说明、参数调整等帮助信息
 * 使用GSAP实现面板淡入淡出动画，支持Escape键关闭
 */
export default function InstructionsPanel({ show, onClose }: InstructionsPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useGSAP(() => {
    if (show) {
      setVisible(true);
      // 淡入
      gsap.fromTo(overlayRef.current,
        { autoAlpha: 0 },
        { autoAlpha: 1, duration: 0.3, ease: "power2.out" }
      );
      gsap.fromTo(panelRef.current,
        { scale: 0.95, autoAlpha: 0 },
        { scale: 1, autoAlpha: 1, duration: 0.3, ease: "power2.out" }
      );
    } else {
      // 淡出
      gsap.to(overlayRef.current, { autoAlpha: 0, duration: 0.3, ease: "power2.in" });
      gsap.to(panelRef.current, {
        scale: 0.95, autoAlpha: 0, duration: 0.3, ease: "power2.in",
        onComplete: () => setVisible(false),
      });
    }
  }, { scope: containerRef, dependencies: [show] });

  // Escape关闭
  useEffect(() => {
    if (!show) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [show, onClose]);

  if (!visible) return null;

  const theme = THEME_COLORS;

  return (
    <div ref={containerRef}>
      <div
        ref={overlayRef}
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          backgroundColor: "rgba(0, 0, 0, 0.6)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 50,
        }}
      >
        <div
          ref={panelRef}
          onClick={(e) => e.stopPropagation()}
          style={{
            backgroundColor: theme.card,
            border: `1px solid ${theme.border}`,
            borderRadius: 8,
            maxWidth: 600,
            width: "90%",
            maxHeight: "80vh",
            display: "flex",
            flexDirection: "column",
            boxShadow: "0 8px 32px rgba(61, 43, 31, 0.3)",
          }}
        >
          {/* 标题栏 */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "16px 20px",
              borderBottom: `1px solid ${theme.border}`,
            }}
          >
            <h2
              style={{
                color: theme.accent,
                fontSize: "1.25rem",
                fontFamily: "Ma Shan Zheng, SimSun, serif",
                margin: 0,
                letterSpacing: "0.05em",
              }}
            >
              游戏说明
            </h2>
            <button
              onClick={onClose}
              style={{
                background: "none",
                border: "none",
                color: theme.textMuted,
                fontSize: "1.25rem",
                cursor: "pointer",
                padding: "4px 8px",
                lineHeight: 1,
              }}
            >
              ✕
            </button>
          </div>

          {/* 内容区 */}
          <div
            style={{
              padding: "20px",
              overflowY: "auto",
              flex: 1,
            }}
          >
            {/* 1. 游戏流程 */}
            <section style={{ marginBottom: 20 }}>
              <h3 style={{ color: theme.text, fontSize: "1rem", fontWeight: "bold", marginBottom: 8, fontFamily: "STSong, serif" }}>
                1. 游戏流程
              </h3>
              <ul style={{ color: theme.textMuted, fontSize: "0.875rem", lineHeight: 1.8, paddingLeft: 20, margin: 0, fontFamily: "KaiTi, serif" }}>
                <li>本游戏为AI驱动的三国策略对战游戏，魏、蜀、吴三方势力由独立AI控制</li>
                <li>首先在"设置"中配置AI模型（需要为魏、蜀、吴、史官各配置一个AI模型）</li>
                <li>点击"开始"初始化游戏世界</li>
                <li>通过"推进"按钮或"自动"模式观看AI对战</li>
                <li>每回合魏→蜀→吴依次行动，AI会根据战略目标做出决策</li>
              </ul>
            </section>

            {/* 2. 操作说明 */}
            <section style={{ marginBottom: 20 }}>
              <h3 style={{ color: theme.text, fontSize: "1rem", fontWeight: "bold", marginBottom: 8, fontFamily: "STSong, serif" }}>
                2. 操作说明
              </h3>
              <ul style={{ color: theme.textMuted, fontSize: "0.875rem", lineHeight: 1.8, paddingLeft: 20, margin: 0, fontFamily: "KaiTi, serif" }}>
                <li><strong style={{ color: theme.text }}>推进</strong>：执行当前国家的AI行动</li>
                <li><strong style={{ color: theme.text }}>自动</strong>：自动连续推进，再次点击停止</li>
                <li><strong style={{ color: theme.text }}>历史</strong>：查看各国的AI思考记录</li>
                <li><strong style={{ color: theme.text }}>史官</strong>：查看编年史叙事</li>
                <li><strong style={{ color: theme.text }}>存档</strong>：手动存档/读档</li>
                <li><strong style={{ color: theme.text }}>返回</strong>：返回主菜单（自动存档）</li>
              </ul>
            </section>

            {/* 3. 参数调整 */}
            <section style={{ marginBottom: 20 }}>
              <h3 style={{ color: theme.text, fontSize: "1rem", fontWeight: "bold", marginBottom: 8, fontFamily: "STSong, serif" }}>
                3. 参数调整
              </h3>
              <ul style={{ color: theme.textMuted, fontSize: "0.875rem", lineHeight: 1.8, paddingLeft: 20, margin: 0, fontFamily: "KaiTi, serif" }}>
                <li>在"设置→AI配置"中可调整各AI的Temperature、Max Tokens等参数</li>
                <li>Temperature越高，AI决策越有创造性；越低越保守</li>
                <li>可开启"流式输出"，实时查看AI思考过程</li>
                <li>可开启"深度思考"模式，让AI进行更深入的推理</li>
              </ul>
            </section>

            {/* 4. 特殊中立势力 */}
            <section style={{ marginBottom: 20 }}>
              <h3 style={{ color: theme.text, fontSize: "1rem", fontWeight: "bold", marginBottom: 8, fontFamily: "STSong, serif" }}>
                4. 特殊中立势力
              </h3>
              <ul style={{ color: theme.textMuted, fontSize: "0.875rem", lineHeight: 1.8, paddingLeft: 20, margin: 0, fontFamily: "KaiTi, serif" }}>
                <li>地图上的<strong style={{ color: theme.text }}>山越、南中、凉州、公孙度、士燮</strong>为特殊中立势力</li>
                <li>攻占其领地可获得额外奖励：<strong style={{ color: theme.text }}>+200 金币、+5 士气、+3 秩序</strong></li>
              </ul>
            </section>

            {/* 5. 存档与安全 */}
            <section style={{ marginBottom: 20 }}>
              <h3 style={{ color: theme.text, fontSize: "1rem", fontWeight: "bold", marginBottom: 8, fontFamily: "STSong, serif" }}>
                5. 存档与安全
              </h3>
              <ul style={{ color: theme.textMuted, fontSize: "0.875rem", lineHeight: 1.8, paddingLeft: 20, margin: 0, fontFamily: "KaiTi, serif" }}>
                <li>存档文件保存在 <code style={{ backgroundColor: theme.border, padding: "2px 6px", borderRadius: 3, fontSize: "0.8rem", color: theme.text }}>backend/data/saves/</code> 目录下</li>
                <li>点击"返回"按钮将自动存档并返回主菜单</li>
                <li>API Key 存储在本地 <code style={{ backgroundColor: theme.border, padding: "2px 6px", borderRadius: 3, fontSize: "0.8rem", color: theme.text }}>backend/data/ai_config.json</code>，仅保存在您的本机，绝不会发送到任何第三方服务器</li>
              </ul>
            </section>

            {/* 6. 自定义背景音乐 */}
            <section>
              <h3 style={{ color: theme.text, fontSize: "1rem", fontWeight: "bold", marginBottom: 8, fontFamily: "STSong, serif" }}>
                6. 自定义背景音乐
              </h3>
              <ul style={{ color: theme.textMuted, fontSize: "0.875rem", lineHeight: 1.8, paddingLeft: 20, margin: 0, fontFamily: "KaiTi, serif" }}>
                <li>在游戏安装目录的 <code style={{ backgroundColor: theme.border, padding: "2px 6px", borderRadius: 3, fontSize: "0.8rem", color: theme.text }}>frontend/public/Music/background/</code> 文件夹中添加音频文件</li>
                <li>支持格式：MP3、WAV、OGG、FLAC</li>
                <li>添加后重新启动游戏即可在播放列表中看到新曲目</li>
                <li>在"设置→声音"中可调整音量、播放模式等</li>
              </ul>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
