import { useState, useEffect } from "react";
import {
  Badge,
  Body1,
  Button,
  Caption1,
  Input,
  Select,
  Switch,
  Title2,
  Spinner,
  Text,
} from "@fluentui/react-components";
import {
  FolderOpenRegular,
  ArrowSyncRegular,
  OpenRegular,
} from "@fluentui/react-icons";
import { check, Update } from "@tauri-apps/plugin-updater";
import { useTranslation } from "react-i18next";
import {
  getAppDataPath,
  getModLibraryPath,
  openDirectory,
  resetSettings,
  saveSettings,
  Settings,
  syncGameToWorkspace,
} from "../api/tauri";
import { open } from "@tauri-apps/plugin-dialog";

interface SettingsPageProps {
  settings: Settings;
  onSettingsChange: (s: Settings) => void;
}

export function SettingsPage({ settings, onSettingsChange }: SettingsPageProps) {
  const { t } = useTranslation();
  const [local, setLocal] = useState<Settings>({ ...settings });
  const [status, setStatus] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [checkingUpdate, setCheckingUpdate] = useState(false);
  const [installingUpdate, setInstallingUpdate] = useState(false);
  const [modLibPath, setModLibPath] = useState("");
  const [appDataPath, setAppDataPath] = useState("");
  const [availableUpdate, setAvailableUpdate] = useState<Update | null>(null);

  useEffect(() => {
    getModLibraryPath().then(setModLibPath).catch(() => {});
    getAppDataPath().then(setAppDataPath).catch(() => {});
  }, [settings.modLibraryDir]);

  useEffect(() => {
    setLocal({ ...settings });
  }, [settings]);

  const update = (patch: Partial<Settings>) => {
    const next = { ...local, ...patch };
    setLocal(next);
    saveSettings(next).then(() => {
      onSettingsChange(next);
      setStatus(t("settings_saved"));
      setTimeout(() => setStatus(null), 2000);
    });
  };

  const handlePickGameDir = async () => {
    const dir = await open({ directory: true, multiple: false }) as string | null;
    if (dir) update({ gameDir: dir });
  };

  const handlePickModLibraryDir = async () => {
    const dir = await open({ directory: true, multiple: false }) as string | null;
    if (dir) update({ modLibraryDir: dir });
  };

  const handleResetModLibraryDir = () => {
    update({ modLibraryDir: null });
  };

  const handleSync = async () => {
    if (!local.gameDir) return;
    setSyncing(true);
    try {
      const result = await syncGameToWorkspace(local.gameDir);
      setStatus(`同步完成：复制 ${result.copied}，跳过 ${result.skipped}，重命名 ${result.renamed}`);
    } finally {
      setSyncing(false);
    }
  };

  const handleCheckUpdate = async () => {
    setCheckingUpdate(true);
    try {
      const update = await check();
      setAvailableUpdate(update);
      if (update) {
        setStatus(`${t("settings_update_available")}: ${update.version}`);
      } else {
        setStatus(t("settings_up_to_date"));
      }
    } catch {
      setStatus(t("settings_update_check_failed"));
    } finally {
      setCheckingUpdate(false);
    }
  };

  const handleInstallUpdate = async () => {
    if (!availableUpdate) return;
    setInstallingUpdate(true);
    try {
      await availableUpdate.downloadAndInstall();
    } catch {
      setInstallingUpdate(false);
      setStatus(t("settings_update_install_failed"));
    }
  };

  const handleReset = async () => {
    const defaults = await resetSettings();
    setLocal(defaults);
    onSettingsChange(defaults);
    setStatus(t("settings_saved"));
  };

  return (
    <div className="page-scroll settings-page">
      <div className="page-container settings-page__container">
        <section className="page-hero">
          <div className="page-hero__text">
            <Caption1 className="muted-text">{t("nav_settings")}</Caption1>
            <Title2>{t("settings_page_title")}</Title2>
            <Body1 className="muted-text">{t("settings_page_desc")}</Body1>
          </div>
          {status && (
            <Badge appearance="tint" color="success">
              {status}
            </Badge>
          )}
        </section>

        <div className="page-grid settings-grid">
          <section className="page-card settings-card">
            <div className="page-card__header">
              <Text weight="semibold">{t("settings_general")}</Text>
              <Caption1 className="muted-text">{t("settings_general_desc")}</Caption1>
            </div>
            <div className="settings-list">
              <div className="settings-item">
                <div className="settings-item__meta">
                  <Text className="settings-item__title">{t("settings_language")}</Text>
                  <Caption1 className="muted-text">{t("settings_language_desc")}</Caption1>
                </div>
                <div className="settings-item__control">
                <Select value={local.language} onChange={(_, d) => update({ language: d.value })}>
                  <option value="zh-CN">中文（简体）</option>
                  <option value="en-US">English</option>
                </Select>
                </div>
              </div>

              <div className="settings-item">
                <div className="settings-item__meta">
                  <Text className="settings-item__title">{t("settings_theme")}</Text>
                  <Caption1 className="muted-text">{t("settings_theme_desc")}</Caption1>
                </div>
                <div className="settings-item__control">
                  <Select value={local.theme} onChange={(_, d) => update({ theme: d.value })}>
                    <option value="system">{t("settings_theme_system")}</option>
                    <option value="light">{t("settings_theme_light")}</option>
                    <option value="dark">{t("settings_theme_dark")}</option>
                  </Select>
                </div>
              </div>
            </div>
          </section>

          <section className="page-card settings-card">
            <div className="page-card__header">
              <Text weight="semibold">{t("settings_behavior")}</Text>
              <Caption1 className="muted-text">{t("settings_behavior_desc")}</Caption1>
            </div>
            <div className="settings-list">
              <div className="settings-item">
                <div className="settings-item__meta">
                  <Text className="settings-item__title">{t("settings_remember_last_page")}</Text>
                  <Caption1 className="muted-text">{t("settings_remember_last_page_desc")}</Caption1>
                </div>
                <div className="settings-item__control">
                  <Switch checked={local.rememberLastPage} onChange={(_, d) => update({ rememberLastPage: d.checked })} />
                </div>
              </div>

              <div className="settings-item">
                <div className="settings-item__meta">
                  <Text className="settings-item__title">{t("settings_remember_last_selected_mod")}</Text>
                  <Caption1 className="muted-text">{t("settings_remember_last_selected_mod_desc")}</Caption1>
                </div>
                <div className="settings-item__control">
                  <Switch checked={local.rememberLastSelectedMod} onChange={(_, d) => update({ rememberLastSelectedMod: d.checked })} />
                </div>
              </div>

              <div className="settings-item">
                <div className="settings-item__meta">
                  <Text className="settings-item__title">{t("settings_remember_collapsed_groups")}</Text>
                  <Caption1 className="muted-text">{t("settings_remember_collapsed_groups_desc")}</Caption1>
                </div>
                <div className="settings-item__control">
                  <Switch checked={local.rememberCollapsedGroups} onChange={(_, d) => update({ rememberCollapsedGroups: d.checked })} />
                </div>
              </div>

              <div className="settings-item">
                <div className="settings-item__meta">
                  <Text className="settings-item__title">{t("settings_confirm_delete")}</Text>
                  <Caption1 className="muted-text">{t("settings_confirm_delete_desc")}</Caption1>
                </div>
                <div className="settings-item__control">
                  <Switch checked={local.confirmDelete} onChange={(_, d) => update({ confirmDelete: d.checked })} />
                </div>
              </div>
            </div>
          </section>

          <section className="page-card page-card--span-2 settings-card settings-card--wide">
            <div className="page-card__header">
              <Text weight="semibold">{t("settings_storage")}</Text>
              <Caption1 className="muted-text">{t("settings_storage_desc")}</Caption1>
            </div>
            <div className="settings-list">
              <div className="settings-item settings-item--stack">
                <div className="settings-item__meta">
                  <Text className="settings-item__title">{t("settings_game_dir")}</Text>
                  <Caption1 className="muted-text">{t("settings_game_dir_desc")}</Caption1>
                </div>
                <div className="settings-item__control settings-item__control--full">
                  <div className="settings-path-row">
                    <Input
                      className="settings-path-row__input"
                      value={local.gameDir ?? ""}
                      onChange={(_, d) => update({ gameDir: d.value || null })}
                      placeholder="请选择游戏安装目录…"
                    />
                    <div className="settings-actions settings-actions--path">
                      <Button icon={<FolderOpenRegular />} onClick={handlePickGameDir} size="small">
                        {t("settings_game_dir_pick")}
                      </Button>
                      <Button
                        icon={<OpenRegular />}
                        size="small"
                        appearance="subtle"
                        disabled={!local.gameDir}
                        onClick={() => local.gameDir && openDirectory(local.gameDir)}
                      >
                        {t("settings_game_dir_open")}
                      </Button>
                    </div>
                  </div>
                </div>
              </div>

              <div className="settings-item settings-item--stack">
                <div className="settings-item__meta">
                  <Text className="settings-item__title">{t("settings_custom_dir")}</Text>
                  <Caption1 className="muted-text">{t("settings_custom_dir_desc")}</Caption1>
                </div>
                <div className="settings-item__control settings-item__control--full">
                  <div className="settings-path-row">
                    <Input className="settings-path-row__input" value={modLibPath || "..."} readOnly />
                    <div className="settings-actions settings-actions--path">
                      <Button icon={<FolderOpenRegular />} onClick={handlePickModLibraryDir} size="small">
                        {t("settings_custom_dir_pick")}
                      </Button>
                      <Button
                        icon={<OpenRegular />}
                        size="small"
                        appearance="subtle"
                        disabled={!modLibPath}
                        onClick={() => modLibPath && openDirectory(modLibPath)}
                      >
                        {t("settings_custom_dir_open")}
                      </Button>
                      <Button appearance="subtle" size="small" onClick={handleResetModLibraryDir}>
                        {t("settings_custom_dir_reset")}
                      </Button>
                    </div>
                  </div>
                </div>
              </div>

              <div className="settings-item settings-item--stack">
                <div className="settings-item__meta">
                  <Text className="settings-item__title">{t("settings_app_data_dir")}</Text>
                  <Caption1 className="muted-text">{t("settings_app_data_desc")}</Caption1>
                </div>
                <div className="settings-item__control settings-item__control--full">
                  <div className="settings-path-row">
                    <Input className="settings-path-row__input" value={appDataPath || "..."} readOnly />
                    <div className="settings-actions settings-actions--path">
                      <Button
                        icon={<OpenRegular />}
                        size="small"
                        appearance="subtle"
                        disabled={!appDataPath}
                        onClick={() => appDataPath && openDirectory(appDataPath)}
                      >
                        {t("settings_app_data_open")}
                      </Button>
                    </div>
                  </div>
                </div>
              </div>

              <div className="settings-item settings-item--stack">
                <div className="settings-item__meta">
                  <Text className="settings-item__title">{t("settings_sync")}</Text>
                  <Caption1 className="muted-text">{t("settings_sync_desc")}</Caption1>
                </div>
                <div className="settings-item__control settings-item__control--full">
                  <Button
                    icon={syncing ? <Spinner size="tiny" /> : <ArrowSyncRegular />}
                    appearance="primary"
                    disabled={!local.gameDir || syncing}
                    onClick={handleSync}
                  >
                    {t("settings_sync")}
                  </Button>
                </div>
              </div>
            </div>
          </section>

          <section className="page-card page-card--span-2 settings-card settings-card--wide">
            <div className="page-card__header">
              <Text weight="semibold">{t("settings_update")}</Text>
              <Caption1 className="muted-text">{t("settings_update_desc")}</Caption1>
            </div>
            <div className="settings-list">
              <div className="settings-item">
                <div className="settings-item__meta">
                  <Text className="settings-item__title">{t("settings_startup_check")}</Text>
                  <Caption1 className="muted-text">{t("settings_startup_check_desc")}</Caption1>
                </div>
                <div className="settings-item__control">
                <Switch
                  checked={local.startupUpdateCheck}
                  onChange={(_, d) => update({ startupUpdateCheck: d.checked })}
                />
                </div>
              </div>

              <div className="settings-item settings-item--stack">
                <div className="settings-item__meta">
                  <Text className="settings-item__title">{t("settings_check_now")}</Text>
                  <Caption1 className="muted-text">{t("settings_check_now_desc")}</Caption1>
                </div>
                <div className="settings-actions">
                <Button
                  icon={checkingUpdate ? <Spinner size="tiny" /> : undefined}
                  appearance="secondary"
                  disabled={checkingUpdate}
                  onClick={handleCheckUpdate}
                >
                  {t("settings_check_now")}
                </Button>
                {availableUpdate && (
                  <Badge appearance="tint" color="brand">
                    {t("settings_update_available")}: {availableUpdate.version}
                  </Badge>
                )}
              </div>
              </div>

              {availableUpdate && (
                <div className="settings-item settings-item--stack">
                  <div className="settings-item__meta">
                    <Text className="settings-item__title">{t("settings_update_install_now")}</Text>
                    <Caption1 className="muted-text">{t("settings_update_install_desc")}</Caption1>
                  </div>
                  <div className="settings-item__control settings-item__control--full">
                    <Button appearance="primary" onClick={handleInstallUpdate} disabled={installingUpdate}>
                      {installingUpdate ? t("settings_update_installing") : t("settings_update_install_now")}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </section>
        </div>

        <div className="page-actions">
          <Caption1 className="muted-text">{t("settings_legal_in_about")}</Caption1>
          <Button appearance="subtle" onClick={handleReset}>
            {t("settings_reset")}
          </Button>
        </div>
      </div>
    </div>
  );
}
