import {
  Body1,
  Caption1,
  Button,
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogSurface,
  DialogTitle,
  Link,
  Text,
  Subtitle2,
  Title2,
  Badge,
} from "@fluentui/react-components";
import { useState } from "react";
import { useTranslation } from "react-i18next";

const APP_VERSION = "1.1.0";

export function AboutPage() {
  const { t } = useTranslation();
  const [legalDialog, setLegalDialog] = useState<"terms" | "privacy" | "openSource" | null>(null);

  const legalTexts = {
    terms: t("legal_terms_body"),
    privacy: t("legal_privacy_body"),
    openSource: t("legal_open_source_body"),
  };

  return (
    <div className="page-scroll">
      <div className="page-container">
        <section className="page-hero">
          <div className="page-hero__content">
            <div className="brand-mark brand-mark--brand">M</div>
            <div className="page-hero__text">
              <Caption1 className="muted-text">{t("nav_about")}</Caption1>
              <Title2>Manaka MOD Station</Title2>
              <Body1 className="muted-text">{t("about_desc")}</Body1>
            </div>
          </div>
          <div className="page-hero__meta">
            <Badge appearance="tint" color="brand">{t("about_version")} {APP_VERSION}</Badge>
            <Badge appearance="outline">GNU AGPL v3</Badge>
          </div>
        </section>

        <div className="page-grid">
          <section className="page-card">
            <div className="page-card__header">
              <Subtitle2>{t("about_project_info")}</Subtitle2>
              <Caption1 className="muted-text">{t("about_project_info_desc")}</Caption1>
            </div>
            <div className="info-grid">
              <Caption1 className="info-grid__label">{t("about_author")}</Caption1>
              <Text>FelixChaos</Text>

              <Caption1 className="info-grid__label">{t("about_license")}</Caption1>
              <Text>GNU AGPL v3</Text>

              <Caption1 className="info-grid__label">{t("about_repo")}</Caption1>
              <Link href="https://github.com/felixchaos/Manaka-MOD-Station" target="_blank" rel="noopener noreferrer">
                felixchaos/Manaka-MOD-Station
              </Link>
            </div>
          </section>

          <section className="page-card">
            <div className="page-card__header">
              <Subtitle2>{t("settings_legal")}</Subtitle2>
              <Caption1 className="muted-text">{t("about_legal_desc")}</Caption1>
            </div>
            <div className="chip-row">
              <Button appearance="secondary" onClick={() => setLegalDialog("terms")}>{t("settings_terms")}</Button>
              <Button appearance="secondary" onClick={() => setLegalDialog("privacy")}>{t("settings_privacy")}</Button>
              <Button appearance="secondary" onClick={() => setLegalDialog("openSource")}>{t("settings_open_source")}</Button>
            </div>
          </section>

          <section className="page-card page-card--span-2">
            <div className="page-card__header">
              <Subtitle2>{t("about_stack")}</Subtitle2>
              <Caption1 className="muted-text">{t("about_stack_desc")}</Caption1>
            </div>
            <div className="chip-row">
              {["Tauri v2", "React 19", "Fluent UI v9", "Rust 1.95", "Monaco Editor", "i18next"].map((tech) => (
                <Badge key={tech} appearance="outline" size="small">{tech}</Badge>
              ))}
            </div>
          </section>
        </div>
      </div>

      <Dialog open={legalDialog !== null} onOpenChange={(_, data) => !data.open && setLegalDialog(null)}>
        <DialogSurface>
          <DialogBody>
            <DialogTitle>
              {legalDialog === "terms" && t("settings_terms")}
              {legalDialog === "privacy" && t("settings_privacy")}
              {legalDialog === "openSource" && t("settings_open_source")}
            </DialogTitle>
            <DialogContent>
              <div className="dialog-text">
                {legalDialog ? legalTexts[legalDialog] : ""}
              </div>
            </DialogContent>
            <DialogActions>
              <Button appearance="primary" onClick={() => setLegalDialog(null)}>{t("close")}</Button>
            </DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>
    </div>
  );
}
