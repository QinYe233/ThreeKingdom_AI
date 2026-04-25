import { memo } from "react";
import type { ThemeColors } from "../../theme";
import { COUNTRY_COLORS, OWNER_NAMES, getOrderMoraleColor } from "../../theme";

interface BlockDetailProps {
  block: any;
  blockName: string;
  theme: ThemeColors;
}

// Optimized with custom comparison to prevent unnecessary re-renders
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

  return (
    <div
      className="p-3 rounded text-sm"
      style={{
        backgroundColor: theme.bg,
        fontFamily: "'Microsoft YaHei', 'PingFang SC', sans-serif",
        lineHeight: 1.6
      }}
    >
      <div className="font-bold text-base mb-2" style={{ color: COUNTRY_COLORS[block.owner] || theme.text }}>
        {blockName}
      </div>
      <div className="grid grid-cols-2 gap-1 text-xs">
        <div style={{ color: theme.text }}>
          <span style={{ color: theme.textMuted }}>归属:</span> {ownerName}
        </div>
        <div style={{ color: theme.text }}>
          <span style={{ color: theme.textMuted }}>兵力:</span> {block.garrison}
        </div>
        <div style={{ color: theme.text }}>
          <span style={{ color: theme.textMuted }}>秩序:</span>{" "}
          <span style={{ color: orderColor }}>{block.order}</span>
        </div>
        <div style={{ color: theme.text }}>
          <span style={{ color: theme.textMuted }}>士气:</span>{" "}
          <span style={{ color: moraleColor }}>{block.morale}</span>
        </div>
        <div style={{ color: theme.text }}>
          <span style={{ color: theme.textMuted }}>人力池:</span> {block.manpower_pool}
        </div>
        <div style={{ color: theme.text }}>
          <span style={{ color: theme.textMuted }}>补给:</span> {block.supply_connected ? "✓" : "✗"}
        </div>
      </div>
      <div className="flex gap-1 text-xs flex-wrap mt-2">
        <span className={`px-2 py-0.5 rounded ${block.region_type === "core" ? "bg-blue-800/50 text-blue-200" : "bg-orange-800/50 text-orange-200"}`}>
          {block.region_type === "core" ? "核心" : "羁縻"}
        </span>
        {!block.supply_connected && (
          <span className="px-2 py-0.5 rounded bg-red-800/50 text-red-200">飞地</span>
        )}
        {block.recently_conquered && (
          <span className="px-2 py-0.5 rounded bg-yellow-800/50 text-yellow-200">新附</span>
        )}
        {block.geographic_trait !== "none" && (
          <span className="px-2 py-0.5 rounded bg-purple-800/50 text-purple-200">
            {block.geographic_trait === "farming" ? "农垦" : block.geographic_trait === "trade" ? "商贸" : "堡垒"}
          </span>
        )}
      </div>
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison to prevent unnecessary re-renders
  return (
    prevProps.block === nextProps.block &&
    prevProps.blockName === nextProps.blockName &&
    prevProps.theme === nextProps.theme
  );
});

export default BlockDetail;
