import { memo } from "react";
import type { ThemeColors } from "../../theme";
import { COUNTRY_COLORS, getActionPointColor } from "../../theme";

interface CountryPanelProps {
  countries: Record<string, any>;
  currentActingCountry: string;
  theme: ThemeColors;
}

const CountryPanel = memo(function CountryPanel({ countries, currentActingCountry, theme }: CountryPanelProps) {
  return (
    <div className="border-b p-3" style={{ borderColor: theme.border }}>
      <div className="text-sm font-subtitle font-bold mb-2" style={{ color: theme.text }}>三国态势</div>
      <div className="grid grid-cols-3 gap-1">
        {["魏", "蜀", "吴"].map((name) => {
          const country = countries[name];
          if (!country) return null;
          const apColors = getActionPointColor(country.action_points);
          return (
            <div
              key={name}
              className="p-2 rounded text-center transition-all duration-200"
              style={{
                backgroundColor: currentActingCountry === name ? COUNTRY_COLORS[name] + "40" : "rgba(0,0,0,0.15)",
                border: currentActingCountry === name ? `2px solid ${COUNTRY_COLORS[name]}` : "none"
              }}
            >
              <div className="font-bold text-sm" style={{ color: COUNTRY_COLORS[name] }}>{name}</div>
              <div className="text-xs mt-1" style={{ color: theme.textMuted }}>
                金:{country.gold}
              </div>
              <div className="text-xs" style={{ color: theme.textMuted }}>
                秩:{country.order} 士:{country.morale}
              </div>
              <div className="text-xs mt-0.5 px-1 py-0.5 rounded" style={{
                backgroundColor: apColors.bg,
                color: apColors.text
              }}>
                AP:{country.action_points}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
});

export default CountryPanel;
