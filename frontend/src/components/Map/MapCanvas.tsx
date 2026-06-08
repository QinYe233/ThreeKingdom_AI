/**
 * 地图Canvas组件 - 基于Canvas2D绘制三国地图
 * 支持缩放、拖拽、区块选中、动画效果（征兵/进攻/征税/发展）
 * 使用Path2D缓存区块路径，实现高效点击检测和渲染
 */
import { useEffect, useRef, useState, useCallback, useMemo, memo } from "react";
import { MAP_COLORS, COUNTRY_COLOR_SETS } from "../../theme";

interface MapAnimation {
  type: string;
  block?: string;
  from?: string;
  to?: string;
  value?: number;
  country?: string;
  success?: boolean;
  timestamp: number;
}

interface MapCanvasProps {
  geojson: any;
  blocksData: Record<string, any>;
  countriesData?: Record<string, any>;
  selectedBlock: string | null;
  onSelectBlock: (name: string) => void;
  animations?: MapAnimation[];
}

interface BlockPathCache {
  name: string;
  path: Path2D;
  centerLonLat: { lon: number; lat: number };
  bounds: { minLon: number; maxLon: number; minLat: number; maxLat: number };
}

const ANIMATION_DURATION = 5000;
// 地理坐标范围（中国三国时期地图）
const MIN_LON = 97, MAX_LON = 135, MIN_LAT = 15, MAX_LAT = 45;
const LON_RANGE = MAX_LON - MIN_LON;
const LAT_RANGE = MAX_LAT - MIN_LAT;
const MIN_SCALE = 0.8;
const MAX_SCALE = 3.0;
const ZOOM_FACTOR = 1.05;
const AGED_SPOTS_SEED = 42;

/** 伪随机数生成器（用于古卷纸斑点纹理） */
function seededRandom(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

/** 绘制圆角矩形路径 */
function drawRoundRect(ctx: CanvasRenderingContext2D, x: number, y: number, width: number, height: number, radius: number) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
}

