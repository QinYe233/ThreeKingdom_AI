/**
 * 音频管理器 - 单例模式
 * 管理背景音乐（BGM）和UI音效（SFX），支持淡入淡出、播放模式切换
 * 通过AudioContext + GainNode实现精确的音量控制和淡入淡出效果
 */

import type { PlayMode } from "./settings";

// 曲目信息
export interface TrackInfo {
  name: string;
  url: string;
}

// BGM曲目列表（硬编码，浏览器无法扫描目录）
const BGM_TRACKS: TrackInfo[] = [
  { name: "battle", url: "/Music/background/battle.mp3" },
  { name: "fantasy", url: "/Music/background/fantasy.wav" },
  { name: "last-war", url: "/Music/background/last-war.wav" },
  { name: "maou", url: "/Music/background/maou.wav" },
  { name: "neighofwar", url: "/Music/background/neighofwar.wav" },
  { name: "worldsend", url: "/Music/background/worldsend.mp3" },
];

// UI 音效映射
const SFX_MAP: Record<string, string> = {
  "button-click-single-short-soft-close": "/Music/ui/button-click-single-short-soft-close.mp3",
  "button-in-space-muted-close": "/Music/ui/button-in-space-muted-close.mp3",
  "notification-sound": "/Music/ui/notification-sound.mp3",
};

class AudioManagerClass {
  // BGM 相关
  private bgmAudio: HTMLAudioElement | null = null;
  private audioContext: AudioContext | null = null;
  private gainNode: GainNode | null = null;
  private sourceNode: MediaElementAudioSourceNode | null = null;
  private trackList: TrackInfo[] = [...BGM_TRACKS];
  private currentTrackIndex = -1;
  private _playMode: PlayMode = "list_loop";
  private _bgmVolume = 0.5;
  private _bgmMuted = false;
  private _fadeDuration = 1.5;
  private _isPlaying = false;
  private _fadeTimer: ReturnType<typeof setTimeout> | null = null;

  // SFX 相关
  private sfxPool: Map<string, HTMLAudioElement> = new Map();
  private _sfxVolume = 0.7;
  private _sfxMuted = false;

  // 回调
  public onTrackChange?: (track: { name: string }) => void;
  public onPlayStateChange?: (isPlaying: boolean) => void;

  // 是否已初始化 AudioContext（需要用户交互后才能创建）
  private contextInitialized = false;

  constructor() {
    // 预加载音效
    this.preloadSfx();
  }

  /** 惰性初始化 AudioContext（必须在用户交互后调用） */
  private ensureAudioContext(): AudioContext | null {
    if (this.contextInitialized && this.audioContext) {
      return this.audioContext;
    }
    try {
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      this.gainNode = this.audioContext.createGain();
      this.gainNode.connect(this.audioContext.destination);
      this.gainNode.gain.value = this._bgmMuted ? 0 : this._bgmVolume;
      this.contextInitialized = true;
      return this.audioContext;
    } catch (e) {
      console.error("无法创建 AudioContext:", e);
      return null;
    }
  }

  /** 将 HTMLAudioElement 连接到 AudioContext（仅连接一次） */
  private connectToContext(audio: HTMLAudioElement) {
    if (!this.sourceNode && this.audioContext && this.gainNode) {
      try {
        this.sourceNode = this.audioContext.createMediaElementSource(audio);
        this.sourceNode.connect(this.gainNode);
      } catch (e) {
        // 已经连接过，忽略
        console.warn("音频源连接异常:", e);
      }
    }
  }

  /** 预加载 UI 音效 */
  private preloadSfx() {
    for (const [name, url] of Object.entries(SFX_MAP)) {
      const audio = new Audio(url);
      audio.preload = "auto";
      audio.volume = this._sfxMuted ? 0 : this._sfxVolume;
      audio.addEventListener("error", () => {
        console.warn(`[AudioManager] 音效预加载失败: ${name} (${url})`);
      });
      this.sfxPool.set(name, audio);
    }
  }

  /** 获取曲目列表 */
  getTrackList(): TrackInfo[] {
    return this.trackList;
  }

  /** 获取当前播放模式 */
  get playMode(): PlayMode {
    return this._playMode;
  }

  /** 获取当前 BGM 音量 */
  get bgmVolume(): number {
    return this._bgmVolume;
  }

  /** 获取当前 SFX 音量 */
  get sfxVolume(): number {
    return this._sfxVolume;
  }

  /** 获取淡入淡出时长 */
  get fadeDuration(): number {
    return this._fadeDuration;
  }

  /** 获取 BGM 是否静音 */
  get bgmMuted(): boolean {
    return this._bgmMuted;
  }

  /** 获取 SFX 是否静音 */
  get sfxMuted(): boolean {
    return this._sfxMuted;
  }

