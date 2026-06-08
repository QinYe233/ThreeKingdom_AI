/**
 * 音频状态管理 - Zustand Store
 * 管理背景音乐和音效的播放状态、音量、播放模式等，持久化到localStorage
 */

import { create } from "zustand";
import { AudioManager } from "../utils/AudioManager";
import type { TrackInfo } from "../utils/AudioManager";
import { loadSettings, saveSettings } from "../utils/settings";
import type { PlayMode } from "../utils/settings";

interface AudioState {
  // 状态
  currentTrack: string | null;
  isPlaying: boolean;
  playMode: PlayMode;
  bgmVolume: number;
  sfxVolume: number;
  fadeDuration: number;
  bgmMuted: boolean;
  sfxMuted: boolean;
  trackList: TrackInfo[];
  initialized: boolean;

  // 操作
  play: () => void;
  pause: () => void;
  next: () => void;
  setPlayMode: (mode: PlayMode) => void;
  setBgmVolume: (volume: number) => void;
  setSfxVolume: (volume: number) => void;
  setFadeDuration: (duration: number) => void;
  toggleBgmMuted: () => void;
  toggleSfxMuted: () => void;
  playSfx: (name: string) => void;
  playTrack: (index: number) => void;
  initAudio: () => void;
}

// 从 localStorage 读取初始设置
const _initialSettings = loadSettings();

export const useAudioStore = create<AudioState>((set, get) => ({
  // 初始状态 - 从 localStorage 读取
  currentTrack: null,
  isPlaying: false,
  playMode: _initialSettings.playMode,
  bgmVolume: _initialSettings.bgmVolume,
  sfxVolume: _initialSettings.sfxVolume,
  fadeDuration: _initialSettings.fadeDuration,
  bgmMuted: _initialSettings.bgmMuted,
  sfxMuted: _initialSettings.sfxMuted,
  trackList: AudioManager.getTrackList(),
  initialized: false,

  // 初始化音频系统
  initAudio: () => {
    if (get().initialized) return;

    const settings = loadSettings();

    // 同步设置到 AudioManager
    AudioManager.setPlayMode(settings.playMode);
    AudioManager.setBgmVolume(settings.bgmVolume);
    AudioManager.setSfxVolume(settings.sfxVolume);
    AudioManager.setFadeDuration(settings.fadeDuration);
    AudioManager.setBgmMuted(settings.bgmMuted);
    AudioManager.setSfxMuted(settings.sfxMuted);

    // 监听 AudioManager 事件
    AudioManager.onTrackChange = (track) => {
      set({ currentTrack: track.name });
    };

    AudioManager.onPlayStateChange = (isPlaying) => {
      set({ isPlaying });
    };

    set({
      playMode: settings.playMode,
      bgmVolume: settings.bgmVolume,
      sfxVolume: settings.sfxVolume,
      fadeDuration: settings.fadeDuration,
      bgmMuted: settings.bgmMuted,
      sfxMuted: settings.sfxMuted,
      initialized: true,
    });
  },

  // 播放
  play: () => {
    AudioManager.play().catch(console.error);
  },

  // 暂停
  pause: () => {
    AudioManager.pause().catch(console.error);
  },

  // 下一首
  next: () => {
    AudioManager.next().catch(console.error);
  },

  // 设置播放模式
  setPlayMode: (mode: PlayMode) => {
    AudioManager.setPlayMode(mode);
    saveSettings({ playMode: mode });
    set({ playMode: mode });
  },

  // 设置 BGM 音量
  setBgmVolume: (volume: number) => {
    AudioManager.setBgmVolume(volume);
    saveSettings({ bgmVolume: volume });
    set({ bgmVolume: volume });
  },

  // 设置 SFX 音量
  setSfxVolume: (volume: number) => {
    AudioManager.setSfxVolume(volume);
    saveSettings({ sfxVolume: volume });
    set({ sfxVolume: volume });
  },

  // 设置淡入淡出时长
  setFadeDuration: (duration: number) => {
    AudioManager.setFadeDuration(duration);
    saveSettings({ fadeDuration: duration });
    set({ fadeDuration: duration });
  },

  // 切换 BGM 静音
  toggleBgmMuted: () => {
    const newMuted = !get().bgmMuted;
    AudioManager.setBgmMuted(newMuted);
    saveSettings({ bgmMuted: newMuted });
    set({ bgmMuted: newMuted });
  },

  // 切换 SFX 静音
  toggleSfxMuted: () => {
    const newMuted = !get().sfxMuted;
    AudioManager.setSfxMuted(newMuted);
    saveSettings({ sfxMuted: newMuted });
    set({ sfxMuted: newMuted });
  },

  // 播放音效
  playSfx: (name: string) => {
    AudioManager.playSfx(name);
  },

  // 播放指定曲目
  playTrack: (index: number) => {
    AudioManager.playTrack(index).catch(console.error);
  },
}));
