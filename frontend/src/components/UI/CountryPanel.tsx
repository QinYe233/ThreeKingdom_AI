import { memo } from "react";
import type { ThemeColors } from "../../theme";
import { COUNTRY_COLORS, COUNTRY_ORDER, getActionPointColor, GOAL_LABELS } from "../../theme";

interface CountryPanelProps {
  countries: Record<string, any>;
  currentActingCountry: string;
  theme: ThemeColors;
}

const CountryPanel = memo(function CountryPanel({ countries, currentActingCountry, theme }: CountryPanelProps) {
  const countryList = COUNTRY_ORDER;

  return (
    <div className="border-b p-3" style={{ borderColor: theme.border }}>
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm font-subtitle font-bold" style={{ color: theme.text }}>三国态势</div>
      </div>
      <div className="space-y-2">
        {countryList.map((name) => {
          const country = countries[name];
          if (!country) return null;
          const apColors = getActionPointColor(country.action_points);
          const isActive = currentActingCountry === name;
          const blockCount = country.block_count || 0;

          return (
            <div
              key={name}
              className="p-2 rounded transition-all duration-200"
              style={{
                backgroundColor: isActive ? COUNTRY_COLORS[name] + "20" : theme.bg,
                border: isActive ? `2px solid ${COUNTRY_COLORS[name]}` : `1px solid ${theme.border}`,
              }}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: COUNTRY_COLORS[name] }}
                  />
                  <span className="font-bold text-sm" style={{ color: COUNTRY_COLORS[name] }}>{name}</span>
                  {isActive && (
                    <span className="text-xs px-1.5 py-0.5 rounded animate-pulse" style={{ backgroundColor: COUNTRY_COLORS[name], color: "#fff" }}>
                      行动中
                    </span>
                  )}
                  {country.is_defeated && (
                    <span className="text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: theme.error + "30", color: theme.error }}>
                      已灭亡
                    </span>
                  )}
                </div>
                <span className="text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: apColors.bg, color: apColors.text }}>
                  AP {country.action_points.toFixed(1)}
                </span>
              </div>
              <div className="grid grid-cols-4 gap-1 text-xs" style={{ color: theme.textMuted }}>
                <div title="黄金">
                  💰 {country.gold}
                </div>
                <div title="秩序" style={{ color: country.order < 30 ? theme.error : country.order < 50 ? theme.warning : theme.success }}>
                  🏛 {country.order}
                </div>
                <div title="士气" style={{ color: country.morale < 30 ? theme.error : country.morale < 50 ? theme.warning : theme.success }}>
                  ⚔ {country.morale}
                </div>
                <div title="领地/兵力">
                  🏠 {blockCount}
                </div>
              </div>
              {country.goal && (
                <div className="mt-1 text-xs" style={{ color: theme.textMuted }}>
                  战略：{GOAL_LABELS[country.goal] || country.goal}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
});

export default CountryPanel;
