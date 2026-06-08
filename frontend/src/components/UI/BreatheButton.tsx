import { useRef } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";

/**
 * 呼吸动画按钮组件
 * 鼠标悬停时触发呼吸缩放效果，使用GSAP驱动高性能动画
 */
export function BreatheButton({
  children,
  className = "",
  style,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const ref = useRef<HTMLButtonElement>(null);

  useGSAP(() => {
    const el = ref.current;
    if (!el) return;

    const breathe = gsap.to(el, {
      scale: 1.02,
      opacity: 0.9,
      duration: 1,
      ease: "sine.inOut",
      yoyo: true,
      repeat: -1,
      paused: true,
    });

    const onMouseEnter = () => {
      breathe.restart();
      gsap.to(el, { scale: 1.05, duration: 0.3, ease: "power2.out", overwrite: true });
    };
    const onMouseLeave = () => {
      breathe.pause();
      gsap.to(el, { scale: 1, opacity: 1, duration: 0.3, ease: "power2.out", overwrite: true });
    };

    el.addEventListener("mouseenter", onMouseEnter);
    el.addEventListener("mouseleave", onMouseLeave);

    return () => {
      el.removeEventListener("mouseenter", onMouseEnter);
      el.removeEventListener("mouseleave", onMouseLeave);
      breathe.kill();
    };
  }, { scope: ref });

  return (
    <button
      ref={ref}
      className={className}
      style={{ ...style }}
      {...props}
    >
      {children}
    </button>
  );
}
