import { useEffect, useMemo, useState } from "react";
import {
  FluentProvider,
  createDarkTheme,
  createLightTheme,
  BrandVariants,
  Theme,
} from "@fluentui/react-components";
import { Dialog, DialogActions, DialogBody, DialogContent, DialogSurface, DialogTitle, Button } from "@fluentui/react-components";
import { check, Update } from "@tauri-apps/plugin-updater";
import { getSystemAccentColor, getSystemDarkMode, loadSettings, Settings } from "./api/tauri";
import i18n from "./i18n";
import { AppShell } from "./components/AppShell.tsx";

function clamp(value: number) {
  return Math.max(0, Math.min(255, Math.round(value)));
}

function hexToRgb(hex: string) {
  const normalized = hex.replace("#", "").trim();
  if (!/^[0-9a-fA-F]{6}$/.test(normalized)) {
    return { r: 79, g: 107, b: 237 };
  }
  return {
    r: parseInt(normalized.slice(0, 2), 16),
    g: parseInt(normalized.slice(2, 4), 16),
    b: parseInt(normalized.slice(4, 6), 16),
  };
}

function rgbToHex(r: number, g: number, b: number) {
  return `#${clamp(r).toString(16).padStart(2, "0")}${clamp(g).toString(16).padStart(2, "0")}${clamp(b).toString(16).padStart(2, "0")}`.toUpperCase();
}

function mix(base: { r: number; g: number; b: number }, target: { r: number; g: number; b: number }, amount: number) {
  return rgbToHex(
    base.r + (target.r - base.r) * amount,
    base.g + (target.g - base.g) * amount,
    base.b + (target.b - base.b) * amount,
  );
}

function buildBrandVariants(accentColor: string): BrandVariants {
  const accent = hexToRgb(accentColor);
  const black = { r: 0, g: 0, b: 0 };
  const white = { r: 255, g: 255, b: 255 };
  return {
    10: mix(accent, black, 0.92),
    20: mix(accent, black, 0.84),
    30: mix(accent, black, 0.74),
    40: mix(accent, black, 0.62),
    50: mix(accent, black, 0.48),
    60: mix(accent, black, 0.34),
    70: mix(accent, black, 0.18),
    80: mix(accent, black, 0.06),
    90: rgbToHex(accent.r, accent.g, accent.b),
    100: mix(accent, white, 0.12),
    110: mix(accent, white, 0.24),
    120: mix(accent, white, 0.36),
    130: mix(accent, white, 0.48),
    140: mix(accent, white, 0.62),
    150: mix(accent, white, 0.78),
    160: mix(accent, white, 0.9),
  };
}

export default function App() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [systemDark, setSystemDark] = useState(true);
  const [accentColor, setAccentColor] = useState("#4F6BED");
  const [startupUpdate, setStartupUpdate] = useState<Update | null>(null);
  const [installingStartupUpdate, setInstallingStartupUpdate] = useState(false);

  useEffect(() => {
    Promise.all([loadSettings(), getSystemDarkMode(), getSystemAccentColor()]).then(([s, sysDark, accent]) => {
      setSettings(s);
      i18n.changeLanguage(s.language);
      setSystemDark(sysDark);
      setAccentColor(accent);
      if (s.startupUpdateCheck) {
        check().then((update: Update | null) => setStartupUpdate(update)).catch(() => {});
      }
    });
  }, []);

  const isDark = settings?.theme === "dark"
    ? true
    : settings?.theme === "light"
      ? false
      : systemDark;

  useEffect(() => {
    document.documentElement.style.colorScheme = isDark ? "dark" : "light";
  }, [isDark]);

  const brand = useMemo(() => buildBrandVariants(accentColor), [accentColor]);
  const lightTheme: Theme = useMemo(() => createLightTheme(brand), [brand]);
  const darkTheme: Theme = useMemo(() => createDarkTheme(brand), [brand]);
  const theme = isDark ? darkTheme : lightTheme;

  const handleInstallStartupUpdate = async () => {
    if (!startupUpdate) return;
    setInstallingStartupUpdate(true);
    try {
      await startupUpdate.downloadAndInstall();
    } catch {
      setInstallingStartupUpdate(false);
    }
  };

  return (
    <FluentProvider className={`app-root app-theme--${isDark ? "dark" : "light"}`} theme={theme} style={{ height: "100vh", display: "flex", flexDirection: "column", background: "transparent" }}>
      <AppShell
        settings={settings}
        onSettingsChange={(s: Settings) => {
          setSettings(s);
          Promise.all([getSystemDarkMode(), getSystemAccentColor()]).then(([dark, accent]) => {
            setSystemDark(dark);
            setAccentColor(accent);
          });
          i18n.changeLanguage(s.language);
        }}
        isDark={isDark}
      />
      <Dialog open={!!startupUpdate} onOpenChange={(_, data) => !data.open && setStartupUpdate(null)}>
        <DialogSurface>
          <DialogBody>
            <DialogTitle>{i18n.t("settings_update_available")}</DialogTitle>
            <DialogContent>
              {startupUpdate
                ? i18n.t("settings_startup_update_prompt", { version: startupUpdate.version })
                : ""}
            </DialogContent>
            <DialogActions>
              <Button appearance="secondary" onClick={() => setStartupUpdate(null)}>
                {i18n.t("cancel")}
              </Button>
              <Button appearance="primary" onClick={handleInstallStartupUpdate} disabled={installingStartupUpdate}>
                {installingStartupUpdate ? i18n.t("settings_update_installing") : i18n.t("settings_update_install_now")}
              </Button>
            </DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>
    </FluentProvider>
  );
}
