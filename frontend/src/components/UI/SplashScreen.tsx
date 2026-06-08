import { useRef, useEffect, useState, useCallback } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";

interface SplashScreenProps {
  onComplete: () => void;
}

/**
 * 启动画面 - 依次展示开发者Logo和App图标，带GSAP淡入淡出效果
 * 包含图片预加载和超时保护机制
 */
export default function SplashScreen({ onComplete }: SplashScreenProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const logoRef = useRef<HTMLImageElement>(null);
  const iconRef = useRef<HTMLImageElement>(null);
  const [imagesLoaded, setImagesLoaded] = useState(false);
  const completedRef = useRef(false);

  /** 安全完成回调 - 防止重复调用 */
  const safeOnComplete = useCallback(() => {
    if (completedRef.current) return;
    completedRef.current = true;
    onComplete();
  }, [onComplete]);

  // 等待图片加载
  useEffect(() => {
    const logoImg = new Image();
    const iconImg = new Image();
    let loaded = 0;

    const checkLoaded = () => {
      loaded++;
      if (loaded >= 2) {
        setImagesLoaded(true);
      }
    };

    logoImg.onload = checkLoaded;
    logoImg.onerror = checkLoaded;
    iconImg.onload = checkLoaded;
    iconImg.onerror = checkLoaded;

    logoImg.src = "/logo.png";
    iconImg.src = "/icon.png";

    // 超时保护
    const timeout = setTimeout(() => setImagesLoaded(true), 2000);
    return () => clearTimeout(timeout);
  }, []);

  // 超时保护：如果 GSAP 动画卡住，8秒后强制完成
  useEffect(() => {
    const timeout = setTimeout(() => {
      console.warn("SplashScreen timeout, forcing completion");
      safeOnComplete();
    }, 8000);
    return () => clearTimeout(timeout);
  }, [safeOnComplete]);

  useGSAP(() => {
    if (!imagesLoaded || !containerRef.current) return;

    const tl = gsap.timeline({
      onComplete: safeOnComplete,
    });

    // Logo: 淡入 1.0s → 保持 1.5s → 淡出 0.6s
    if (logoRef.current) {
      tl.fromTo(logoRef.current,
        { autoAlpha: 0, scale: 0.9 },
        { autoAlpha: 1, scale: 1, duration: 1.0, ease: "power2.out" }
      )
      .to({}, { duration: 1.5 })
      .to(logoRef.current, { autoAlpha: 0, scale: 0.95, duration: 0.6, ease: "power2.in" });
    }

    // 间隔 0.8s
    tl.to({}, { duration: 0.8 });

    // Icon: 淡入 1.0s → 保持 1.5s → 淡出 0.6s
    if (iconRef.current) {
      tl.fromTo(iconRef.current,
        { autoAlpha: 0, scale: 0.9 },
        { autoAlpha: 1, scale: 1, duration: 1.0, ease: "power2.out" }
      )
      .to({}, { duration: 1.5 })
      .to(iconRef.current, { autoAlpha: 0, scale: 0.95, duration: 0.6, ease: "power2.in" });
    }

    // 整体淡出 0.6s
    if (containerRef.current) {
      tl.to(containerRef.current, { autoAlpha: 0, duration: 0.6, ease: "power2.in" });
    }
  }, { scope: containerRef, dependencies: [imagesLoaded, safeOnComplete] });

  return (
    <div
      ref={containerRef}
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "#000000",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
      }}
    >
      <img
        ref={logoRef}
        src="/logo.png"
        alt="logo"
        style={{
          position: "absolute",
          width: 240,
          height: 240,
          objectFit: "contain",
          visibility: "hidden",
        }}
      />
      <img
        ref={iconRef}
        src="/icon.png"
        alt="icon"
        style={{
          position: "absolute",
          width: 180,
          height: 180,
          objectFit: "contain",
          visibility: "hidden",
        }}
      />
    </div>
  );
}
