import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Badge,
  Button,
  Caption1,
  Checkbox,
  Input,
  Spinner,
  Text,
  Title3,
  Tooltip,
} from "@fluentui/react-components";
import {
  ArrowClockwiseRegular,
  CheckmarkSquareRegular,
  ChevronDownRegular,
  ChevronRightRegular,
  DismissSquareRegular,
  DeleteRegular,
  EditRegular,
  SearchRegular,
  TagRegular,
} from "@fluentui/react-icons";
import { useTranslation } from "react-i18next";
import {
  deleteMod,
  ModInfo,
  Settings,
  scanMods,
  setAllModsEnabled,
  setModEnabled,
} from "../api/tauri";

interface ModManagerPageProps {
  onOpenInEditor: (filename: string) => void;
  settings: Settings | null;
  selectedFilename: string | null;
  onSelectedFilenameChange: (filename: string | null) => void;
  selectionReady: boolean;
}

let cachedMods: ModInfo[] | null = null;
let cachedModsPromise: Promise<ModInfo[]> | null = null;
let cachedModsKey = "__default__";

async function loadCachedMods(cacheKey: string, force = false) {
  if (cachedModsKey !== cacheKey) {
    cachedMods = null;
    cachedModsPromise = null;
    cachedModsKey = cacheKey;
  }

  if (!force && cachedMods) {
    return cachedMods;
  }
  if (!force && cachedModsPromise) {
    return cachedModsPromise;
  }

  cachedModsPromise = scanMods()
    .then((mods) => {
      cachedMods = mods;
      cachedModsKey = cacheKey;
      return mods;
    })
    .finally(() => {
      cachedModsPromise = null;
    });

  return cachedModsPromise;
}

function updateCachedMods(cacheKey: string, updater: (mods: ModInfo[]) => ModInfo[]) {
  if (!cachedMods || cachedModsKey !== cacheKey) {
    return;
  }
  cachedMods = updater(cachedMods);
}

