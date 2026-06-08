/**
 * 面板滑入滑出动画 Hook
 * 使用GSAP驱动高性能transform动画，替代CSS transition
 */
import { useRef, useState } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";

/**
 * 面板滑入滑出动画 Hook
 * 替代 CSS transition-transform，使用 GSAP 驱动高性能 transform 动画
 *
 * @param show - 是否显示面板
 * @param direction - 滑动方向，"up" 从底部滑入，"left" 从左侧滑入
 * @param distance - 滑动距离（px），默认 400
 * @param duration - 动画时长（秒），默认 0.3
 * @returns panelRef - 绑定到面板DOM的ref，visible - 面板是否可见
 */
export function usePanelAnimation(
  show: boolean,
  direction: "up" | "left" = "up",
  distance: number = 400,
  duration: number = 0.3
) {
  const panelRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useGSAP(() => {
    if (show) {
      setVisible(true);
      const from = direction === "up" ? { y: distance } : { x: -distance };
      const to = direction === "up" ? { y: 0 } : { x: 0 };
      gsap.fromTo(panelRef.current, { ...from, autoAlpha: 0 }, { ...to, autoAlpha: 1, duration, ease: "power2.out", overwrite: true });
    } else if (visible) {
      const to = direction === "up" ? { y: distance } : { x: -distance };
      gsap.to(panelRef.current, {
        ...to, autoAlpha: 0, duration, ease: "power2.in", overwrite: true,
        onComplete: () => setVisible(false),
      });
    }
  }, { scope: panelRef, dependencies: [show] });

  return { panelRef, visible };
}
