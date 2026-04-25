import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { THEME_COLORS, MAP_COLORS } from "../../theme";

const COUNTRY_COLORS: Record<string, { fill: string; stroke: string; star: string }> = {
  "魏": { fill: "#4a6fa5", stroke: "#3d5a80", star: "#6b8fc7" },
  "蜀": { fill: "#a54657", stroke: "#8b3a4a", star: "#d46a7a" },
  "吴": { fill: "#4a8f5c", stroke: "#3a7a4a", star: "#6ab87a" },
  neutral: { fill: "#7a7a7a", stroke: "#5a5a5a", star: "#9a9a9a" },
  "公孙度": { fill: "#8b7355", stroke: "#6b5340", star: "#ab9375" },
  "士燮": { fill: "#b8860b", stroke: "#8b6914", star: "#d8a62b" },
  "南中": { fill: "#8b4513", stroke: "#6b3510", star: "#ab6533" },
  "山越": { fill: "#6b8e23", stroke: "#556b2f", star: "#8bae43" },
  "凉州": { fill: "#cd853f", stroke: "#a0522d", star: "#eda55f" },
};

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
const MIN_LON = 97, MAX_LON = 135, MIN_LAT = 15, MAX_LAT = 45;
const LON_RANGE = MAX_LON - MIN_LON;
const LAT_RANGE = MAX_LAT - MIN_LAT;
const MIN_SCALE = 0.8;
const MAX_SCALE = 3.0;
const ZOOM_FACTOR = 1.05;