  /** 获取是否正在播放 */
  get isPlaying(): boolean {
    return this._isPlaying;
  }

  /** 获取当前曲目名 */
  get currentTrackName(): string | null {
    if (this.currentTrackIndex >= 0 && this.currentTrackIndex < this.trackList.length) {
      return this.trackList[this.currentTrackIndex].name;
    }
    return null;
  }

  /** 播放背景音乐 */
  async play(): Promise<void> {
    // 确保在用户交互时初始化 AudioContext
    this.ensureAudioContext();

    if (this.trackList.length === 0) return;

    if (this.currentTrackIndex < 0) {
      this.currentTrackIndex = 0;
    }

    const track = this.trackList[this.currentTrackIndex];

    if (!this.bgmAudio) {
      this.bgmAudio = new Audio(track.url);
      this.bgmAudio.loop = false;
      this.bgmAudio.volume = 1.0; // 音量由 gainNode 控制

      // 连接到 AudioContext
      if (this.audioContext && this.gainNode) {
        this.connectToContext(this.bgmAudio);
      }

      // 曲目播放结束，自动播放下一首
      this.bgmAudio.addEventListener("ended", () => {
        this.handleTrackEnd();
      });
    } else {
      // 如果已有音频对象，切换曲目
      if (this.bgmAudio.src !== new URL(track.url, window.location.origin).href) {
        await this.fadeOut(() => {
          if (this.bgmAudio) {
            this.bgmAudio.src = track.url;
          }
        });
      }
    }

    try {
      // 恢复 AudioContext（浏览器策略要求用户交互后才能播放）
      if (this.audioContext?.state === "suspended") {
        await this.audioContext.resume();
      }

      this._isPlaying = true;
      this.onPlayStateChange?.(true);
      this.onTrackChange?.({ name: track.name });

      await this.bgmAudio.play();
      await this.fadeIn();
    } catch (e) {
      console.warn("播放失败:", e);
      this._isPlaying = false;
      this.onPlayStateChange?.(false);
    }
  }

  /** 暂停背景音乐（即时，无淡出） */
  async pause(): Promise<void> {
    if (!this.bgmAudio || !this._isPlaying) return;

    if (this.bgmAudio) {
      this.bgmAudio.pause();
    }

    this._isPlaying = false;
    this.onPlayStateChange?.(false);
  }

  /** 播放下一首 */
  async next(): Promise<void> {
    if (this.trackList.length === 0) return;

    const nextIndex = this.getNextTrackIndex();
    this.currentTrackIndex = nextIndex;

    if (this._isPlaying) {
      await this.fadeOut(async () => {
        if (this.bgmAudio) {
          const track = this.trackList[this.currentTrackIndex];
          this.bgmAudio.src = track.url;
          this.bgmAudio.currentTime = 0;
        }
      });

      const track = this.trackList[this.currentTrackIndex];
      this.onTrackChange?.({ name: track.name });

      try {
        if (this.audioContext?.state === "suspended") {
          await this.audioContext.resume();
        }
        await this.bgmAudio?.play();
        await this.fadeIn();
      } catch (e) {
        console.warn("切换曲目失败:", e);
      }
    } else {
      const track = this.trackList[this.currentTrackIndex];
      this.onTrackChange?.({ name: track.name });
    }
  }

  /** 播放指定曲目 */
  async playTrack(index: number): Promise<void> {
    if (index < 0 || index >= this.trackList.length) return;

    this.currentTrackIndex = index;

    if (this._isPlaying) {
      await this.fadeOut(async () => {
        if (this.bgmAudio) {
          this.bgmAudio.src = this.trackList[this.currentTrackIndex].url;
          this.bgmAudio.currentTime = 0;
        }
      });

      const track = this.trackList[this.currentTrackIndex];
      this.onTrackChange?.({ name: track.name });

      try {
        if (this.audioContext?.state === "suspended") {
          await this.audioContext.resume();
        }
        await this.bgmAudio?.play();
        await this.fadeIn();
      } catch (e) {
        console.warn("播放指定曲目失败:", e);
      }
    } else {
      // 未在播放，直接开始播放
      await this.play();
    }
  }

  /** 设置播放模式 */
  setPlayMode(mode: PlayMode): void {
    this._playMode = mode;

    // 单曲循环时设置 loop
    if (this.bgmAudio) {
      this.bgmAudio.loop = mode === "single_loop";
    }
  }

  /** 设置 BGM 音量 - 仅通过 gainNode 控制，bgmAudio.volume 保持 1.0 */
  setBgmVolume(volume: number): void {
    this._bgmVolume = Math.max(0, Math.min(1, volume));
    if (this.gainNode && !this._bgmMuted) {
      this.gainNode.gain.value = this._bgmVolume;
    }
  }

