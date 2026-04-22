import { useEffect, useState } from "react";
import { TitleBar } from "./TitleBar";
import { NavPane, PageId } from "./NavPane";
import { ModManagerPage } from "../pages/ModManagerPage";
import { JsonEditorPage } from "../pages/JsonEditorPage";
import { SettingsPage } from "../pages/SettingsPage";
import { AboutPage } from "../pages/AboutPage";
import { Settings } from "../api/tauri";

interface AppShellProps {
  settings: Settings | null;
  onSettingsChange: (s: Settings) => void;
  isDark: boolean;
}

export function AppShell({ settings, onSettingsChange, isDark }: AppShellProps) {
  const [activePage, setActivePage] = useState<PageId>("mods");
  const [editorFile, setEditorFile] = useState<string | null>(null);
  const [selectedModFilename, setSelectedModFilename] = useState<string | null>(null);
  const [selectionHydrated, setSelectionHydrated] = useState(false);

  useEffect(() => {
    if (!settings?.rememberLastPage) {
      localStorage.removeItem("mms.activePage");
      return;
    }
    const saved = localStorage.getItem("mms.activePage");
    if (saved === "creator") {
      setActivePage("editor");
      return;
    }
    if (saved && ["mods", "editor", "settings", "about"].includes(saved)) {
      setActivePage(saved as PageId);
    }
  }, [settings?.rememberLastPage]);

  useEffect(() => {
    if (settings?.rememberLastPage) {
      localStorage.setItem("mms.activePage", activePage);
    }
  }, [activePage, settings?.rememberLastPage]);

  useEffect(() => {
    if (settings === null) {
      return;
    }
    if (!settings.rememberLastSelectedMod) {
      localStorage.removeItem("mms.mods.selectedFilename");
      setSelectedModFilename(null);
      setSelectionHydrated(true);
      return;
    }
    setSelectedModFilename(localStorage.getItem("mms.mods.selectedFilename"));
    setSelectionHydrated(true);
  }, [settings?.rememberLastSelectedMod]);

  useEffect(() => {
    if (!settings?.rememberLastSelectedMod || !selectionHydrated) {
      return;
    }
    if (selectedModFilename) {
      localStorage.setItem("mms.mods.selectedFilename", selectedModFilename);
    }
  }, [selectedModFilename, settings?.rememberLastSelectedMod, selectionHydrated]);

  const handleOpenInEditor = (filename: string) => {
    setEditorFile(filename);
    setActivePage("editor");
  };

  return (
    <div className="app-shell">
      <TitleBar isDark={isDark} />
      <div className="app-shell__body">
        <NavPane activePage={activePage} onNavigate={setActivePage} isDark={isDark} />
        <main className="app-shell__main">
          <section className={`app-shell__page${activePage === "mods" ? " app-shell__page--active" : ""}`}>
            <ModManagerPage
              onOpenInEditor={handleOpenInEditor}
              settings={settings}
              selectedFilename={selectedModFilename}
              onSelectedFilenameChange={setSelectedModFilename}
              selectionReady={selectionHydrated}
            />
          </section>
          <section className={`app-shell__page${activePage === "editor" ? " app-shell__page--active" : ""}`}>
            <JsonEditorPage
              initialFile={editorFile}
              isDark={isDark}
              onActiveFileChange={setEditorFile}
              modLibraryVersion={settings?.modLibraryDir ?? null}
            />
          </section>
          <section className={`app-shell__page${activePage === "settings" ? " app-shell__page--active" : ""}`}>
            {settings && (
            <SettingsPage settings={settings} onSettingsChange={onSettingsChange} />
            )}
          </section>
          <section className={`app-shell__page${activePage === "about" ? " app-shell__page--active" : ""}`}>
            <AboutPage />
          </section>
        </main>
      </div>
    </div>
  );
}