function seededRandom(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

export default function MapCanvas({
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
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [scale, setScale] = useState(1);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [lastOffset, setLastOffset] = useState({ x: 0, y: 0 });
  const [hoveredBlock, setHoveredBlock] = useState<string | null>(null);
  const [dragMoved, setDragMoved] = useState(false);
  
  const blockPathCacheRef = useRef<BlockPathCache[]>([]);
  const offsetRef = useRef(offset);
  const scaleRef = useRef(scale);
  const lastDrawnOffsetRef = useRef({ x: 0, y: 0 });
  const lastDrawnScaleRef = useRef(1);
  const animationFrameRef = useRef<number | null>(null);
  
  offsetRef.current = offset;
  scaleRef.current = scale;

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

  const lonLatToCanvas = useCallback((lon: number, lat: number) => {
    const { drawWidth, drawHeight, offsetX, offsetY } = getViewTransform();
    const x = ((lon - MIN_LON) / LON_RANGE) * drawWidth + offsetX;
    const y = ((MAX_LAT - lat) / LAT_RANGE) * drawHeight + offsetY;
    return { x, y };
  }, [getViewTransform]);

  const canvasToLonLat = useCallback((x: number, y: number) => {
    const { drawWidth, drawHeight, offsetX, offsetY } = getViewTransform();
    const lon = ((x - offsetX) / drawWidth) * LON_RANGE + MIN_LON;
    const lat = MAX_LAT - ((y - offsetY) / drawHeight) * LAT_RANGE;
    return { lon, lat };
  }, [getViewTransform]);

  useEffect(() => {
    if (!geojson || !geojson.features) return;
    
    const cache: BlockPathCache[] = [];
    
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
        
        cache.push({
          name,
          path,
          centerLonLat: { lon: centerLon / pointCount, lat: centerLat / pointCount },
          bounds: { minLon, maxLon, minLat, maxLat },
        });
      }
    }
    
    blockPathCacheRef.current = cache;
  }, [geojson]);

  const capitals = useMemo(() => {
    const map = new Map<string, string>();
    if (countriesData) {
      Object.entries(countriesData).forEach(([countryName, country]: [string, any]) => {
        if (country.capital) map.set(country.capital, countryName);
      });
    }
    return map;
  }, [countriesData]);

  const drawMap = useCallback((forceRedraw: boolean = false) => {
    const canvas = canvasRef.current;
    if (!canvas || !geojson || !geojson.features) return;
    
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const offsetChanged = 
      Math.abs(offsetRef.current.x - lastDrawnOffsetRef.current.x) > 0.5 ||
      Math.abs(offsetRef.current.y - lastDrawnOffsetRef.current.y) > 0.5;
    const scaleChanged = Math.abs(scaleRef.current - lastDrawnScaleRef.current) > 0.01;
    
    if (!forceRedraw && !offsetChanged && !scaleChanged) {
      return;
    }
    
    lastDrawnOffsetRef.current = { ...offsetRef.current };
    lastDrawnScaleRef.current = scaleRef.current;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = canvasSize.width * dpr;
    canvas.height = canvasSize.height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    ctx.fillStyle = MAP_COLORS.base;
    ctx.fillRect(0, 0, canvasSize.width, canvasSize.height);

    // Subtle parchment aged spots
    const rng = seededRandom(Math.floor(Math.random() * 100000));
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

    for (const blockCache of blockPathCacheRef.current) {
      const owner = blocksData[blockCache.name]?.owner || "neutral";
      const isSelected = selectedBlock === blockCache.name;
      const isHovered = hoveredBlock === blockCache.name;
      
      ctx.save();
      ctx.translate(offsetX, offsetY);
      ctx.scale(scaleX, -scaleY);
      ctx.translate(-MIN_LON, -MAX_LAT);
      
      const colorSet = COUNTRY_COLORS[owner] || COUNTRY_COLORS.neutral;
      
      ctx.fillStyle = colorSet.fill + (isSelected ? "ee" : isHovered ? "dd" : "cc");
      ctx.fill(blockCache.path);
      
      ctx.strokeStyle = isSelected ? MAP_COLORS.selectionBorder : isHovered ? MAP_COLORS.hoverBorder : colorSet.stroke;
      ctx.lineWidth = (isSelected ? 2.5 : isHovered ? 2 : 1) / Math.min(scaleX, scaleY);
      ctx.stroke(blockCache.path);
      
      if (isSelected) {
        ctx.shadowColor = "#FFD700";
        ctx.shadowBlur = 10 / Math.min(scaleX, scaleY);
        ctx.stroke(blockCache.path);
        ctx.shadowBlur = 0;
      }
      
      ctx.restore();
    }

    for (const blockCache of blockPathCacheRef.current) {
      const countryName = capitals.get(blockCache.name);
      if (!countryName) continue;
      
      const center = lonLatToCanvas(blockCache.centerLonLat.lon, blockCache.centerLonLat.lat);
      const owner = blocksData[blockCache.name]?.owner || "neutral";
      const colorSet = COUNTRY_COLORS[owner] || COUNTRY_COLORS.neutral;
      const starSize = Math.max(6, Math.min(12, 8)) * scaleRef.current;

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
  }, [geojson, blocksData, selectedBlock, hoveredBlock, canvasSize, lonLatToCanvas, capitals, getViewTransform, offset, scale]);

  const drawAnimations = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const now = Date.now();
    let hasActiveAnimations = false;

    for (const anim of animations) {
      const elapsed = now - anim.timestamp;
      if (elapsed > ANIMATION_DURATION) continue;
      
      hasActiveAnimations = true;
      const progress = elapsed / ANIMATION_DURATION;

      if (anim.type === "recruit" && anim.block) {
        const block = blockPathCacheRef.current.find(b => b.name === anim.block);
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
        const fromBlock = blockPathCacheRef.current.find(b => b.name === anim.from);
        const toBlock = blockPathCacheRef.current.find(b => b.name === anim.to);
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
        let countryCapital: string | undefined;
        capitals.forEach((countryName, capitalName) => {
          if (countryName === anim.country) {
            countryCapital = capitalName;
          }
        });
        if (countryCapital) {
          const block = blockPathCacheRef.current.find(b => b.name === countryCapital);
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
        const block = blockPathCacheRef.current.find(b => b.name === anim.block);
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
  }, [animations, lonLatToCanvas, capitals]);

  useEffect(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    const render = () => {
      drawMap(true);
      drawAnimations();
      
      if (animations.some(a => Date.now() - a.timestamp < ANIMATION_DURATION)) {
        animationFrameRef.current = requestAnimationFrame(render);
      }
    };

    render();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [drawMap, drawAnimations, animations]);

  useEffect(() => {
    drawMap(true);
  }, [drawMap]);

  const findBlockAtPoint = useCallback((x: number, y: number): string | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;

    const { drawWidth, drawHeight, offsetX, offsetY } = getViewTransform();
    const scaleX = drawWidth / LON_RANGE;
    const scaleY = drawHeight / LAT_RANGE;

    const lon = (x - offsetX) / scaleX + MIN_LON;
    const lat = MAX_LAT - (y - offsetY) / scaleY;

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
  }, [getViewTransform]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 1) {
      e.preventDefault();
      setIsDragging(true);
      setDragMoved(false);
      setDragStart({ x: e.clientX, y: e.clientY });
      setLastOffset({ ...offsetRef.current });
    }
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isDragging) {
      const dx = e.clientX - dragStart.x;
      const dy = e.clientY - dragStart.y;
      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
        setDragMoved(true);
      }
      setOffset({ x: lastOffset.x + dx, y: lastOffset.y + dy });
    } else {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      const found = findBlockAtPoint(x, y);
      setHoveredBlock(found);
    }
  }, [isDragging, dragStart, lastOffset, findBlockAtPoint]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleClick = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) {
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const found = findBlockAtPoint(x, y);

    if (found) {
      onSelectBlock(found);
    }
  }, [findBlockAtPoint, onSelectBlock]);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (isDragging) return;
    
    const canvas = canvasRef.current;
    if (!canvas) return;
    
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
    
    setScale(newScale);
    setOffset({ x: newOffsetX, y: newOffsetY });
  }, [canvasSize, canvasToLonLat, isDragging]);

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
  }, []);

  return (
    <div ref={containerRef} className="w-full h-full">
      <canvas
        ref={canvasRef}
        style={{
          width: canvasSize.width,
          height: canvasSize.height,
          cursor: isDragging ? "grabbing" : "pointer",
          display: "block"
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onClick={handleClick}
        onWheel={handleWheel}
        onContextMenu={handleContextMenu}
      />
    </div>
  );
}
