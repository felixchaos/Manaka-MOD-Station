import { useEffect, useRef, useState } from "react";
import {
  Button,
  Caption1,
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogSurface,
  DialogTitle,
  Field,
  Input,
  Spinner,
  Select,
  tokens,
  Badge,
  Text,
} from "@fluentui/react-components";
import {
  ArrowUpRegular,
  SaveRegular,
  ArrowClockwiseRegular,
  CheckmarkCircleRegular,
  ErrorCircleRegular,
  DocumentAddRegular,
  DocumentRegular,
  DismissRegular,
  FolderOpenRegular,
  FolderRegular,
  InfoRegular,
  SearchRegular,
} from "@fluentui/react-icons";
import Editor from "@monaco-editor/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useTranslation } from "react-i18next";
import {
  formatJson,
  getModLibraryPath,
  listDirectory,
  readTextFileAtPath,
  validateMissionJson,
  ValidationIssue,
  writeTextFileAtPath,
} from "../api/tauri";
import { configureSerikaMissionMonaco } from "../editor/serikaMissionMonaco";
import { basename, dirname, isRootPath, joinPath, parseMissionGuideSections } from "../editor/missionGuide";
import missionGuideMarkdown from "../content/serika-mission-mod-guide.md?raw";
import { open } from "@tauri-apps/plugin-dialog";

interface JsonEditorPageProps {
  initialFile?: string | null;
  isDark?: boolean;
  onActiveFileChange?: (filePath: string | null) => void;
  modLibraryVersion?: string | null;
}

type CreateMode = "blank" | "template";

function normalizeMissionFilename(name: string) {
  const trimmed = name.trim();
  if (!trimmed) {
    return "";
  }
  return trimmed.toLowerCase().endsWith(".json") ? trimmed : `${trimmed}.json`;
}

function buildBlankMissionDocument() {
  return JSON.stringify({}, null, 2);
}

function buildTemplateMissionDocument(filename: string, title: string, author: string, version: string) {
  const fallbackTitle = normalizeMissionFilename(filename).replace(/\.json$/i, "") || "new_mission";
  return JSON.stringify(
    {
      title: title.trim() || fallbackTitle,
      version: version.trim() || "1.0.0",
      author: author.trim() || undefined,
      zones: [
        {
          id: "zone_01",
          stage: "Park",
          areas: [
            { stage: "Park", x: 0, y: 0, z: 0, r: 30 },
          ],
        },
      ],
      subconditions: [
        {
          id: "start",
          condition: {
            type: "reachArea",
            zoneId: "zone_01",
            description: "前往目标区域",
          },
        },
      ],
      checkpoints: [
        {
          id: "cp_01",
          condition: {
            type: "reachArea",
            zoneId: "zone_01",
            description: "完成任务",
          },
        },
      ],
    },
    null,
    2,
  );
}