export function ModManagerPage({ onOpenInEditor, settings, selectedFilename, onSelectedFilenameChange, selectionReady }: ModManagerPageProps) {
  const { t } = useTranslation();
  const cacheKey = settings?.modLibraryDir?.trim() || "__default__";
  const [mods, setMods] = useState<ModInfo[]>(() => (cachedModsKey === cacheKey ? cachedMods ?? [] : []));
  const [loading, setLoading] = useState(() => !(cachedModsKey === cacheKey && cachedMods !== null));
  const [search, setSearch] = useState("");
  const [quickFilter, setQuickFilter] = useState<"all" | "enabled" | "disabled" | "warp">("all");
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; mod: ModInfo } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const contextMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (settings?.rememberCollapsedGroups) {
      const raw = localStorage.getItem("mms.mods.collapsedGroups");
      if (raw) {
        try {
          setCollapsedGroups(JSON.parse(raw));
        } catch {
          localStorage.removeItem("mms.mods.collapsedGroups");
        }
      }
    } else {
      localStorage.removeItem("mms.mods.collapsedGroups");
    }
  }, [settings?.rememberCollapsedGroups]);

  const reload = useCallback((force = false) => {
    setLoading(true);
    loadCachedMods(cacheKey, force)
      .then(setMods)
      .finally(() => setLoading(false));
  }, [cacheKey]);

  useEffect(() => {
    if (cachedModsKey === cacheKey && cachedMods !== null) {
      setMods(cachedMods);
      setLoading(false);
      return;
    }
    reload(true);
  }, [cacheKey, reload]);

  // Group mods by stage
  const grouped = useMemo(() => {
    const filtered = mods.filter((m) => {
      const q = search.toLowerCase();
      const matchesSearch = !q || m.name.toLowerCase().includes(q) || m.filename.toLowerCase().includes(q);
      const matchesQuickFilter =
        quickFilter === "all"
          ? true
          : quickFilter === "enabled"
            ? m.enabled
            : quickFilter === "disabled"
              ? !m.enabled
              : m.is_warp;
      return matchesSearch && matchesQuickFilter;
    });
    const map = new Map<string, ModInfo[]>();
    for (const m of filtered) {
      const key = m.stage ?? t("mod_unknown_stage");
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(m);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [mods, quickFilter, search, t]);

  useEffect(() => {
    setCollapsedGroups((prev) => {
      const next = { ...prev };
      for (const [stage] of grouped) {
        if (next[stage] === undefined) {
          next[stage] = false;
        }
      }
      return next;
    });
  }, [grouped]);

  useEffect(() => {
    if (settings?.rememberCollapsedGroups) {
      localStorage.setItem("mms.mods.collapsedGroups", JSON.stringify(collapsedGroups));
    }
  }, [collapsedGroups, settings?.rememberCollapsedGroups]);

  const visibleMods = useMemo(() => grouped.flatMap(([, items]) => items), [grouped]);

  useEffect(() => {
    if (settings === null || !selectionReady) {
      return;
    }
    if (visibleMods.length === 0) {
      onSelectedFilenameChange(null);
      return;
    }
    if (selectedFilename && visibleMods.some((mod) => mod.filename === selectedFilename)) {
      return;
    }
    onSelectedFilenameChange(visibleMods[0].filename);
  }, [onSelectedFilenameChange, selectedFilename, selectionReady, settings, visibleMods]);

  const selected = useMemo(
    () => visibleMods.find((mod) => mod.filename === selectedFilename) ?? null,
    [selectedFilename, visibleMods],
  );

  const totalEnabled = mods.filter((m) => m.enabled).length;

  const handleToggle = async (mod: ModInfo, checked: boolean) => {
    await setModEnabled(mod.filename, checked);
    setMods((prev) => prev.map((m) => m.filename === mod.filename ? { ...m, enabled: checked } : m));
    updateCachedMods(cacheKey, (prev) => prev.map((m) => m.filename === mod.filename ? { ...m, enabled: checked } : m));
  };

  const handleSelectAll = async (enabled: boolean) => {
    await setAllModsEnabled(enabled);
    setMods((prev) => prev.map((m) => ({ ...m, enabled })));
    updateCachedMods(cacheKey, (prev) => prev.map((m) => ({ ...m, enabled })));
  };

  const handleDelete = async (mod: ModInfo) => {
    if (settings?.confirmDelete !== false && !confirm(t("mod_delete_confirm"))) return;
    await deleteMod(mod.filename);
    if (selectedFilename === mod.filename) onSelectedFilenameChange(null);
    setMods((prev) => prev.filter((item) => item.filename !== mod.filename));
    updateCachedMods(cacheKey, (prev) => prev.filter((item) => item.filename !== mod.filename));
  };

  const setAllGroupsCollapsed = (collapsed: boolean) => {
    setCollapsedGroups((prev) => {
      const next = { ...prev };
      for (const [stage] of grouped) {
        next[stage] = collapsed;
      }
      return next;
    });
  };

  const handleContextMenu = (e: React.MouseEvent, mod: ModInfo) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, mod });
  };

  // Close context menu on outside click
  useEffect(() => {
    const handler = () => setContextMenu(null);
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, []);

  useEffect(() => {
    if (!contextMenu || !contextMenuRef.current) {
      return;
    }
    contextMenuRef.current.style.top = `${contextMenu.y}px`;
    contextMenuRef.current.style.left = `${contextMenu.x}px`;
  }, [contextMenu]);

  return (
    <div className="workspace-page mod-page" ref={containerRef} onClick={() => setContextMenu(null)}>
      <div className="workspace-page__container">
        <div className="workspace-page__header">
          <div className="mod-header-grid">
            <section className="page-hero page-hero--compact">
              <div className="page-hero__text">
                <Caption1 className="muted-text">{t("nav_mods")}</Caption1>
                <Title3>{t("mod_page_title")}</Title3>
                <Text className="muted-text">{t("mod_page_desc")}</Text>
              </div>
              <div className="page-hero__meta">
                <Badge appearance="tint" color="brand">{t("mod_total")} {mods.length}</Badge>
                <Badge appearance="outline">{t("mod_enabled")} {totalEnabled}</Badge>
                <Badge appearance="outline">{t("mod_stage_groups")} {grouped.length}</Badge>
              </div>
            </section>

            <aside className="page-card mod-tips-card">
              <div className="page-card__header">
                <Text weight="semibold">{t("mod_tips_title")}</Text>
                <Caption1 className="muted-text">{t("mod_tips_desc")}</Caption1>
              </div>
              <div className="mod-tips-card__body">
                <Badge appearance="tint" color="warning">Alt + F9</Badge>
                <Caption1>{t("mod_tips_reload")}</Caption1>
              </div>
            </aside>
          </div>
        </div>

        <div className="workspace-page__body">
          <div className="mod-layout">
          <section className="page-card mod-panel">
            <div className="mod-panel__header mod-panel__header--stack">
              <div>
                <Title3>{t("mod_library_panel")}</Title3>
                <Caption1 className="muted-text">{t("mod_library_panel_desc")}</Caption1>
              </div>
              <Input
                placeholder={t("mod_search_placeholder")}
                value={search}
                onChange={(_, d) => setSearch(d.value)}
                contentBefore={<SearchRegular />}
              />
              <div className="mod-toolbar mod-toolbar--stacked">
                <div className="mod-toolbar__filters">
                  <Button appearance={quickFilter === "all" ? "primary" : "subtle"} size="small" onClick={() => setQuickFilter("all")}>
                    {t("mod_filter_all")}
                  </Button>
                  <Button appearance={quickFilter === "enabled" ? "primary" : "subtle"} size="small" onClick={() => setQuickFilter("enabled")}>
                    {t("mod_filter_enabled")}
                  </Button>
                  <Button appearance={quickFilter === "disabled" ? "primary" : "subtle"} size="small" onClick={() => setQuickFilter("disabled")}>
                    {t("mod_filter_disabled")}
                  </Button>
                  <Button appearance={quickFilter === "warp" ? "primary" : "subtle"} size="small" onClick={() => setQuickFilter("warp")}>
                    {t("mod_filter_warp")}
                  </Button>
                </div>
                <div className="mod-toolbar__actions">
                  <Tooltip content={t("mod_select_all")} relationship="label">
                    <Button icon={<CheckmarkSquareRegular />} appearance="subtle" size="small" onClick={() => handleSelectAll(true)} />
                  </Tooltip>
                  <Tooltip content={t("mod_deselect_all")} relationship="label">
                    <Button icon={<DismissSquareRegular />} appearance="subtle" size="small" onClick={() => handleSelectAll(false)} />
                  </Tooltip>
                  <Tooltip content={t("mod_refresh")} relationship="label">
                    <Button icon={<ArrowClockwiseRegular />} appearance="subtle" size="small" onClick={() => reload(true)} />
                  </Tooltip>
                  <Button appearance="subtle" size="small" onClick={() => setAllGroupsCollapsed(false)}>
                    {t("mod_expand_all")}
                  </Button>
                  <Button appearance="subtle" size="small" onClick={() => setAllGroupsCollapsed(true)}>
                    {t("mod_collapse_all")}
                  </Button>
                </div>
              </div>
            </div>
            <div className="mod-panel__body">
              {loading ? (
                <div className="mod-empty">
                  <Spinner size="small" label={t("loading")} />
                </div>
              ) : grouped.length === 0 ? (
                <div className="mod-empty">
                  <Text>{search ? t("mod_no_results") : t("mod_no_mods")}</Text>
                </div>
              ) : (
                grouped.map(([stage, items]) => (
                  <div className="mod-stage" key={stage}>
                    <button
                      type="button"
                      title={stage}
                      className="mod-stage__header"
                      onClick={() => {
                        setCollapsedGroups((prev) => ({
                          ...prev,
                          [stage]: !prev[stage],
                        }));
                      }}
                    >
                      <div className="mod-stage__title">
                        {collapsedGroups[stage] ? (
                          <ChevronRightRegular fontSize={14} className="mod-stage__chevron" />
                        ) : (
                          <ChevronDownRegular fontSize={14} className="mod-stage__chevron" />
                        )}
                        <TagRegular fontSize={13} className="mod-stage__tag" />
                        <Caption1 className="mod-stage__label">{stage}</Caption1>
                      </div>
                      <Badge size="small" appearance="tint" color="brand">{items.length}</Badge>
                    </button>
                    {!collapsedGroups[stage] && items.map((mod) => {
                      const isSelected = selected?.filename === mod.filename;
                      return (
                        <div
                          key={mod.filename}
                          className={`mod-item${isSelected ? " mod-item--selected" : ""}`}
                          onClick={() => onSelectedFilenameChange(mod.filename)}
                          onContextMenu={(e) => handleContextMenu(e, mod)}
                        >
                          <Checkbox
                            checked={mod.enabled}
                            onChange={(_, d) => handleToggle(mod, d.checked as boolean)}
                            onClick={(e) => e.stopPropagation()}
                            size="medium"
                          />
                          <div className="mod-item__content">
                            <Text className="mod-item__title" weight={isSelected ? "semibold" : "regular"}>
                              {mod.name}
                            </Text>
                            <div className="mod-item__meta">
                              {mod.version && <Caption1 className="muted-text">v{mod.version}</Caption1>}
                              {mod.author && <Caption1 className="muted-text">{mod.author}</Caption1>}
                              {mod.is_warp && (
                                <Badge size="small" appearance="tint" color="warning">Warp</Badge>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ))
              )}
            </div>
          </section>

          <section className="page-card mod-panel">
            <div className="mod-panel__header">
              <div>
                <Title3>{t("mod_details_panel")}</Title3>
                <Caption1 className="muted-text">{t("mod_details_panel_desc")}</Caption1>
              </div>
            </div>
            <div className="mod-panel__body mod-panel__body--detail mod-panel__body--padded">
              {!selected ? (
                <div className="mod-empty">
                  <Text>{t("mod_no_selection")}</Text>
                </div>
              ) : (
                <div className="mod-detail">
                  <div className="mod-detail__top">
                    <div className="mod-detail__identity">
                      <Title3 className="mod-detail__title">{selected.name}</Title3>
                      <Caption1 className="mod-detail__filename">{selected.filename}</Caption1>
                    </div>
                    <div className="mod-detail__actions">
                      <Button icon={<EditRegular />} size="small" appearance="subtle" onClick={() => onOpenInEditor(selected.filename)}>
                        {t("mod_edit")}
                      </Button>
                      <Button icon={<DeleteRegular />} size="small" appearance="subtle" onClick={() => handleDelete(selected)}>
                        {t("mod_delete")}
                      </Button>
                    </div>
                  </div>

                  <div className="mod-detail__surface mod-detail__surface--meta">
                    <div className="mod-detail__grid">
                      <Caption1 className="muted-text">{t("mod_version")}</Caption1>
                      <Text>{selected.version ?? "-"}</Text>
                      <Caption1 className="muted-text">{t("mod_author")}</Caption1>
                      <Text>{selected.author ?? "-"}</Text>
                    </div>
                  </div>

                  {selected.descriptions.length > 0 && (
                    <div className="mod-detail__section">
                      <Caption1 className="mod-detail__section-label">{t("mod_description")}</Caption1>
                      <div className="mod-detail__surface mod-detail__surface--text">{selected.descriptions.join("\n\n")}</div>
                    </div>
                  )}

                  {selected.start_condition && (
                    <div className="mod-detail__section mod-detail__section--grow">
                      <Caption1 className="mod-detail__section-label">{t("mod_start_condition")}</Caption1>
                      <div className="mod-detail__surface mod-detail__surface--grow">
                        <pre className="mod-detail__code">{selected.start_condition}</pre>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>
          </div>

          {contextMenu && (
            <div ref={contextMenuRef} className="mod-context-menu" onClick={(e) => e.stopPropagation()}>
              <button
                title={t("mod_edit")}
                className="mod-context-menu__item"
                onClick={() => {
                  onOpenInEditor(contextMenu.mod.filename);
                  setContextMenu(null);
                }}
              >
                <EditRegular fontSize={16} />
                {t("mod_edit")}
              </button>
              <button
                title={t("mod_delete")}
                className="mod-context-menu__item mod-context-menu__item--danger"
                onClick={() => {
                  handleDelete(contextMenu.mod);
                  setContextMenu(null);
                }}
              >
                <DeleteRegular fontSize={16} />
                {t("mod_delete")}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
