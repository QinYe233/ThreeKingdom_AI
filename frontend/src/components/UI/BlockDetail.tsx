import { memo } from "react";
import type { ThemeColors } from "../../theme";
import { COUNTRY_COLORS, OWNER_NAMES, getOrderMoraleColor, SPECIALIZATION_LABELS } from "../../theme";

interface BlockDetailProps {
  block: any;
  blockName: string;
  theme: ThemeColors;
}

const BlockDetail = memo(function BlockDetail({ block, blockName, theme }: BlockDetailProps) {
  if (!block) {
    return (
      <div className="text-xs text-center py-4" style={{ color: theme.textMuted }}>
        点击地图选择区块
      </div>
    );
  }

  const ownerName = OWNER_NAMES[block.owner] || block.owner;
  const orderColor = getOrderMoraleColor(block.order);
  const moraleColor = getOrderMoraleColor(block.morale);

  const specLabel = SPECIALIZATION_LABELS[block.specialization] || null;
  const geoLabel = SPECIALIZATION_LABELS[block.geographic_trait] || null;

  return (
    <div className="p-3 rounded text-sm" style={{ backgroundColor: theme.bg, lineHeight: 1.6 }}>
      <div className="flex items-center justify-between mb-2">
        <div className="font-bold text-base" style={{ color: COUNTRY_COLORS[block.owner] || theme.text }}>
          {blockName}
        </div>
        <span className={`px-2 py-0.5 rounded text-xs ${block.region_type === "core" ? "bg-blue-800/50 text-blue-200" : "bg-orange-800/50 text-orange-200"}`}>
          {block.region_type === "core" ? "核心" : "羁縻"}
        </span>
      </div>

      <div className="flex items-center gap-1 mb-2">
        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COUNTRY_COLORS[block.owner] || "#999" }} />
        <span className="text-xs" style={{ color: theme.text }}>{ownerName}</span>
        {block.recently_conquered && (
          <span className="px-1.5 py-0.5 rounded text-xs bg-yellow-800/50 text-yellow-200 ml-1">新附</span>
        )}
        {!block.supply_connected && (
          <span className="px-1.5 py-0.5 rounded text-xs bg-red-800/50 text-red-200 ml-1">飞地</span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
        <div className="flex justify-between">
          <span style={{ color: theme.textMuted }}>驻军</span>
          <span style={{ color: theme.text }}>{block.garrison}</span>
        </div>
        <div className="flex justify-between">
          <span style={{ color: theme.textMuted }}>人力池</span>
          <span style={{ color: theme.text }}>{block.manpower_pool}/{block.base_manpower}</span>
        </div>
        <div className="flex justify-between">
          <span style={{ color: theme.textMuted }}>秩序</span>
          <span style={{ color: orderColor }}>{block.order}</span>
        </div>
        <div className="flex justify-between">
          <span style={{ color: theme.textMuted }}>士气</span>
          <span style={{ color: moraleColor }}>{block.morale}</span>
        </div>
        <div className="flex justify-between">
          <span style={{ color: theme.textMuted }}>发展</span>
          <span style={{ color: theme.text }}>{block.develop_count}/3</span>
        </div>
        <div className="flex justify-between">
          <span style={{ color: theme.textMuted }}>补给</span>
          <span style={{ color: block.supply_connected ? theme.success : theme.error }}>{block.supply_connected ? "✓ 连通" : "✗ 断绝"}</span>
        </div>
      </div>

      {(specLabel || geoLabel) && (
        <div className="flex gap-1 mt-2 flex-wrap">
          {geoLabel && (
            <span className="px-2 py-0.5 rounded text-xs bg-purple-800/50 text-purple-200">
              地理: {geoLabel}
            </span>
          )}
          {specLabel && (
            <span className="px-2 py-0.5 rounded text-xs bg-teal-800/50 text-teal-200">
              专精: {specLabel}
            </span>
          )}
        </div>
      )}

      {block.neighbors && block.neighbors.length > 0 && (
        <div className="mt-2 pt-2" style={{ borderTop: `1px solid ${theme.border}` }}>
          <div className="text-xs mb-1" style={{ color: theme.textMuted }}>相邻区块</div>
          <div className="flex flex-wrap gap-1">
            {block.neighbors.map((n: string) => (
              <span
                key={n}
                className="px-1.5 py-0.5 rounded text-xs"
                style={{ backgroundColor: theme.border + "40", color: theme.text }}
              >
                {n}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}, (prevProps, nextProps) => {
  return (
    prevProps.block === nextProps.block &&
    prevProps.blockName === nextProps.blockName &&
    prevProps.theme === nextProps.theme
  );
});

export default BlockDetail;