  /** 设置 SFX 音量 */
  setSfxVolume(volume: number): void {
    this._sfxVolume = Math.max(0, Math.min(1, volume));
    for (const audio of this.sfxPool.values()) {
      audio.volume = this._sfxMuted ? 0 : this._sfxVolume;
    }
  }

  /** 设置淡入淡出时长 */
  setFadeDuration(duration: number): void {
    this._fadeDuration = Math.max(0, Math.min(5, duration));
  }

  /** 切换 BGM 静音 - 仅通过 gainNode 控制 */
  setBgmMuted(muted: boolean): void {
    this._bgmMuted = muted;
    if (this.gainNode) {
      this.gainNode.gain.value = muted ? 0 : this._bgmVolume;
    }
  }

  /** 切换 SFX 静音 */
  setSfxMuted(muted: boolean): void {
    this._sfxMuted = muted;
    for (const audio of this.sfxPool.values()) {
      audio.volume = muted ? 0 : this._sfxVolume;
    }
  }

  /** 播放 UI 音效 */
  playSfx(name: string): void {
    const audio = this.sfxPool.get(name);
    if (!audio) {
      console.warn(`未找到音效: ${name}`);
      return;
    }

    // 克隆音频对象以支持重叠播放
    try {
      const clone = audio.cloneNode() as HTMLAudioElement;
      clone.volume = this._sfxMuted ? 0 : this._sfxVolume;
      clone.addEventListener("ended", () => {
        clone.remove();
      });
      clone.play().catch(() => {
        // 浏览器阻止自动播放时静默忽略
      });
    } catch (e) {
      console.warn("播放音效失败:", e);
    }
  }

  /** 曲目播放结束处理 */
  private async handleTrackEnd(): Promise<void> {
    if (this._playMode === "single_loop") {
      // 单曲循环由 HTMLAudioElement.loop 处理
      return;
    }

    const nextIndex = this.getNextTrackIndex();
    this.currentTrackIndex = nextIndex;

    const track = this.trackList[this.currentTrackIndex];
    this.onTrackChange?.({ name: track.name });

    if (this.bgmAudio) {
      this.bgmAudio.src = track.url;
      this.bgmAudio.currentTime = 0;
      await this.bgmAudio.play().catch(() => {});
      await this.fadeIn();
    }
  }

  /** 获取下一首曲目索引 */
  private getNextTrackIndex(): number {
    if (this._playMode === "weighted_random") {
      // 加权随机：随机选择一个不同的曲目
      if (this.trackList.length <= 1) return 0;
      let next: number;
      do {
        next = Math.floor(Math.random() * this.trackList.length);
      } while (next === this.currentTrackIndex);
      return next;
    }

    // 列表循环
    return (this.currentTrackIndex + 1) % this.trackList.length;
  }

  /** 淡入效果 */
  private async fadeIn(): Promise<void> {
    if (!this.gainNode || this._fadeDuration <= 0) {
      if (this.gainNode) {
        this.gainNode.gain.value = this._bgmMuted ? 0 : this._bgmVolume;
      }
      return;
    }

    const ctx = this.audioContext;
    if (!ctx) return;

    const now = ctx.currentTime;
    this.gainNode.gain.cancelScheduledValues(now);
    this.gainNode.gain.setValueAtTime(0, now);
    this.gainNode.gain.linearRampToValueAtTime(this._bgmMuted ? 0 : this._bgmVolume, now + this._fadeDuration);
  }

  /** 淡出效果，完成后执行回调 */
  private async fadeOut(onComplete: () => void): Promise<void> {
    if (!this.gainNode || this._fadeDuration <= 0) {
      onComplete();
      return;
    }

    const ctx = this.audioContext;
    if (!ctx) {
      onComplete();
      return;
    }

    const now = ctx.currentTime;
    this.gainNode.gain.cancelScheduledValues(now);
    this.gainNode.gain.setValueAtTime(this.gainNode.gain.value, now);
    this.gainNode.gain.linearRampToValueAtTime(0, now + this._fadeDuration);

    // 等待淡出完成
    await new Promise<void>((resolve) => {
      // 清除上一次未完成的淡出定时器
      if (this._fadeTimer) clearTimeout(this._fadeTimer);
      this._fadeTimer = setTimeout(() => {
        this._fadeTimer = null;
        onComplete();
        resolve();
      }, this._fadeDuration * 1000 + 50);
    });
  }
}

// 单例导出
export const AudioManager = new AudioManagerClass();

// 便捷函数：播放点击音效
export function playClickSound(): void {
  AudioManager.playSfx("button-click-single-short-soft-close");
}

// 便捷函数：播放通知音效
export function playNotificationSound(): void {
  AudioManager.playSfx("notification-sound");
}