const MapCanvas = memo(function MapCanvas({
  geojson,
  blocksData,
  countriesData,
  selectedBlock,
  onSelectBlock,
  animations = []
}: MapCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [canvasSize, setCanvasSize] = useState({ width: 800, height: 600 });
  const isDraggingRef = useRef(false);

  const offsetRef = useRef({ x: 0, y: 0 });
  const scaleRef = useRef(1);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const lastOffsetRef = useRef({ x: 0, y: 0 });
  const blockPathCacheRef = useRef<BlockPathCache[]>([]);
  const blockPathMapRef = useRef<Map<string, BlockPathCache>>(new Map());
  const lastDrawnOffsetRef = useRef({ x: 0, y: 0 });
  const lastDrawnScaleRef = useRef(1);
  const animationFrameRef = useRef<number | null>(null);
  const pulseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastCanvasSizeRef = useRef({ width: 0, height: 0 });
  const drawMapRef = useRef<(forceRedraw?: boolean) => void>(() => {});

  useEffect(() => {
    const handleResize = () => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      setCanvasSize({ width: rect.width, height: rect.height });
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // 计算视图变换参数（保持地图宽高比，居中显示）
  const getViewTransform = useCallback(() => {
    const aspectRatio = LON_RANGE / LAT_RANGE;
    const canvasAspect = canvasSize.width / canvasSize.height;
    
    let drawWidth: number, drawHeight: number, offsetX: number, offsetY: number;
    
    if (canvasAspect > aspectRatio) {
      drawHeight = canvasSize.height * scaleRef.current;
      drawWidth = drawHeight * aspectRatio;
      offsetX = (canvasSize.width - drawWidth) / 2 + offsetRef.current.x;
      offsetY = offsetRef.current.y;
    } else {
      drawWidth = canvasSize.width * scaleRef.current;
      drawHeight = drawWidth / aspectRatio;
      offsetX = offsetRef.current.x;
      offsetY = (canvasSize.height - drawHeight) / 2 + offsetRef.current.y;
    }
    
    return { drawWidth, drawHeight, offsetX, offsetY };
  }, [canvasSize]);

  /** 经纬度转Canvas像素坐标 */
  const lonLatToCanvas = useCallback((lon: number, lat: number) => {
    const { drawWidth, drawHeight, offsetX, offsetY } = getViewTransform();
    const x = ((lon - MIN_LON) / LON_RANGE) * drawWidth + offsetX;
    const y = ((MAX_LAT - lat) / LAT_RANGE) * drawHeight + offsetY;
    return { x, y };
  }, [getViewTransform]);

  /** Canvas像素坐标转经纬度 */
  const canvasToLonLat = useCallback((x: number, y: number) => {
    const { drawWidth, drawHeight, offsetX, offsetY } = getViewTransform();
    const lon = ((x - offsetX) / drawWidth) * LON_RANGE + MIN_LON;
    const lat = MAX_LAT - ((y - offsetY) / drawHeight) * LAT_RANGE;
    return { lon, lat };
  }, [getViewTransform]);

  // GeoJSON加载后，预计算Path2D缓存和区块边界（避免每帧重复计算）
  useEffect(() => {
    if (!geojson || !geojson.features) return;

    const cache: BlockPathCache[] = [];
    const map = new Map<string, BlockPathCache>();
    
    for (const feature of geojson.features) {
      const name = feature.properties?.label || "";
      if (!name) continue;
      
      const coords = feature.geometry?.coordinates;
      if (!coords) continue;

      let centerLon = 0, centerLat = 0, pointCount = 0;
      let minLon = Infinity, maxLon = -Infinity, minLat = Infinity, maxLat = -Infinity;
      
      const countPoints = (c: any) => {
        if (typeof c[0] === "number") {
          centerLon += c[0];
          centerLat += c[1];
          pointCount++;
          minLon = Math.min(minLon, c[0]);
          maxLon = Math.max(maxLon, c[0]);
          minLat = Math.min(minLat, c[1]);
          maxLat = Math.max(maxLat, c[1]);
        } else {
          c.forEach(countPoints);
        }
      };
      
      for (const ring of coords) {
        countPoints(ring);
      }

      if (pointCount > 0) {
        const path = new Path2D();
        let firstRing = true;
        
        const buildPath = (c: any) => {
          if (typeof c[0] === "number") {
            if (firstRing) {
              path.moveTo(c[0], c[1]);
              firstRing = false;
            } else {
              path.lineTo(c[0], c[1]);
            }
          } else {
            c.forEach(buildPath);
          }
        };
        
        for (const ring of coords) {
          if (!firstRing) path.closePath();
          firstRing = false;
          buildPath(ring);
        }
        path.closePath();
        
        const entry: BlockPathCache = {
          name,
          path,
          centerLonLat: { lon: centerLon / pointCount, lat: centerLat / pointCount },
          bounds: { minLon, maxLon, minLat, maxLat },
        };
        cache.push(entry);
        map.set(name, entry);
      }
    }
    
    blockPathCacheRef.current = cache;
    blockPathMapRef.current = map;
  }, [geojson]);

  // 首都名称 → 势力名称映射
  const capitals = useMemo(() => {
    const map = new Map<string, string>();
    if (countriesData) {
      Object.entries(countriesData).forEach(([countryName, country]: [string, any]) => {
        if (country.capital) map.set(country.capital, countryName);
      });
    }
    return map;
  }, [countriesData]);

  // 势力名称 → 首都名称映射
  const countryToCapital = useMemo(() => {
    const map = new Map<string, string>();
    if (countriesData) {
      Object.entries(countriesData).forEach(([countryName, country]: [string, any]) => {
        if (country.capital) map.set(countryName, country.capital);
      });
    }
    return map;
  }, [countriesData]);

  /** 核心绘制函数 - 绘制地图底图、区块填充/描边、选中高亮、首都星标 */
  const drawMap = useCallback((forceRedraw: boolean = false) => {
    const canvas = canvasRef.current;
    if (!canvas || !geojson || !geojson.features) return;
    
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // 跳过无变化的帧（优化性能）
    const offsetChanged = 
      Math.abs(offsetRef.current.x - lastDrawnOffsetRef.current.x) > 0.5 ||
      Math.abs(offsetRef.current.y - lastDrawnOffsetRef.current.y) > 0.5;
    const scaleChanged = Math.abs(scaleRef.current - lastDrawnScaleRef.current) > 0.01;
    
    if (!forceRedraw && !offsetChanged && !scaleChanged && !selectedBlock) {
      return;
    }
    
    lastDrawnOffsetRef.current = { ...offsetRef.current };
    lastDrawnScaleRef.current = scaleRef.current;

    const dpr = window.devicePixelRatio || 1;
    const sizeChanged = 
      lastCanvasSizeRef.current.width !== canvasSize.width ||
      lastCanvasSizeRef.current.height !== canvasSize.height;
    
    if (sizeChanged) {
      canvas.width = canvasSize.width * dpr;
      canvas.height = canvasSize.height * dpr;
      lastCanvasSizeRef.current = { width: canvasSize.width, height: canvasSize.height };
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    ctx.fillStyle = MAP_COLORS.base;
    ctx.fillRect(0, 0, canvasSize.width, canvasSize.height);

    const rng = seededRandom(AGED_SPOTS_SEED);
    for (let i = 0; i < 30; i++) {
      ctx.fillStyle = MAP_COLORS.agedSpots;
      ctx.beginPath();
      ctx.arc(rng() * canvasSize.width, rng() * canvasSize.height, rng() * 3 + 0.5, 0, Math.PI * 2);
      ctx.fill();
    }

    if (blockPathCacheRef.current.length === 0) return;

    const { drawWidth, drawHeight, offsetX, offsetY } = getViewTransform();
    const scaleX = drawWidth / LON_RANGE;
    const scaleY = drawHeight / LAT_RANGE;
    const invScale = 1 / Math.min(scaleX, scaleY);
    
    const pulsePhase = (Date.now() % 1500) / 1500;
    const pulseAlpha = 0.3 + Math.sin(pulsePhase * Math.PI * 2) * 0.2;
    const starSize = 8 * scaleRef.current;
    
    const selectedBlockCache = selectedBlock ? blockPathMapRef.current.get(selectedBlock) : null;

    for (const blockCache of blockPathCacheRef.current) {
      const owner = blocksData[blockCache.name]?.owner || "neutral";
      const isSelected = selectedBlock === blockCache.name;
      const isCapital = capitals.has(blockCache.name);
      
      ctx.save();
      ctx.translate(offsetX, offsetY);
      ctx.scale(scaleX, -scaleY);
      ctx.translate(-MIN_LON, -MAX_LAT);
      
      const colorSet = COUNTRY_COLOR_SETS[owner] || COUNTRY_COLOR_SETS.neutral;
      
      ctx.fillStyle = colorSet.fill + (isSelected ? "ff" : "cc");
      ctx.fill(blockCache.path);
      
      if (isSelected) {
        ctx.strokeStyle = "#FFD700";
        ctx.lineWidth = 2.5 * invScale;
        ctx.shadowColor = "#FFD700";
        ctx.shadowBlur = 8 * invScale;
        ctx.stroke(blockCache.path);
        
        ctx.strokeStyle = `rgba(255, 215, 0, ${pulseAlpha})`;
        ctx.lineWidth = 4 * invScale;
        ctx.shadowBlur = 12 * invScale;
        ctx.stroke(blockCache.path);
        ctx.shadowBlur = 0;
      } else {
        ctx.strokeStyle = colorSet.stroke;
        ctx.lineWidth = 0.8 * invScale;
        ctx.stroke(blockCache.path);
      }
      
      ctx.restore();

      if (isCapital) {
        const center = lonLatToCanvas(blockCache.centerLonLat.lon, blockCache.centerLonLat.lat);

        ctx.save();
        ctx.beginPath();
        ctx.translate(center.x, center.y);
        for (let i = 0; i < 10; i++) {
          const radius = i % 2 === 0 ? starSize : starSize * 0.4;
          const angle = (Math.PI / 5) * i - Math.PI / 2;
          const x = Math.cos(angle) * radius;
          const y = Math.sin(angle) * radius;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.fillStyle = colorSet.star;
        ctx.shadowColor = colorSet.star;
        ctx.shadowBlur = 4;
        ctx.fill();
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 0.5;
        ctx.shadowBlur = 0;
        ctx.stroke();
        ctx.restore();
      }
    }

    if (selectedBlockCache) {
      const center = lonLatToCanvas(selectedBlockCache.centerLonLat.lon, selectedBlockCache.centerLonLat.lat);
      
      ctx.save();
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      
      const label = selectedBlockCache.name;
      ctx.font = "bold 14px 'Ma Shan Zheng', 'SimSun', serif";
      const textWidth = ctx.measureText(label).width;
      const padding = 8;
      const labelHeight = 22;
      
      const labelX = center.x - textWidth / 2 - padding;
      const labelY = center.y - labelHeight / 2;
      
      ctx.fillStyle = "rgba(61, 43, 31, 0.9)";
      drawRoundRect(ctx, labelX, labelY, textWidth + padding * 2, labelHeight, 4);
      ctx.fill();
      
      ctx.strokeStyle = "#FFD700";
      ctx.lineWidth = 2;
      ctx.stroke();
      
      ctx.fillStyle = "#FFD700";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(label, center.x, center.y);
      
      ctx.restore();
    }
  }, [geojson, blocksData, selectedBlock, canvasSize, lonLatToCanvas, capitals, getViewTransform]);

  drawMapRef.current = drawMap;

  /** 绘制行动动画（征兵飘字、进攻箭头、征税/发展提示） */
  const drawAnimations = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const now = Date.now();
    let hasActiveAnimations = false;
    const blockMap = blockPathMapRef.current;

    for (const anim of animations) {
      const elapsed = now - anim.timestamp;
      if (elapsed > ANIMATION_DURATION) continue;
      
      hasActiveAnimations = true;
      const progress = elapsed / ANIMATION_DURATION;

      if (anim.type === "recruit" && anim.block) {
        const block = blockMap.get(anim.block);
        if (block) {
          const center = lonLatToCanvas(block.centerLonLat.lon, block.centerLonLat.lat);
          const alpha = progress < 0.7 ? 1 : 1 - (progress - 0.7) / 0.3;
          const yOffset = progress * 40;
          ctx.save();
          ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
          ctx.globalAlpha = Math.max(0, alpha);
          ctx.font = "bold 14px sans-serif";
          ctx.textAlign = "center";
          ctx.fillStyle = "#34d399";
          ctx.shadowColor = "rgba(0,0,0,0.8)";
          ctx.shadowBlur = 4;
          ctx.fillText(`+${anim.value}兵`, center.x, center.y - yOffset);
          ctx.restore();
        }
      } else if (anim.type === "attack" && anim.from && anim.to) {
        const fromBlock = blockMap.get(anim.from);
        const toBlock = blockMap.get(anim.to);
        if (fromBlock && toBlock) {
          const from = lonLatToCanvas(fromBlock.centerLonLat.lon, fromBlock.centerLonLat.lat);
          const to = lonLatToCanvas(toBlock.centerLonLat.lon, toBlock.centerLonLat.lat);
          const alpha = progress < 0.2 ? progress / 0.2 : progress > 0.7 ? 1 - (progress - 0.7) / 0.3 : 1;
          
          ctx.save();
          ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
          ctx.globalAlpha = Math.max(0, alpha);
          ctx.strokeStyle = anim.success ? "#f59e0b" : "#ef4444";
          ctx.lineWidth = 2.5;
          ctx.setLineDash([6, 4]);
          ctx.lineDashOffset = -elapsed * 0.03;
          ctx.beginPath();
          ctx.moveTo(from.x, from.y);
          ctx.lineTo(to.x, to.y);
          ctx.stroke();
          ctx.restore();

          const midX = (from.x + to.x) / 2;
          const midY = (from.y + to.y) / 2;
          const angle = Math.atan2(to.y - from.y, to.x - from.x);
          const arrowLen = 12;
          ctx.save();
          ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
          ctx.globalAlpha = Math.max(0, alpha);
          ctx.translate(midX, midY);
          ctx.rotate(angle);
          ctx.beginPath();
          ctx.moveTo(arrowLen, 0);
          ctx.lineTo(-arrowLen * 0.5, -arrowLen * 0.5);
          ctx.lineTo(-arrowLen * 0.5, arrowLen * 0.5);
          ctx.closePath();
          ctx.fillStyle = anim.success ? "#f59e0b" : "#ef4444";
          ctx.fill();
          ctx.restore();

          if (progress > 0.3) {
            const textAlpha = progress < 0.7 ? 1 : 1 - (progress - 0.7) / 0.3;
            ctx.save();
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            ctx.globalAlpha = Math.max(0, textAlpha);
            ctx.font = "bold 13px sans-serif";
            ctx.textAlign = "center";
            ctx.fillStyle = anim.success ? "#f59e0b" : "#ef4444";
            ctx.shadowColor = "rgba(0,0,0,0.8)";
            ctx.shadowBlur = 4;
            ctx.fillText(anim.success ? "⚔ 攻占!" : "✗ 受挫", to.x, to.y - 18);
            ctx.restore();
          }
        }
      } else if (anim.type === "tax" && anim.country) {
        const capitalName = countryToCapital.get(anim.country);
        if (capitalName) {
          const block = blockMap.get(capitalName);
          if (block) {
            const center = lonLatToCanvas(block.centerLonLat.lon, block.centerLonLat.lat);
            const alpha = progress < 0.7 ? 1 : 1 - (progress - 0.7) / 0.3;
            const yOffset = progress * 50;
            ctx.save();
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            ctx.globalAlpha = Math.max(0, alpha);
            ctx.font = "bold 14px sans-serif";
            ctx.textAlign = "center";
            ctx.fillStyle = "#fbbf24";
            ctx.shadowColor = "rgba(0,0,0,0.8)";
            ctx.shadowBlur = 4;
            ctx.fillText(`+${anim.value}金`, center.x + 50, center.y - yOffset);
            ctx.restore();
          }
        }
      } else if (anim.type === "develop" && anim.block) {
        const block = blockMap.get(anim.block);
        if (block) {
          const center = lonLatToCanvas(block.centerLonLat.lon, block.centerLonLat.lat);
          const alpha = progress < 0.7 ? 1 : 1 - (progress - 0.7) / 0.3;
          const yOffset = progress * 35;
          ctx.save();
          ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
          ctx.globalAlpha = Math.max(0, alpha);
          ctx.font = "bold 13px sans-serif";
          ctx.textAlign = "center";
          ctx.fillStyle = "#60a5fa";
          ctx.shadowColor = "rgba(0,0,0,0.8)";
          ctx.shadowBlur = 4;
          ctx.fillText(`人力+${anim.value}`, center.x, center.y - yOffset);
          ctx.restore();
        }
      }
    }

    return hasActiveAnimations;
  }, [animations, lonLatToCanvas, countryToCapital]);

  // 渲染循环：有动画时用requestAnimationFrame，选中区块时用setTimeout实现脉冲
  useEffect(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    if (pulseTimerRef.current) {
      clearTimeout(pulseTimerRef.current);
      pulseTimerRef.current = null;
    }

    const render = () => {
      drawMap(true);
      const hasActiveAnimations = drawAnimations();

      if (hasActiveAnimations) {
        animationFrameRef.current = requestAnimationFrame(render);
      } else if (selectedBlock) {
        pulseTimerRef.current = setTimeout(render, 66);
      }
    };

    render();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (pulseTimerRef.current) {
        clearTimeout(pulseTimerRef.current);
      }
    };
  }, [drawMap, drawAnimations, animations, selectedBlock]);

  useEffect(() => {
    drawMap(true);
  }, [drawMap]);

  /** 通过isPointInPath检测点击位置对应的区块 */
  const findBlockAtPoint = useCallback((x: number, y: number): string | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;

    const { lon, lat } = canvasToLonLat(x, y);

    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);

    for (const blockCache of blockPathCacheRef.current) {
      const { bounds } = blockCache;
      if (
        lon >= bounds.minLon && lon <= bounds.maxLon &&
        lat >= bounds.minLat && lat <= bounds.maxLat
      ) {
        const isInPath = ctx.isPointInPath(blockCache.path, lon, lat);

        if (isInPath) {
          ctx.restore();
          return blockCache.name;
        }
      }
    }
    ctx.restore();
    return null;
  }, [canvasToLonLat]);

  const handleClick = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const found = findBlockAtPoint(x, y);

    if (found) {
      onSelectBlock(found);
    }
  }, [findBlockAtPoint, onSelectBlock]);

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
  }, []);

  // 滚轮缩放 - 以鼠标位置为中心缩放，保持鼠标下地理坐标不变
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      e.stopPropagation();

      if (isDraggingRef.current) return;

      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const { lon, lat } = canvasToLonLat(mouseX, mouseY);

      const delta = e.deltaY > 0 ? 1 / ZOOM_FACTOR : ZOOM_FACTOR;
      const newScale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, scaleRef.current * delta));

      const aspectRatio = LON_RANGE / LAT_RANGE;
      const canvasAspect = canvasSize.width / canvasSize.height;

      let newDrawWidth: number, newDrawHeight: number, newOffsetX: number, newOffsetY: number;

      if (canvasAspect > aspectRatio) {
        newDrawHeight = canvasSize.height * newScale;
        newDrawWidth = newDrawHeight * aspectRatio;
        newOffsetX = mouseX - ((lon - MIN_LON) / LON_RANGE) * newDrawWidth - (canvasSize.width - newDrawWidth) / 2;
        newOffsetY = mouseY - ((MAX_LAT - lat) / LAT_RANGE) * newDrawHeight;
      } else {
        newDrawWidth = canvasSize.width * newScale;
        newDrawHeight = newDrawWidth / aspectRatio;
        newOffsetX = mouseX - ((lon - MIN_LON) / LON_RANGE) * newDrawWidth;
        newOffsetY = mouseY - ((MAX_LAT - lat) / LAT_RANGE) * newDrawHeight - (canvasSize.height - newDrawHeight) / 2;
      }

      scaleRef.current = newScale;
      offsetRef.current = { x: newOffsetX, y: newOffsetY };
      drawMapRef.current(true);
    };

    canvas.addEventListener("wheel", onWheel, { passive: false });
    return () => canvas.removeEventListener("wheel", onWheel);
  }, [canvasSize, canvasToLonLat]);

  // 拖拽状态（仅用于光标样式显示，事件处理用ref避免闭包问题）
  const [isDraggingDisplay, setIsDraggingDisplay] = useState(false);

  // 中键拖拽平移地图
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const onMouseDown = (e: MouseEvent) => {
      if (e.button === 1) {
        e.preventDefault();
        isDraggingRef.current = true;
        setIsDraggingDisplay(true);
        dragStartRef.current = { x: e.clientX, y: e.clientY };
        lastOffsetRef.current = { ...offsetRef.current };
      }
    };

    const onMouseMove = (e: MouseEvent) => {
      if (isDraggingRef.current) {
        const dx = e.clientX - dragStartRef.current.x;
        const dy = e.clientY - dragStartRef.current.y;
        offsetRef.current = { x: lastOffsetRef.current.x + dx, y: lastOffsetRef.current.y + dy };
        drawMapRef.current(true);
      }
    };

    const onMouseUp = () => {
      isDraggingRef.current = false;
      setIsDraggingDisplay(false);
    };

    canvas.addEventListener("mousedown", onMouseDown);
    canvas.addEventListener("mousemove", onMouseMove);
    canvas.addEventListener("mouseup", onMouseUp);
    canvas.addEventListener("mouseleave", onMouseUp);

    return () => {
      canvas.removeEventListener("mousedown", onMouseDown);
      canvas.removeEventListener("mousemove", onMouseMove);
      canvas.removeEventListener("mouseup", onMouseUp);
      canvas.removeEventListener("mouseleave", onMouseUp);
    };
  }, []);

  return (
    <div ref={containerRef} className="w-full h-full">
      <canvas
        ref={canvasRef}
        style={{
          width: canvasSize.width,
          height: canvasSize.height,
          cursor: isDraggingDisplay ? "grabbing" : "default",
          display: "block"
        }}
        onClick={handleClick}
        onContextMenu={handleContextMenu}
      />
    </div>
  );
});

export default MapCanvas;
