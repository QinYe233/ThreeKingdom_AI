/**
 * 音乐播放器组件 - 紧凑型播放控件 + 曲目列表弹窗
 * 支持播放/暂停、上下首、播放模式切换、GSAP跑马灯动画
 */

import { useState, useRef, useEffect } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useAudioStore } from "../../stores/audioStore";
import { THEME_COLORS } from "../../theme";
import type { PlayMode } from "../../utils/settings";

// 播放模式配置
const PLAY_MODE_CONFIG: { value: PlayMode; icon: string; label: string }[] = [
  { value: "list_loop", icon: "🔁", label: "列表循环" },
  { value: "weighted_random", icon: "🔀", label: "加权随机" },
  { value: "single_loop", icon: "🔂", label: "单曲循环" },
];

// 曲目中文名称映射
const TRACK_DISPLAY_NAMES: Record<string, string> = {
  battle: "战鼓",
  fantasy: "幻想",
  "last-war": "终战",
  maou: "魔王",
  neighofwar: "战马嘶鸣",
  worldsend: "世界尽头",
};

export default function MusicPlayer() {
  const colors = THEME_COLORS;
  const {
    currentTrack, isPlaying, playMode, trackList,
    play, pause, next, setPlayMode, playTrack,
  } = useAudioStore();

  const [showPlaylist, setShowPlaylist] = useState(false);
  const playlistRef = useRef<HTMLDivElement>(null);
  const marqueeRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // 曲名过长时启用GSAP跑马灯动画
  const shouldMarquee = currentTrack && currentTrack.length > 4;
  useGSAP(() => {
    if (shouldMarquee && marqueeRef.current) {
      gsap.to(marqueeRef.current, {
        xPercent: -50,
        duration: 8,
        ease: "none",
        repeat: -1,
      });
    }
    return () => {
      if (marqueeRef.current) {
        gsap.killTweensOf(marqueeRef.current);
        gsap.set(marqueeRef.current, { xPercent: 0 });
      }
    };
  }, { scope: containerRef, dependencies: [shouldMarquee] });

  // 点击外部关闭播放列表
  useEffect(() => {
    if (!showPlaylist) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (playlistRef.current && !playlistRef.current.contains(e.target as Node)) {
        setShowPlaylist(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showPlaylist]);

  /** 循环切换播放模式 */
  const cyclePlayMode = () => {
    const currentIndex = PLAY_MODE_CONFIG.findIndex((m) => m.value === playMode);
    const nextIndex = (currentIndex + 1) % PLAY_MODE_CONFIG.length;
    setPlayMode(PLAY_MODE_CONFIG[nextIndex].value);
  };

  // 当前播放模式图标
  const currentModeConfig = PLAY_MODE_CONFIG.find((m) => m.value === playMode) || PLAY_MODE_CONFIG[0];

  // 显示名
  const displayName = currentTrack ? (TRACK_DISPLAY_NAMES[currentTrack] || currentTrack) : "未播放";

  return (
    <div ref={containerRef} className="relative flex items-center gap-1" style={{ height: 32 }}>
      {/* 曲目名 - 跑马灯 */}
      <div
        className="overflow-hidden"
        style={{ width: 120, height: 20 }}
      >
        <div
          ref={marqueeRef}
          className="whitespace-nowrap"
          style={{
            color: isPlaying ? colors.accent : colors.textMuted,
            fontSize: "0.75rem",
            lineHeight: "20px",
          }}
        >
          <span>🎵 {displayName}</span>
          {currentTrack && currentTrack.length > 4 && (
            <>
              <span style={{ paddingLeft: 40 }}>🎵 {displayName}</span>
            </>
          )}
        </div>
      </div>

      {/* 播放/暂停 */}
      <button
        onClick={isPlaying ? pause : play}
        className="w-7 h-7 flex items-center justify-center rounded cursor-pointer transition-colors"
        style={{
          backgroundColor: isPlaying ? colors.accent : colors.input,
          color: isPlaying ? "#fff" : colors.text,
          border: `1px solid ${colors.border}`,
          fontSize: "0.7rem",
        }}
        title={isPlaying ? "暂停" : "播放"}
      >
        {isPlaying ? "⏸" : "▶"}
      </button>

      {/* 下一首 */}
      <button
        onClick={next}
        className="w-7 h-7 flex items-center justify-center rounded cursor-pointer transition-colors"
        style={{
          backgroundColor: colors.input,
          color: colors.text,
          border: `1px solid ${colors.border}`,
          fontSize: "0.7rem",
        }}
        title="下一首"
      >
        ⏭
      </button>

      {/* 播放模式 */}
      <button
        onClick={cyclePlayMode}
        className="w-7 h-7 flex items-center justify-center rounded cursor-pointer transition-colors"
        style={{
          backgroundColor: colors.input,
          color: colors.text,
          border: `1px solid ${colors.border}`,
          fontSize: "0.7rem",
        }}
        title={currentModeConfig.label}
      >
        {currentModeConfig.icon}
      </button>

      {/* 曲目列表 */}
      <button
        onClick={() => setShowPlaylist((prev) => !prev)}
        className="w-7 h-7 flex items-center justify-center rounded cursor-pointer transition-colors"
        style={{
          backgroundColor: showPlaylist ? colors.accent : colors.input,
          color: showPlaylist ? "#fff" : colors.text,
          border: `1px solid ${colors.border}`,
          fontSize: "0.7rem",
        }}
        title="曲目列表"
      >
        📋
      </button>

      {/* 曲目列表弹窗 */}
      {showPlaylist && (
        <div
          ref={playlistRef}
          className="absolute top-full right-0 mt-1 rounded-lg shadow-lg overflow-hidden z-50"
          style={{
            width: 240,
            backgroundColor: colors.card,
            border: `1px solid ${colors.border}`,
            boxShadow: "0 8px 24px rgba(61, 43, 31, 0.25)",
          }}
        >
          {/* 弹窗头部 */}
          <div
            className="flex items-center justify-between px-3 py-2"
            style={{
              backgroundColor: colors.header,
              borderBottom: `1px solid ${colors.border}`,
            }}
          >
            <span className="text-xs font-bold" style={{ color: colors.text }}>
              🎵 曲目列表
            </span>
            <div className="flex items-center gap-1">
              <span className="text-xs" style={{ color: colors.textMuted }}>
                {currentModeConfig.icon} {currentModeConfig.label}
              </span>
              <button
                onClick={() => setShowPlaylist(false)}
                className="w-5 h-5 flex items-center justify-center rounded cursor-pointer"
                style={{ color: colors.textMuted, fontSize: "0.7rem" }}
              >
                ✕
              </button>
            </div>
          </div>

          {/* 曲目列表 */}
          <div className="max-h-64 overflow-y-auto">
            {trackList.map((track, index) => {
              const isActive = currentTrack === track.name;
              const trackDisplayName = TRACK_DISPLAY_NAMES[track.name] || track.name;

              return (
                <button
                  key={track.name}
                  onClick={() => {
                    playTrack(index);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-left cursor-pointer transition-colors"
                  style={{
                    backgroundColor: isActive ? `${colors.accent}20` : "transparent",
                    borderBottom: `1px solid ${colors.border}30`,
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.backgroundColor = `${colors.input}`;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.backgroundColor = "transparent";
                    }
                  }}
                >
                  {/* 播放指示器 */}
                  <span className="w-4 text-center text-xs" style={{ color: isActive ? colors.accent : colors.textMuted }}>
                    {isActive && isPlaying ? "▶" : isActive ? "⏸" : `${index + 1}`}
                  </span>

                  {/* 曲目名 */}
                  <span
                    className="text-sm flex-1"
                    style={{
                      color: isActive ? colors.accent : colors.text,
                      fontWeight: isActive ? "bold" : "normal",
                    }}
                  >
                    {trackDisplayName}
                  </span>

                  {/* 当前播放标记 */}
                  {isActive && isPlaying && (
                    <span className="text-xs" style={{ color: colors.accent }}>
                      ♪
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
