import React, { useState } from "react";
import {
  Tooltip,
} from "@fluentui/react-components";
import {
  AppsRegular,
  EditRegular,
  SettingsRegular,
  InfoRegular,
  NavigationRegular,
} from "@fluentui/react-icons";
import { useTranslation } from "react-i18next";

export type PageId = "mods" | "editor" | "settings" | "about";

interface NavItem {
  id: PageId;
  labelKey: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  { id: "mods", labelKey: "nav_mods", icon: <AppsRegular fontSize={20} /> },
  { id: "editor", labelKey: "nav_editor", icon: <EditRegular fontSize={20} /> },
  { id: "settings", labelKey: "nav_settings", icon: <SettingsRegular fontSize={20} /> },
  { id: "about", labelKey: "nav_about", icon: <InfoRegular fontSize={20} /> },
];

interface NavPaneProps {
  activePage: PageId;
  onNavigate: (page: PageId) => void;
  isDark: boolean;
}

export function NavPane({ activePage, onNavigate, isDark }: NavPaneProps) {
  const { t } = useTranslation();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className={`nav-pane nav-pane--${collapsed ? "collapsed" : "expanded"} nav-pane--${isDark ? "dark" : "light"}`}>
      <button
        title={collapsed ? t("nav_expand") : t("nav_collapse")}
        onClick={() => setCollapsed(!collapsed)}
        className="nav-pane__toggle"
      >
        <NavigationRegular fontSize={18} />
        {!collapsed && (
          <span className="nav-pane__toggle-label">{t("nav_menu")}</span>
        )}
      </button>

      <div className="nav-pane__items">
        {NAV_ITEMS.map((item) => {
          const isActive = activePage === item.id;
          return (
            <Tooltip
              key={item.id}
              content={t(item.labelKey)}
              relationship="label"
              positioning="after"
              visible={collapsed ? undefined : false}
            >
              <button
                title={t(item.labelKey)}
                onClick={() => onNavigate(item.id)}
                className={`nav-pane__item${isActive ? " nav-pane__item--active" : ""}`}
              >
                {item.icon}
                {!collapsed && (
                  <span className="nav-pane__item-label">{t(item.labelKey)}</span>
                )}
              </button>
            </Tooltip>
          );
        })}
      </div>
    </div>
  );
}
