import type { Block } from "../../types/game";
import { COUNTRY_COLORS, OWNER_NAMES } from "../../theme";

interface BlockInfoProps {
  block: Block | null;
  selectedCountry: string | null;
}

export default function BlockInfo({ block, selectedCountry }: BlockInfoProps) {
  if (!block) {
    return (
      <div className="p-4 text-center font-body text-sm" style={{ color: "#6b7280" }}>
        点击地图区块查看详情
      </div>
    );
  }

  const ownerName = OWNER_NAMES[block.owner] || block.owner;

  return (
    <div className="p-3 space-y-2 font-body">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-title font-bold">{block.name}</h3>
        <span
          className="px-2 py-0.5 rounded text-xs text-white"
          style={{ backgroundColor: COUNTRY_COLORS[block.owner] || "#999" }}
        >
          {ownerName}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="p-2 rounded" style={{ backgroundColor: "rgba(0,0,0,0.15)" }}>
          <div style={{ color: "#6b7280" }}>驻军</div>
          <div className="font-bold text-sm">{block.garrison}</div>
        </div>
        <div className="p-2 rounded" style={{ backgroundColor: "rgba(0,0,0,0.15)" }}>
          <div style={{ color: "#6b7280" }}>人力</div>
          <div className="font-bold text-sm">{block.manpower_pool}/{block.base_manpower}</div>
        </div>
        <div className="p-2 rounded" style={{ backgroundColor: "rgba(0,0,0,0.15)" }}>
          <div style={{ color: "#6b7280" }}>秩序</div>
          <div className="font-bold text-sm" style={{ color: block.order >= 60 ? "#16a34a" : block.order >= 30 ? "#ca8a04" : "#dc2626" }}>
            {block.order}
          </div>
        </div>
        <div className="p-2 rounded" style={{ backgroundColor: "rgba(0,0,0,0.15)" }}>
          <div style={{ color: "#6b7280" }}>士气</div>
          <div className="font-bold text-sm" style={{ color: block.morale >= 60 ? "#16a34a" : block.morale >= 30 ? "#ca8a04" : "#dc2626" }}>
            {block.morale}
          </div>
        </div>
      </div>

      <div className="flex gap-1 text-xs flex-wrap">
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

      <div className="text-xs" style={{ color: "#6b7280" }}>
        发展: {block.develop_count}/3 {block.specialization && `| ${block.specialization}`}
      </div>
    </div>
  );
}