export function JsonEditorPage({ initialFile, isDark, onActiveFileChange, modLibraryVersion }: JsonEditorPageProps) {
  const { t } = useTranslation();
  const [filename, setFilename] = useState<string | null>(initialFile ?? null);
  const [currentFilePath, setCurrentFilePath] = useState<string | null>(null);
  const [currentDirectory, setCurrentDirectory] = useState<string>("");
  const [explorerEntries, setExplorerEntries] = useState<Array<{ name: string; path: string; isDirectory: boolean }>>([]);
  const [loadingExplorer, setLoadingExplorer] = useState(false);
  const [explorerError, setExplorerError] = useState<string | null>(null);
  const [content, setContent] = useState<string>("");
  const [issues, setIssues] = useState<ValidationIssue[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [helpVisible, setHelpVisible] = useState(false);
  const [guideQuery, setGuideQuery] = useState("");
  const [selectedGuideSectionId, setSelectedGuideSectionId] = useState<string | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createMode, setCreateMode] = useState<CreateMode>("blank");
  const [createFilename, setCreateFilename] = useState("new_mission.json");
  const [createTitle, setCreateTitle] = useState("");
  const [createAuthor, setCreateAuthor] = useState("");
  const [createVersion, setCreateVersion] = useState("1.0.0");
  const [createError, setCreateError] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const editorRef = useRef<any>(null);
  const libraryRootRef = useRef("");

  const guideSections = useState(() => parseMissionGuideSections(missionGuideMarkdown))[0];
  const filteredGuideSections = guideSections.filter((section) =>
    !guideQuery.trim() || section.searchText.includes(guideQuery.trim().toLowerCase()),
  );
  const selectedGuideSection = filteredGuideSections.find((section) => section.id === selectedGuideSectionId)
    ?? filteredGuideSections[0]
    ?? guideSections[0]
    ?? null;
  const hasOpenFile = currentFilePath !== null;
  const handbookHighlights = [
    {
      title: t("editor_help_tip_debug_title"),
      description: t("editor_help_tip_debug_desc"),
    },
    {
      title: t("editor_help_tip_reload_title"),
      description: t("editor_help_tip_reload_desc"),
    },
    {
      title: t("editor_help_tip_json_title"),
      description: t("editor_help_tip_json_desc"),
    },
  ];

  useEffect(() => {
    let cancelled = false;

    getModLibraryPath()
      .then(async (dir) => {
        if (cancelled) {
          return;
        }

        const shouldSyncDirectory = !currentDirectory || currentDirectory === libraryRootRef.current;
        libraryRootRef.current = dir;

        if (shouldSyncDirectory) {
          setCurrentDirectory(dir);
          await loadDirectory(dir);
        }
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [modLibraryVersion]);

  useEffect(() => {
    if (!initialFile) {
      return;
    }

    const baseDirectory = currentDirectory || libraryRootRef.current;
    if (!/[\\/]/.test(initialFile) && !baseDirectory) {
      return;
    }

    const path = /[\\/]/.test(initialFile) ? initialFile : joinPath(baseDirectory, initialFile);
    if (path === currentFilePath) {
      return;
    }

    void loadFile(path, true);
  }, [currentDirectory, currentFilePath, initialFile]);

  useEffect(() => {
    if (!rootRef.current) {
      return;
    }

    const themeVars = {
      "--editor-border": tokens.colorNeutralStroke2,
      "--editor-surface": tokens.colorNeutralBackground2,
      "--editor-bg": isDark ? "#111216" : "#f5f6f8",
      "--editor-toolbar-bg": isDark ? "#181a1f" : "#f8fafc",
      "--editor-tab-bg": isDark ? "#16171b" : "#eef1f5",
      "--editor-tab-active": isDark ? "#1f2128" : "#ffffff",
      "--editor-sidebar-bg": isDark ? "#15171c" : "#f8fafc",
      "--editor-panel-bg": isDark ? "#15171c" : "#f8fafc",
      "--editor-muted": tokens.colorNeutralForeground3,
      "--editor-danger-border": tokens.colorStatusDangerBorder1,
      "--editor-danger-bg": tokens.colorStatusDangerBackground1,
      "--editor-danger": tokens.colorStatusDangerForeground1,
    };

    for (const [key, value] of Object.entries(themeVars)) {
      rootRef.current.style.setProperty(key, value);
    }
  }, [isDark]);

  useEffect(() => {
    if (!selectedGuideSectionId && guideSections[0]) {
      setSelectedGuideSectionId(guideSections[0].id);
    }
  }, [guideSections, selectedGuideSectionId]);

  useEffect(() => {
    if (selectedGuideSection && selectedGuideSection.id !== selectedGuideSectionId) {
      setSelectedGuideSectionId(selectedGuideSection.id);
    }
  }, [selectedGuideSection, selectedGuideSectionId]);

  const loadDirectory = async (dir: string) => {
    setLoadingExplorer(true);
    try {
      const entries = await listDirectory(dir);
      const filtered = entries
        .filter((entry) => entry.name)
        .filter((entry) => entry.isDirectory || entry.name?.toLowerCase().endsWith(".json"))
        .map((entry) => ({
          name: entry.name || "",
          path: entry.path || joinPath(dir, entry.name || ""),
          isDirectory: !!entry.isDirectory,
        }))
        .sort((left, right) => {
          if (left.isDirectory !== right.isDirectory) {
            return left.isDirectory ? -1 : 1;
          }
          return left.name.localeCompare(right.name, "zh-CN");
        });
      setExplorerError(null);
      setExplorerEntries(filtered);
    } catch {
      setExplorerEntries([]);
      setExplorerError(t("editor_explorer_read_failed"));
    } finally {
      setLoadingExplorer(false);
    }
  };

  const confirmDiscardCurrentFile = () => !dirty || confirm(t("editor_discard_confirm"));

  const clearCurrentFile = () => {
    setCurrentFilePath(null);
    setFilename(null);
    setContent("");
    setIssues([]);
    setDirty(false);
    setLoadError(null);
    onActiveFileChange?.(null);
  };

  const resetCreateDialog = () => {
    setCreateMode("blank");
    setCreateFilename("new_mission.json");
    setCreateTitle("");
    setCreateAuthor("");
    setCreateVersion("1.0.0");
    setCreateError(null);
  };

  const loadFile = async (filePath: string, skipDiscardCheck = false) => {
    if (!skipDiscardCheck && currentFilePath !== filePath && !confirmDiscardCurrentFile()) {
      return;
    }

    setLoading(true);
    try {
      const text = await readTextFileAtPath(filePath);
      setCurrentFilePath(filePath);
      setFilename(basename(filePath));
      setContent(text);
      setDirty(false);
      setLoadError(null);
      runValidation(text);
      onActiveFileChange?.(filePath);
    } catch {
      setLoadError(t("editor_open_failed"));
    } finally {
      setLoading(false);
    }
  };

  const runValidation = async (text: string, showBusy = false) => {
    if (showBusy) setValidating(true);
    try {
      const result = await validateMissionJson(text);
      setIssues(result.issues);
    } finally {
      if (showBusy) setValidating(false);
    }
  };

  const handleNewFile = () => {
    if (!confirmDiscardCurrentFile()) {
      return;
    }
    resetCreateDialog();
    setCreateDialogOpen(true);
  };

  const handleConfirmCreate = () => {
    const normalized = normalizeMissionFilename(createFilename);
    if (!normalized) {
      setCreateError(t("editor_create_filename_required"));
      return;
    }

    const baseDirectory = currentDirectory || libraryRootRef.current || "";
    const nextPath = baseDirectory ? joinPath(baseDirectory, normalized) : normalized;
    const nextContent = createMode === "blank"
      ? buildBlankMissionDocument()
      : buildTemplateMissionDocument(normalized, createTitle, createAuthor, createVersion);

    setCurrentFilePath(nextPath);
    setFilename(normalized);
    setContent(nextContent);
    setDirty(true);
    setLoadError(null);
    runValidation(nextContent);
    onActiveFileChange?.(nextPath);
    setCreateDialogOpen(false);
  };

  const handleOpenFile = async () => {
    if (!confirmDiscardCurrentFile()) {
      return;
    }

    const selected = await open({
      filters: [{ name: "JSON", extensions: ["json"] }],
      multiple: false,
    }) as string | null;
    if (!selected) return;
    const nextDir = dirname(selected);
    setCurrentDirectory(nextDir);
    await loadDirectory(nextDir);
    loadFile(selected);
  };

  const handlePickDirectory = async () => {
    if (!confirmDiscardCurrentFile()) {
      return;
    }

    const selected = await open({ directory: true, multiple: false }) as string | null;
    if (!selected) return;
    setCurrentDirectory(selected);
    clearCurrentFile();
    await loadDirectory(selected);
  };

  const handleOpenParentDirectory = async () => {
    if (!currentDirectory || isRootPath(currentDirectory)) return;
    const parent = dirname(currentDirectory);
    setCurrentDirectory(parent);
    await loadDirectory(parent);
  };

  const handleSave = async () => {
    if (!currentFilePath) return;
    setSaving(true);
    try {
      await writeTextFileAtPath(currentFilePath, content);
      setDirty(false);
      await loadDirectory(dirname(currentFilePath));
    } finally {
      setSaving(false);
    }
  };

  const handleFormat = async () => {
    try {
      const formatted = await formatJson(content);
      setContent(formatted);
      setDirty(true);
      runValidation(formatted);
    } catch (e: any) {
      // show error in issues
    }
  };

  const handleValidate = async () => {
    await runValidation(content, true);
  };

  const handleCloseCurrentFile = () => {
    if (!hasOpenFile && !filename) {
      return;
    }
    if (!confirmDiscardCurrentFile()) {
      return;
    }
    clearCurrentFile();
  };

  const handleEditorChange = (val: string | undefined) => {
    if (val !== undefined) {
      setContent(val);
      setDirty(true);
      runValidation(val);
    }
  };

  const issueCountLabel = issues.length === 0 ? t("editor_no_issues") : `${issues.length} ${t("editor_issues")}`;
  const currentFileLabel = filename ?? t("editor_no_file");
  const currentLanguageLabel = t("editor_syntax_mode");

  return (
    <div className="workspace-page editor-page" ref={rootRef}>
      <div className={`workspace-page__container editor-workbench${helpVisible ? "" : " editor-workbench--help-hidden"}`}>
        <div className="editor-workbench__toolbar">
          <div className="editor-workbench__toolbar-left">
            <Button icon={<DocumentRegular />} size="small" appearance="subtle" onClick={handleOpenFile}>
              {t("editor_open")}
            </Button>
            <Button icon={<DocumentAddRegular />} size="small" appearance="subtle" onClick={handleNewFile}>
              {t("editor_new")}
            </Button>
            <Button
              icon={saving ? <Spinner size="tiny" /> : <SaveRegular />}
              size="small"
              appearance={dirty ? "primary" : "subtle"}
              onClick={handleSave}
              disabled={!filename || saving}
            >
              {t("editor_save")}
            </Button>
            <Button icon={<ArrowClockwiseRegular />} size="small" appearance="subtle" onClick={handleFormat} disabled={!content}>
              {t("editor_format")}
            </Button>
            <Button size="small" appearance="subtle" onClick={handleValidate} disabled={!content || validating}>
              {validating ? t("loading") : t("editor_validate")}
            </Button>
          </div>
          <div className="editor-workbench__toolbar-right">
            <Badge appearance="outline">{currentLanguageLabel}</Badge>
            {hasOpenFile ? (
              <Badge
                appearance="tint"
                color={issues.length === 0 ? "success" : "danger"}
                icon={issues.length === 0 ? <CheckmarkCircleRegular /> : <ErrorCircleRegular />}
              >
                {issueCountLabel}
              </Badge>
            ) : (
              <Badge appearance="outline">{t("editor_no_file")}</Badge>
            )}
            {dirty && <Badge appearance="tint" color="warning">{t("editor_unsaved")}</Badge>}
            <Button
              icon={helpVisible ? <DismissRegular /> : <InfoRegular />}
              size="small"
              appearance={helpVisible ? "primary" : "subtle"}
              onClick={() => setHelpVisible((prev) => !prev)}
            >
              {t("editor_help")}
            </Button>
          </div>
        </div>

        <div className="editor-workbench__body">
          <aside className="editor-explorer">
            <div className="editor-explorer__header">
              <div>
                <Text weight="semibold">{t("editor_explorer")}</Text>
                <Caption1 className="muted-text">{t("editor_explorer_desc")}</Caption1>
              </div>
              <div className="settings-actions">
                <Button icon={<FolderOpenRegular />} size="small" appearance="subtle" onClick={handlePickDirectory}>
                  {t("editor_switch_folder")}
                </Button>
                <Button icon={<ArrowUpRegular />} size="small" appearance="subtle" disabled={!currentDirectory || isRootPath(currentDirectory)} onClick={handleOpenParentDirectory}>
                  {t("editor_parent_folder")}
                </Button>
              </div>
            </div>
            <div className="editor-explorer__path">{currentDirectory || t("loading")}</div>
            <div className="editor-explorer__list">
              {loadingExplorer ? (
                <div className="editor-loading">
                  <Spinner size="tiny" label={t("loading")} />
                </div>
              ) : explorerError ? (
                <div className="editor-explorer__empty">{explorerError}</div>
              ) : explorerEntries.length === 0 ? (
                <div className="editor-explorer__empty">{t("editor_explorer_empty")}</div>
              ) : (
                explorerEntries.map((entry) => {
                  const isActive = entry.path === currentFilePath;
                  return (
                    <button
                      key={entry.path}
                      type="button"
                      className={`editor-explorer__item${isActive ? " editor-explorer__item--active" : ""}`}
                      onClick={() => entry.isDirectory ? (setCurrentDirectory(entry.path), loadDirectory(entry.path)) : loadFile(entry.path)}
                    >
                      {entry.isDirectory ? <FolderRegular fontSize={15} /> : <DocumentRegular fontSize={15} />}
                      <span className="editor-explorer__item-label">{entry.name}</span>
                    </button>
                  );
                })
              )}
            </div>
          </aside>

          <div className="editor-workbench__center">
            <div className="editor-tabstrip">
              {filename ? (
                <div className="editor-tab editor-tab--active">
                  <DocumentRegular fontSize={14} />
                  <Text className="editor-tab__label">{currentFileLabel}</Text>
                  {dirty && <span className="editor-tab__dirty" aria-hidden="true" />}
                  <button type="button" className="editor-tab__close" onClick={handleCloseCurrentFile} aria-label={t("editor_close_tab")}>
                    <DismissRegular fontSize={12} />
                  </button>
                </div>
              ) : (
                <div className="editor-tabstrip__empty">{t("editor_no_file")}</div>
              )}
            </div>

            <div className="editor-shell">
              {loading ? (
                <div className="editor-loading">
                  <Spinner label={t("loading")} />
                </div>
              ) : loadError ? (
                <div className="editor-empty">
                  <div className="editor-empty__body">
                    <Text weight="semibold" size={400}>{loadError}</Text>
                    <Caption1 className="muted-text">{t("editor_empty_desc")}</Caption1>
                    <div className="editor-empty__actions">
                      <Button icon={<DocumentRegular />} appearance="primary" onClick={handleOpenFile}>
                        {t("editor_open")}
                      </Button>
                      <Button icon={<DocumentAddRegular />} appearance="subtle" onClick={handleNewFile}>{t("editor_new")}</Button>
                    </div>
                  </div>
                </div>
              ) : !hasOpenFile ? (
                <div className="editor-empty">
                  <div className="editor-empty__body">
                    <Text weight="semibold" size={500}>{t("editor_empty_title")}</Text>
                    <Caption1 className="muted-text">{t("editor_empty_desc")}</Caption1>
                    <div className="editor-empty__actions">
                      <Button icon={<DocumentRegular />} appearance="primary" onClick={handleOpenFile}>
                        {t("editor_open")}
                      </Button>
                      <Button icon={<DocumentAddRegular />} appearance="subtle" onClick={handleNewFile}>{t("editor_new")}</Button>
                    </div>
                    <div className="editor-empty__tips">
                      {handbookHighlights.map((item) => (
                        <div className="editor-empty__tip" key={item.title}>
                          <Text weight="semibold">{item.title}</Text>
                          <Caption1 className="muted-text">{item.description}</Caption1>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <Editor
                  height="100%"
                  language="serikaMission"
                  value={content}
                  beforeMount={configureSerikaMissionMonaco}
                  onChange={handleEditorChange}
                  theme={isDark ? "serika-mission-dark" : "serika-mission-light"}
                  onMount={(editor) => {
                    editorRef.current = editor;
                  }}
                  options={{
                    automaticLayout: true,
                    minimap: { enabled: true, size: "proportional", showSlider: "mouseover" },
                    fontSize: 14,
                    lineHeight: 22,
                    fontFamily: "'Cascadia Code', 'Consolas', monospace",
                    lineNumbers: "on",
                    wordWrap: "bounded",
                    wrappingIndent: "indent",
                    scrollBeyondLastLine: false,
                    renderLineHighlight: "all",
                    folding: true,
                    tabSize: 2,
                    smoothScrolling: true,
                    padding: { top: 14, bottom: 14 },
                    bracketPairColorization: { enabled: true },
                    guides: { bracketPairs: true, indentation: true },
                    scrollbar: {
                      alwaysConsumeMouseWheel: false,
                      verticalScrollbarSize: 12,
                      horizontalScrollbarSize: 12,
                      useShadows: false,
                    },
                  }}
                />
              )}
            </div>

            <section className="editor-panel">
              <div className="editor-panel__header">
                <div>
                  <Text weight="semibold">{t("editor_issues")}</Text>
                  <Caption1 className="muted-text">{t("editor_issues_desc")}</Caption1>
                </div>
                <Caption1 className="muted-text">{t("editor_file_label")}: {currentFileLabel}</Caption1>
              </div>
              <div className="editor-issues">
                {!hasOpenFile ? (
                  <div className="editor-issue editor-issue--ok">
                    <Caption1 className="muted-text">{t("editor_issues_empty")}</Caption1>
                  </div>
                ) : issues.length === 0 ? (
                  <div className="editor-issue editor-issue--ok">
                    <CheckmarkCircleRegular fontSize={14} className="editor-issue__icon editor-issue__icon--ok" />
                    <Caption1>{t("editor_no_issues")}</Caption1>
                  </div>
                ) : (
                  issues.map((issue, i) => (
                    <div className="editor-issue" key={i}>
                      <ErrorCircleRegular fontSize={14} className="editor-issue__icon" />
                      <Caption1>
                        [{issue.kind}] {issue.message}
                        {issue.line ? ` (行 ${issue.line}${issue.column ? `:${issue.column}` : ""})` : ""}
                      </Caption1>
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>

          {helpVisible && (
            <aside className="editor-sidebar">
              <div className="editor-sidebar__header">
                <div>
                  <Text weight="semibold">{t("editor_help")}</Text>
                  <Caption1 className="muted-text">{t("editor_help_desc")}</Caption1>
                </div>
                <Button
                  icon={<DismissRegular />}
                  size="small"
                  appearance="subtle"
                  onClick={() => setHelpVisible(false)}
                  aria-label={t("close")}
                />
              </div>

              <div className="editor-sidebar__search">
                <Input
                  value={guideQuery}
                  onChange={(_, data) => setGuideQuery(data.value)}
                  placeholder={t("editor_help_search_placeholder")}
                  contentBefore={<SearchRegular />}
                />
              </div>

              <div className="editor-sidebar__highlights">
                <Text weight="semibold">{t("editor_help_highlights")}</Text>
                <div className="editor-sidebar__highlight-grid">
                  {handbookHighlights.map((item) => (
                    <div key={item.title} className="editor-sidebar__highlight">
                      <Text weight="semibold">{item.title}</Text>
                      <Caption1 className="muted-text">{item.description}</Caption1>
                    </div>
                  ))}
                </div>
              </div>

              <div className="editor-sidebar__sections">
                {filteredGuideSections.length === 0 ? (
                  <div className="editor-sidebar__empty">{t("editor_help_no_match")}</div>
                ) : (
                  filteredGuideSections.map((section) => (
                    <button
                      key={section.id}
                      type="button"
                      className={`editor-sidebar__section${selectedGuideSection?.id === section.id ? " editor-sidebar__section--active" : ""}`}
                      onClick={() => setSelectedGuideSectionId(section.id)}
                    >
                      <span className="editor-sidebar__section-title">{section.title}</span>
                      <span className="editor-sidebar__section-summary">{section.summary}</span>
                    </button>
                  ))
                )}
              </div>

              {selectedGuideSection && (
                <div className="editor-help-article__header">
                  <Text weight="semibold" size={400}>{selectedGuideSection.title}</Text>
                  <Caption1 className="muted-text">{selectedGuideSection.summary}</Caption1>
                </div>
              )}

              <div className="editor-help-markdown">
                {selectedGuideSection ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{selectedGuideSection.content}</ReactMarkdown>
                ) : (
                  <Caption1 className="muted-text">{t("editor_help_no_match")}</Caption1>
                )}
              </div>
            </aside>
          )}
        </div>
      </div>

      <Dialog
        open={createDialogOpen}
        onOpenChange={(_, data) => {
          setCreateDialogOpen(data.open);
          if (!data.open) {
            resetCreateDialog();
          }
        }}
      >
        <DialogSurface>
          <DialogBody>
            <DialogTitle>{t("editor_create_title")}</DialogTitle>
            <DialogContent>
              <div className="editor-create-dialog">
                <Caption1 className="muted-text">{t("editor_create_desc")}</Caption1>
                <Field label={t("editor_create_filename")} required validationMessage={createError ?? undefined}>
                  <Input
                    value={createFilename}
                    onChange={(_, data) => {
                      setCreateFilename(data.value);
                      if (createError) {
                        setCreateError(null);
                      }
                    }}
                    placeholder="new_mission.json"
                  />
                </Field>
                <Field label={t("editor_create_mode")}>
                  <Select value={createMode} onChange={(_, data) => setCreateMode(data.value as CreateMode)}>
                    <option value="blank">{t("editor_create_mode_blank")}</option>
                    <option value="template">{t("editor_create_mode_template")}</option>
                  </Select>
                </Field>
                {createMode === "template" && (
                  <div className="editor-create-dialog__fields">
                    <Field label={t("editor_create_template_title")}>
                      <Input value={createTitle} onChange={(_, data) => setCreateTitle(data.value)} />
                    </Field>
                    <Field label={t("editor_create_template_author")}>
                      <Input value={createAuthor} onChange={(_, data) => setCreateAuthor(data.value)} />
                    </Field>
                    <Field label={t("editor_create_template_version")}>
                      <Input value={createVersion} onChange={(_, data) => setCreateVersion(data.value)} />
                    </Field>
                  </div>
                )}
              </div>
            </DialogContent>
            <DialogActions>
              <Button
                appearance="secondary"
                onClick={() => {
                  setCreateDialogOpen(false);
                  resetCreateDialog();
                }}
              >
                {t("cancel")}
              </Button>
              <Button appearance="primary" onClick={handleConfirmCreate}>
                {t("editor_create_confirm")}
              </Button>
            </DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>
    </div>
  );
}
