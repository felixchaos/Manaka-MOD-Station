from PyQt6 import QtCore, QtGui, QtWidgets
from src.settings_manager import load_settings, save_settings
from src.game_sync import get_game_custom_dir, ensure_game_custom_dir, sync_game_to_workspace
from src.config import CUSTOM_MISSIONS_DIR


class SettingsTab(QtWidgets.QWidget):
    """设置标签页
    - 取消左侧菜单，直接展示分组
    - 常规：语言、游戏目录选择与同步
    - 界面：主题
    - 更新：占位
    - 底部：保存/恢复
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        body = QtWidgets.QWidget(self)
        v = QtWidgets.QVBoxLayout(body)
        v.addWidget(self._section_general())
        v.addWidget(self._section_ui())
        v.addWidget(self._section_update())
        v.addStretch(1)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)
        # 底部：状态栏（自动保存，仅保留恢复默认）
        status = QtWidgets.QFrame(self)
        status.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        st = QtWidgets.QHBoxLayout(status)
        self.lbl_state = QtWidgets.QLabel("已保存", status)
        btn_restore = QtWidgets.QPushButton("恢复默认", status)
        st.addWidget(self.lbl_state)
        st.addStretch(1)
        st.addWidget(btn_restore)
        root.addWidget(status)

        # 信号
        btn_restore.clicked.connect(self._restore_default)

        # 加载设置
        self._data = load_settings()
        self._apply_to_ui()
        self._mark_saved()

    def _section_general(self) -> QtWidgets.QGroupBox:
        g = QtWidgets.QGroupBox("常规设置", self)
        form = QtWidgets.QFormLayout(g)
        self.cmb_lang = QtWidgets.QComboBox(g)
        self.cmb_lang.addItems(["zh-CN", "en-US"])
        # 缩短下拉框视觉宽度
        self.cmb_lang.setMaximumWidth(120)

        # 游戏目录
        row = QtWidgets.QHBoxLayout()
        self.txt_game_dir = QtWidgets.QLineEdit(g)
        self.txt_game_dir.setPlaceholderText("请选择游戏安装目录…")
        btn_pick = QtWidgets.QPushButton("选择…", g)
        btn_open_dir = QtWidgets.QPushButton("打开游戏目录", g)
        btn_sync = QtWidgets.QPushButton("从游戏目录同步到本地", g)
        row.addWidget(self.txt_game_dir, 1)
        row.addWidget(btn_pick)
        row.addWidget(btn_open_dir)
        row.addWidget(btn_sync)
        w = QtWidgets.QWidget(g)
        w.setLayout(row)

        form.addRow("语言:", self.cmb_lang)
        form.addRow("游戏目录:", w)
        # 自定义任务目录显示
        row2 = QtWidgets.QHBoxLayout()
        self.lbl_custom_dir = QtWidgets.QLineEdit(g)
        self.lbl_custom_dir.setReadOnly(True)
        btn_open_custom = QtWidgets.QPushButton("打开", g)
        row2.addWidget(self.lbl_custom_dir, 1)
        row2.addWidget(btn_open_custom)
        w2 = QtWidgets.QWidget(g)
        w2.setLayout(row2)
        form.addRow("自定义任务库目录:", w2)

        # 交互：选择 & 同步 & 打开目录
        btn_pick.clicked.connect(self._pick_game_dir)
        btn_open_dir.clicked.connect(self._open_game_dir)
        btn_sync.clicked.connect(self._sync_from_game)
        btn_open_custom.clicked.connect(self._open_custom_dir)
        # 语言改变：立即应用
        self.cmb_lang.currentTextChanged.connect(self._on_language_changed)
        # 文本框变动即保存
        self.txt_game_dir.textChanged.connect(self._on_game_dir_changed)
        self.txt_game_dir.textChanged.connect(self._validate_game_dir)
        return g

    def _section_ui(self) -> QtWidgets.QGroupBox:
        g = QtWidgets.QGroupBox("界面设置", self)
        form = QtWidgets.QFormLayout(g)
        self.cmb_theme = QtWidgets.QComboBox(g)
        self.cmb_theme.addItems(["light", "dark", "system"])
        # 缩短主题下拉框显示宽度
        self.cmb_theme.setMaximumWidth(120)
        form.addRow("主题:", self.cmb_theme)
        # 主题改变：立即应用
        self.cmb_theme.currentTextChanged.connect(self._on_theme_changed)
        return g

    def _section_update(self) -> QtWidgets.QGroupBox:
        g = QtWidgets.QGroupBox("更新设置", self)
        form = QtWidgets.QFormLayout(g)
        self.chk_start_check = QtWidgets.QCheckBox(g)
        self.chk_auto_download = QtWidgets.QCheckBox(g)
        form.addRow("开机自启更新检查:", self.chk_start_check)
        form.addRow("自动下载更新:", self.chk_auto_download)
        return g

    # 数据与交互
    def _apply_to_ui(self) -> None:
        self.cmb_lang.setCurrentText(self._data.get("language", "zh-CN"))
        self.cmb_theme.setCurrentText(self._data.get("theme", "light"))
        self.txt_game_dir.setText(self._data.get("gameDir") or "")
        # 初始进行一次校验
        self._validate_game_dir()
        self.chk_start_check.setChecked(bool(self._data.get("updateCheckAtStartup", False)))
        self.chk_auto_download.setChecked(bool(self._data.get("autoDownloadUpdate", False)))
        # 更新自定义任务目录显示
        from src.config import CUSTOM_MISSIONS_DIR
        self.lbl_custom_dir.setText(str(CUSTOM_MISSIONS_DIR))

    def _collect_from_ui(self) -> None:
        self._data.update({
            "language": self.cmb_lang.currentText(),
            "theme": self.cmb_theme.currentText(),
            "gameDir": self.txt_game_dir.text().strip() or None,
            "updateCheckAtStartup": self.chk_start_check.isChecked(),
            "autoDownloadUpdate": self.chk_auto_download.isChecked(),
        })

    # 交互：游戏目录
    def _pick_game_dir(self) -> None:
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "选择游戏目录")
        if not d:
            return
        self.txt_game_dir.setText(d)
        self._collect_from_ui()
        save_settings(self._data)
        # 检查/创建 CustomMissions
        gdir = get_game_custom_dir(d)
        if not gdir.exists():
            ret = QtWidgets.QMessageBox.question(self, "未找到 CustomMissions", f"目录 {d} 下未找到 CustomMissions，是否创建？")
            if ret == QtWidgets.QMessageBox.StandardButton.Yes:
                ensure_game_custom_dir(d)
            else:
                return
        # 选择后立即同步一次
        self._sync_from_game()

    def _sync_from_game(self) -> None:
        game_dir = self.txt_game_dir.text().strip()
        if not game_dir:
            QtWidgets.QMessageBox.information(self, "请选择", "请先选择游戏目录。")
            return
        copied, skipped, renamed = sync_game_to_workspace(game_dir)
        # 刷新两个页面数据：Mod 管理 & 编辑器文件树
        self._refresh_external_views()
        QtWidgets.QMessageBox.information(self, "完成", f"复制: {copied}, 跳过: {skipped}, 重命名复制: {renamed}")

    def _open_game_dir(self) -> None:
        d = self.txt_game_dir.text().strip()
        if not d:
            QtWidgets.QMessageBox.information(self, "未设置", "请先设置游戏目录。")
            return
        # 在资源管理器打开该目录
        try:
            QtCore.QProcess.startDetached("explorer", [str(d)])
        except Exception:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(d))

    def _refresh_external_views(self) -> None:
        # 遍历父窗口查找 tabs 并调用它们的刷新方法（若有）
        w = self.parent()
        while w and not isinstance(w, QtWidgets.QMainWindow):
            w = w.parent()
        if not w:
            return
        # Mod 管理
        try:
            w.mod_manager_tab._reload_mods()
        except Exception:
            pass
        # 编辑器右侧文件树
        try:
            w.json_editor_tab._populate_tree()
        except Exception:
            pass

    def _save_current(self) -> None:
        self._collect_from_ui()
        save_settings(self._data)
        self._mark_saved()

    # 运行时应用主题
    def _on_theme_changed(self, theme: str) -> None:
        self._collect_from_ui()
        save_settings(self._data)
        # 通知主窗口应用
        w = self.parent()
        while w and not isinstance(w, QtWidgets.QMainWindow):
            w = w.parent()
        if w and hasattr(w, "apply_theme"):
            w.apply_theme(theme)
        self._mark_saved()

    # 运行时应用语言
    def _on_language_changed(self, lang: str) -> None:
        self._collect_from_ui()
        save_settings(self._data)
        w = self.parent()
        while w and not isinstance(w, QtWidgets.QMainWindow):
            w = w.parent()
        if w and hasattr(w, "apply_language"):
            w.apply_language(lang)
        self._mark_saved()

    # 简易文案刷新（供语言变更时调用）
    def retranslate(self, lang: str) -> None:
        if lang == "en-US":
            self.setTitle = self.setWindowTitle  # no-op placeholder
            # 组标题
            self.findChild(QtWidgets.QGroupBox, None).setTitle if False else None
        else:
            pass

    def _restore_default(self) -> None:
        from src.settings_manager import DEFAULT_SETTINGS
        self._data = DEFAULT_SETTINGS.copy()
        self._apply_to_ui()
        save_settings(self._data)
        self._mark_saved()

    def _on_game_dir_changed(self, _text: str) -> None:
        # 文本变更自动保存
        self._collect_from_ui()
        save_settings(self._data)
        self._mark_saved()
        self._validate_game_dir()

    def _validate_game_dir(self) -> None:
        # 路径存在性校验，不存在时红色边框提示
        path = self.txt_game_dir.text().strip()
        ok = False
        try:
            from pathlib import Path
            ok = bool(path) and Path(path).exists()
        except Exception:
            ok = False
        pal = self.txt_game_dir.palette()
        if ok:
            # 清除红框
            self.txt_game_dir.setStyleSheet("")
        else:
            self.txt_game_dir.setStyleSheet("QLineEdit{border:1px solid #d9534f}")

    def _open_custom_dir(self) -> None:
        try:
            QtCore.QProcess.startDetached("explorer", [str(CUSTOM_MISSIONS_DIR)])
        except Exception:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(CUSTOM_MISSIONS_DIR)))

    def _mark_saved(self) -> None:
        self.lbl_state.setText("已保存")

    def _mark_unsaved(self) -> None:
        self.lbl_state.setText("未保存")
