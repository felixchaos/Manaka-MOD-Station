from PyQt6 import QtCore, QtGui, QtWidgets
from pathlib import Path
from typing import Optional, List, Dict
import json
from src.config import CUSTOM_MISSIONS_DIR
from .json_editor_tab import CodeEditor, PreviewTree
from src.mission_validator import validate_text, ValidationIssue


class MissionWizardDialog(QtWidgets.QDialog):
    """简单新建任务对话框：输入标题与文件名，立即创建文件。"""
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新建任务")
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.ed_title = QtWidgets.QLineEdit(self)
        self.ed_filename = QtWidgets.QLineEdit(self)
        self.ed_filename.setPlaceholderText("不带扩展名，例如 my_mission")
        # 生成默认唯一文件名 new_mission_1/2/…
        try:
            CUSTOM_MISSIONS_DIR.mkdir(parents=True, exist_ok=True)
            i = 1
            while True:
                candidate = f"new_mission_{i}"
                if not (CUSTOM_MISSIONS_DIR / f"{candidate}.json").exists():
                    self.ed_filename.setText(candidate)
                    break
                i += 1
        except Exception:
            self.ed_filename.setText("new_mission_1")
        form.addRow("任务标题:", self.ed_title)
        form.addRow("文件名:", self.ed_filename)
        layout.addLayout(form)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel, parent=self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_values(self) -> tuple[str, str]:
        return self.ed_title.text().strip() or "New Mission", self.ed_filename.text().strip() or "new_mission"


class JsonCreatorTab(QtWidgets.QWidget):
    """新任务 Json 创建：默认提供一个内嵌的空白编辑区；点击“新建”弹出向导对话框。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        # 多标签支持
        self._dirty_map: dict[int, bool] = {}
        self._path_map: dict[int, Optional[Path]] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # 顶部工具栏：新建/保存/另存为 + 撤销/重做 + 查找/替换
        bar = QtWidgets.QToolBar(self)
        bar.setMovable(False)
        self.act_new = bar.addAction("新建")
        self.act_save = bar.addAction("保存")
        self.act_save_as = bar.addAction("另存为…")
        bar.addSeparator()
        self.act_undo = bar.addAction("撤销")
        self.act_redo = bar.addAction("重做")
        bar.addSeparator()
        self.act_find = bar.addAction("查找")
        self.act_replace = bar.addAction("替换")
        # 快捷键
        self.act_save.setShortcut(QtGui.QKeySequence.StandardKey.Save)
        self.act_find.setShortcut(QtGui.QKeySequence.StandardKey.Find)
        self.act_replace.setShortcut(QtGui.QKeySequence.StandardKey.Replace)
        self.act_undo.setShortcut(QtGui.QKeySequence.StandardKey.Undo)
        self.act_redo.setShortcut(QtGui.QKeySequence.StandardKey.Redo)
        self.act_save.setEnabled(False)
        root.addWidget(bar)

        # 中间：垂直分割器（上：主区 | 下：错误面板）
        self._v_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical, self)
        self._v_splitter.setHandleWidth(6)

        # 上部主区：水平分割（左：预览树 | 右：编辑器标签）
        center_wrap = QtWidgets.QWidget(self)
        center_v = QtWidgets.QVBoxLayout(center_wrap)
        center_v.setContentsMargins(0, 0, 0, 0)
        center_v.setSpacing(6)
        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal, center_wrap)
        self._splitter.setHandleWidth(4)

        # 左：预览树
        preview_box = QtWidgets.QGroupBox("快速预览", self)
        pv = QtWidgets.QVBoxLayout(preview_box)
        self.tree_preview = PreviewTree(preview_box)
        self.tree_preview.navigateTo.connect(self._goto_line)
        self.tree_preview.itemDoubleClicked.connect(self._on_preview_item_double_clicked)
        pv.addWidget(self.tree_preview)
        self._splitter.addWidget(preview_box)

        # 右：编辑器标签
        editor_wrap = QtWidgets.QWidget(self)
        editor_v = QtWidgets.QVBoxLayout(editor_wrap)
        editor_v.setContentsMargins(0, 0, 0, 0)
        self.tab_editors = QtWidgets.QTabWidget(editor_wrap)
        self.tab_editors.setTabsClosable(True)
        self.tab_editors.currentChanged.connect(self._on_tab_changed)
        self.tab_editors.tabCloseRequested.connect(self._close_tab)
        editor_v.addWidget(self.tab_editors)
        self._splitter.addWidget(editor_wrap)

        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 4)
        center_v.addWidget(self._splitter, 1)

        # 底部：状态栏
        status = QtWidgets.QFrame(center_wrap)
        status.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        st = QtWidgets.QHBoxLayout(status)
        self.lbl_cursor = QtWidgets.QLabel("Ln 1, Col 1", status)
        self.lbl_path = QtWidgets.QLabel("未命名", status)
        self.lbl_saved = QtWidgets.QLabel("未保存", status)
        st.addWidget(self.lbl_cursor)
        st.addWidget(self.lbl_path)
        st.addStretch(1)
        st.addWidget(self.lbl_saved)
        center_v.addWidget(status)

        # 下部：错误面板
        err_container = QtWidgets.QWidget(self)
        err_v = QtWidgets.QVBoxLayout(err_container)
        err_v.setContentsMargins(0, 0, 0, 0)
        self.err_list = QtWidgets.QListWidget(err_container)
        self.err_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.err_list.itemClicked.connect(self._jump_to_error)
        err_v.addWidget(self.err_list)

        # 组装垂直分割器
        self._v_splitter.addWidget(center_wrap)
        self._v_splitter.addWidget(err_container)
        self._v_splitter.setStretchFactor(0, 8)
        self._v_splitter.setStretchFactor(1, 2)
        root.addWidget(self._v_splitter, 1)
        self._err_container = err_container
        self._error_panel_last_size = 140
        QtCore.QTimer.singleShot(0, lambda: self._set_error_panel_visible(False))

        # 默认创建一个未命名标签（最小可用模板）
        self.open_blank()

        # 信号
        self.act_new.triggered.connect(self._on_new)
        self.act_save.triggered.connect(self._on_save)
        self.act_save_as.triggered.connect(self._on_save_as)
        self.act_undo.triggered.connect(self._on_trigger_undo)
        self.act_redo.triggered.connect(self._on_trigger_redo)
        self.act_find.triggered.connect(self._find_text)
        self.act_replace.triggered.connect(self._replace_text)
        # 初始化按钮状态
        self._update_action_states()
        self.act_new.triggered.connect(self._on_new)
        self.act_save.triggered.connect(self._on_save)
        self.act_save_as.triggered.connect(self._on_save_as)
        self.act_undo.triggered.connect(self._on_trigger_undo)
        self.act_redo.triggered.connect(self._on_trigger_redo)
        self.act_find.triggered.connect(self._find_text)
        self.act_replace.triggered.connect(self._replace_text)
        # 初始化按钮状态
        self._update_action_states()

    def _create_editor_tab(self, initial_text: Optional[str] = None) -> int:
        page = QtWidgets.QWidget(self)
        v = QtWidgets.QVBoxLayout(page)
        editor = CodeEditor(page)
        editor.cursorPositionChangedDetailed.connect(self._on_cursor_changed)
        editor.validationReady.connect(self._update_errors)
        editor.validationReady.connect(self._maybe_refresh_preview)
        editor.textChanged.connect(lambda: self._on_editor_text_changed(editor))
        # 上下文菜单回调
        editor._save_cb = self._on_save
        editor._find_cb = self._find_text
        editor._replace_cb = self._replace_text
        try:
            editor.undoAvailable.connect(lambda _v: self._update_action_states())
            editor.redoAvailable.connect(lambda _v: self._update_action_states())
        except Exception:
            pass
        if isinstance(initial_text, str):
            editor.setPlainText(initial_text)
        v.addWidget(editor)
        page.setProperty("editor", editor)
        idx = self.tab_editors.addTab(page, f"未命名 {self.tab_editors.count()+1}")
        self.tab_editors.setCurrentIndex(idx)
        self._path_map[idx] = None
        self._dirty_map[idx] = False
        self._update_saved_label()
        return idx

    def open_blank(self) -> None:
        # 提供最小可用模板（满足结构校验）
        data = {
            "title": "New Mission",
            "listmission": True,
            "addtitleinlist": True,
            "addtitleinpanel": True,
            "zones": [
                {
                    "id": "zone1",
                    "areas": [
                        {"stage": "Park", "x": 0, "y": 0, "r": 5}
                    ]
                }
            ],
            "subconditions": [],
            "checkpoints": [
                {
                    "id": "cp1",
                    "zone": "zone1",
                    "nextcheckpoint": {"selectortype": "None"}
                }
            ],
        }
        self._create_editor_tab(json.dumps(data, ensure_ascii=False, indent=2))

    def _on_new(self) -> None:
        dlg = MissionWizardDialog(self)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        title, fname = dlg.get_values()
        CUSTOM_MISSIONS_DIR.mkdir(parents=True, exist_ok=True)
        path = CUSTOM_MISSIONS_DIR / f"{fname}.json"
        # 最小可用模板
        data = {
            "title": title,
            "listmission": True,
            "addtitleinlist": True,
            "addtitleinpanel": True,
            "zones": [
                {
                    "id": "zone1",
                    "areas": [
                        {"stage": "Park", "x": 0, "y": 0, "r": 5}
                    ]
                }
            ],
            "subconditions": [],
            "checkpoints": [
                {
                    "id": "cp1",
                    "zone": "zone1",
                    "nextcheckpoint": {"selectortype": "None"}
                }
            ],
        }
        # 写入文件
        try:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "创建失败", str(e))
            return
        # 打开新标签
        self._open_path(path)

    # 已按规范移除“打开”入口

    def _on_save(self) -> None:
        idx = self.tab_editors.currentIndex()
        if idx < 0:
            return
        path = self._path_map.get(idx)
        if path is None:
            return self._on_save_as()
        self._save_to(idx, path)

    def _on_save_as(self) -> None:
        idx = self.tab_editors.currentIndex()
        if idx < 0:
            return
        file, _ = QtWidgets.QFileDialog.getSaveFileName(self, "另存为", str(CUSTOM_MISSIONS_DIR), "JSON Files (*.json)")
        if not file:
            return
        path = Path(file)
        self._path_map[idx] = path
        self.tab_editors.setTabText(idx, Path(file).name)
        self._save_to(idx, path)

    def _save_to(self, idx: int, path: Path) -> None:
        ed = self._current_editor()
        if not ed:
            return
        text = ed.toPlainText()
        try:
            # 尝试解析并校验结构（显示但不阻塞保存）
            json.loads(text)
            path.write_text(text, encoding="utf-8")
            self._path_map[idx] = path
            self._dirty_map[idx] = False
            self._update_saved_label()
        except Exception:
            QtWidgets.QMessageBox.warning(self, "保存失败", "JSON 解析失败或无法写入。")

    def _open_path(self, path: Path) -> None:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "打开失败", str(e))
            return
        idx = self._create_editor_tab(text)
        self._path_map[idx] = path
        self.tab_editors.setTabText(idx, path.name)
        self._dirty_map[idx] = False
        self._update_saved_label()

    def _on_text_changed(self) -> None:
        self._set_saved(False)
        self._update_action_states()

    def _set_saved(self, saved: bool) -> None:
        idx = self.tab_editors.currentIndex()
        path = self._path_map.get(idx)
        self.lbl_path.setText(str(path) if path else "未命名")
        self.lbl_saved.setText("已保存" if saved else "未保存")
        self.act_save.setEnabled(not saved)

    def _current_editor(self) -> Optional[CodeEditor]:
        page = self.tab_editors.currentWidget()
        if not page:
            return None
        return page.property("editor")

    def _on_editor_text_changed(self, editor: CodeEditor) -> None:
        # 标记对应标签为脏
        idx = -1
        for i in range(self.tab_editors.count()):
            if self.tab_editors.widget(i).property("editor") is editor:
                idx = i
                break
        if idx >= 0:
            self._dirty_map[idx] = True
            self._update_saved_label()

    def _on_tab_changed(self, _idx: int) -> None:
        self._update_saved_label()
        self._update_action_states()

    def _close_tab(self, idx: int) -> None:
        """处理关闭指定索引的标签，支持保存/不保存/取消，并维护索引映射。"""
        try:
            count_before = self.tab_editors.count()
            if idx < 0 or idx >= count_before:
                return
            page = self.tab_editors.widget(idx)
            if page is None:
                return
            editor: CodeEditor = page.property("editor")
            # 先准备当前映射快照，方便移除后重建
            path_list = [self._path_map.get(i) for i in range(count_before)]
            dirty_list = [self._dirty_map.get(i, False) for i in range(count_before)]

            # 若有未保存更改则提示
            if dirty_list[idx]:
                name = self.tab_editors.tabText(idx)
                m = QtWidgets.QMessageBox(self)
                m.setWindowTitle("关闭标签")
                m.setIcon(QtWidgets.QMessageBox.Icon.Question)
                m.setText(f"是否保存对“{name}”的更改？")
                btn_save = m.addButton("保存", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
                btn_discard = m.addButton("不保存", QtWidgets.QMessageBox.ButtonRole.DestructiveRole)
                btn_cancel = m.addButton("取消", QtWidgets.QMessageBox.ButtonRole.RejectRole)
                m.setDefaultButton(btn_save)
                m.exec()
                clicked = m.clickedButton()
                if clicked is btn_cancel:
                    return
                if clicked is btn_save:
                    # 针对该索引执行保存（支持未命名另存为）
                    target_path = path_list[idx]
                    text = editor.toPlainText() if editor else ""
                    # 尝试解析（与保存逻辑一致，解析失败则中止关闭）
                    try:
                        json.loads(text)
                    except Exception:
                        QtWidgets.QMessageBox.warning(self, "保存失败", "JSON 解析失败，无法保存。")
                        return
                    if target_path is None:
                        file, _ = QtWidgets.QFileDialog.getSaveFileName(
                            self, "保存为", str(CUSTOM_MISSIONS_DIR), "JSON Files (*.json)"
                        )
                        if not file:
                            return
                        target_path = Path(file)
                    try:
                        target_path.write_text(text, encoding="utf-8")
                    except Exception as e:
                        QtWidgets.QMessageBox.warning(self, "保存失败", str(e))
                        return
                    # 更新该索引的状态
                    path_list[idx] = target_path
                    dirty_list[idx] = False
                    self.tab_editors.setTabText(idx, target_path.name)

            # 执行关闭并重建映射
            self.tab_editors.removeTab(idx)
            if page is not None:
                page.deleteLater()
            # 从快照中剔除对应项，重建映射
            if 0 <= idx < len(path_list):
                path_list.pop(idx)
            if 0 <= idx < len(dirty_list):
                dirty_list.pop(idx)
            self._path_map = {i: path_list[i] for i in range(len(path_list))}
            self._dirty_map = {i: dirty_list[i] for i in range(len(dirty_list))}

            # 若已无标签，创建一个空白模板，保持可用性
            if self.tab_editors.count() == 0:
                self.open_blank()

            # 更新底部状态与动作
            self._update_saved_label()
            self._update_action_states()
        except Exception:
            # 容错，避免关闭操作导致崩溃
            pass

    # 操作与状态
    def _on_trigger_undo(self) -> None:
        try:
            ed = self._current_editor()
            if ed:
                ed.undo()
        except Exception:
            pass

    def _on_trigger_redo(self) -> None:
        try:
            ed = self._current_editor()
            if ed:
                ed.redo()
        except Exception:
            pass

    def _on_cursor_changed(self, line: int, col: int) -> None:
        self.lbl_cursor.setText(f"Ln {line}, Col {col}")
        self._update_action_states()

    def _update_action_states(self) -> None:
        ed = self._current_editor()
        can_undo = bool(ed.document().isUndoAvailable()) if ed else False
        can_redo = bool(ed.document().isRedoAvailable()) if ed else False
        idx = self.tab_editors.currentIndex()
        is_dirty = bool(self._dirty_map.get(idx, False))
        self.act_save.setEnabled(is_dirty)
        self.act_save_as.setEnabled(True)
        self.act_find.setEnabled(True)
        self.act_replace.setEnabled(True)
        self.act_undo.setEnabled(can_undo)
        self.act_redo.setEnabled(can_redo)

    # 查找/替换
    def _find_text(self) -> None:
        text, ok = QtWidgets.QInputDialog.getText(self, "查找", "内容:")
        if not ok or not text:
            return
        ed = self._current_editor()
        if not ed:
            return
        if not ed.find(text):
            cursor = ed.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Start)
            ed.setTextCursor(cursor)
            ed.find(text)

    def _replace_text(self) -> None:
        ed = self._current_editor()
        if not ed:
            return
        find_text, ok = QtWidgets.QInputDialog.getText(self, "替换", "查找:")
        if not ok or not find_text:
            return
        replace_text, ok2 = QtWidgets.QInputDialog.getText(self, "替换", "替换为:")
        if not ok2:
            return
        if ed.find(find_text):
            cursor = ed.textCursor()
            cursor.insertText(replace_text)
        else:
            cursor = ed.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Start)
            ed.setTextCursor(cursor)
            if ed.find(find_text):
                cur = ed.textCursor()
                cur.insertText(replace_text)

    # 错误面板 & 预览
    def _update_errors(self, issues: List[ValidationIssue]) -> None:
        self.err_list.clear()
        for it in issues:
            line = f"(行 {it.line}) " if it.line else ""
            item = QtWidgets.QListWidgetItem(f"[{it.kind}] {line}{it.message}")
            item.setData(QtCore.Qt.ItemDataRole.UserRole, int(it.line) if it.line else None)
            self.err_list.addItem(item)
        # 附加简单括号/引号检查
        self._check_brackets_and_quotes()
        # 自动展开/收起错误面板
        has_errors = self.err_list.count() > 0
        self._set_error_panel_visible(has_errors)

    def _set_error_panel_visible(self, show: bool) -> None:
        try:
            sizes = self._v_splitter.sizes()
            if not sizes or len(sizes) < 2:
                return
            total = sum(sizes)
            cur_err_h = sizes[1]
            if show:
                if cur_err_h == 0:
                    err_h = max(80, self._error_panel_last_size)
                    self._v_splitter.setSizes([max(1, total - err_h), err_h])
                self._err_container.setVisible(True)
            else:
                if cur_err_h > 0:
                    self._error_panel_last_size = cur_err_h
                self._v_splitter.setSizes([total, 0])
                self._err_container.setVisible(False)
        except Exception:
            pass

    def _maybe_refresh_preview(self, issues: List[ValidationIssue]) -> None:
        if any(it.kind == "syntax" for it in issues):
            return
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        ed = self._current_editor()
        if not ed:
            return
        try:
            obj = json.loads(ed.toPlainText())
        except Exception:
            return
        self.tree_preview.clear()
        root_zone = QtWidgets.QTreeWidgetItem(["Zone"])
        root_sub = QtWidgets.QTreeWidgetItem(["SubCondition"])
        root_cp = QtWidgets.QTreeWidgetItem(["Checkpoint"])
        self.tree_preview.addTopLevelItem(root_zone)
        self.tree_preview.addTopLevelItem(root_sub)
        self.tree_preview.addTopLevelItem(root_cp)

        def preview(s: str, n: int = 80) -> str:
            s1 = s.replace("\n", " ")
            return (s1[: n] + ("…" if len(s1) > n else ""))

        # zones
        zones = obj.get("zones") if isinstance(obj, dict) else None
        if isinstance(zones, list):
            for i, z in enumerate(zones):
                if not isinstance(z, dict):
                    continue
                zid = z.get("id") or "zone"
                text = json.dumps(z, ensure_ascii=False, indent=2)
                it = QtWidgets.QTreeWidgetItem([str(zid), preview(text)])
                anchor = f'"id": "{z.get("id")}"' if isinstance(z.get("id"), str) else None
                ln = self._estimate_line_by_patterns(ed.toPlainText(), [anchor, text])
                it.setData(0, QtCore.Qt.ItemDataRole.UserRole, ln)
                it.setData(0, QtCore.Qt.ItemDataRole.UserRole + 1, text)
                it.setData(0, QtCore.Qt.ItemDataRole.UserRole + 2, anchor)
                it.setData(0, QtCore.Qt.ItemDataRole.UserRole + 3, "zones")
                it.setData(0, QtCore.Qt.ItemDataRole.UserRole + 4, i)
                root_zone.addChild(it)

        # subconditions
        subs = obj.get("subconditions") if isinstance(obj, dict) else None
        if isinstance(subs, list):
            for i, s in enumerate(subs):
                if not isinstance(s, dict):
                    continue
                sid = s.get("id") or "sub"
                text = json.dumps(s, ensure_ascii=False, indent=2)
                it = QtWidgets.QTreeWidgetItem([str(sid), preview(text)])
                anchor = f'"id": "{s.get("id")}"' if isinstance(s.get("id"), str) else None
                ln = self._estimate_line_by_patterns(ed.toPlainText(), [anchor, text])
                it.setData(0, QtCore.Qt.ItemDataRole.UserRole, ln)
                it.setData(0, QtCore.Qt.ItemDataRole.UserRole + 1, text)
                it.setData(0, QtCore.Qt.ItemDataRole.UserRole + 2, anchor)
                it.setData(0, QtCore.Qt.ItemDataRole.UserRole + 3, "subconditions")
                it.setData(0, QtCore.Qt.ItemDataRole.UserRole + 4, i)
                root_sub.addChild(it)

        # checkpoints 标题取 description
        cps = obj.get("checkpoints") if isinstance(obj, dict) else None
        if isinstance(cps, list):
            for i, c in enumerate(cps):
                if not isinstance(c, dict):
                    continue
                title = None
                for key in ("condition", "travelcondition"):
                    blk = c.get(key)
                    if isinstance(blk, dict) and isinstance(blk.get("description"), str):
                        title = blk.get("description")
                        break
                title = title or c.get("id") or "checkpoint"
                text = json.dumps(c, ensure_ascii=False, indent=2)
                it = QtWidgets.QTreeWidgetItem([str(title), preview(text)])
                anchor = None
                if isinstance(c.get("id"), str):
                    anchor = f'"id": "{c.get("id")}"'
                if anchor is None:
                    for key in ("condition", "travelcondition"):
                        blk = c.get(key)
                        if isinstance(blk, dict) and isinstance(blk.get("description"), str):
                            anchor = f'"description": "{blk.get("description")}"'
                            break
                ln = self._estimate_line_by_patterns(ed.toPlainText(), [anchor, text])
                it.setData(0, QtCore.Qt.ItemDataRole.UserRole, ln)
                it.setData(0, QtCore.Qt.ItemDataRole.UserRole + 1, text)
                it.setData(0, QtCore.Qt.ItemDataRole.UserRole + 2, anchor)
                it.setData(0, QtCore.Qt.ItemDataRole.UserRole + 3, "checkpoints")
                it.setData(0, QtCore.Qt.ItemDataRole.UserRole + 4, i)
                root_cp.addChild(it)

        self.tree_preview.expandAll()

    def _estimate_line_by_patterns(self, big: str, patterns: List[Optional[str]]) -> int:
        for p in patterns:
            if not p:
                continue
            idx = big.find(p)
            if idx >= 0:
                return big[:idx].count('\n') + 1
        return 1

    def _goto_line(self, line: int) -> None:
        ed = self._current_editor()
        block = ed.document().findBlockByNumber(max(0, line - 1))
        if block.isValid():
            cur = ed.textCursor()
            cur.setPosition(block.position())
            ed.setTextCursor(cur)
            try:
                ed.centerCursor()
            except Exception:
                pass
            ed.setFocus()

    def _on_preview_item_double_clicked(self, item: QtWidgets.QTreeWidgetItem) -> None:
        ed = self._current_editor()
        if not ed:
            return
        text = item.data(0, QtCore.Qt.ItemDataRole.UserRole + 1)
        line = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(line, int):
            self._goto_line(line)
        if isinstance(text, str) and text:
            doc_text = ed.toPlainText()
            start = doc_text.find(text)
            if start < 0:
                anchor = item.data(0, QtCore.Qt.ItemDataRole.UserRole + 2)
                if isinstance(anchor, str) and anchor:
                    start = doc_text.find(anchor)
                if start < 0:
                    key = item.data(0, QtCore.Qt.ItemDataRole.UserRole + 3)
                    idx = item.data(0, QtCore.Qt.ItemDataRole.UserRole + 4)
                    if isinstance(key, str) and isinstance(idx, int):
                        s2, e2 = self._locate_array_element(doc_text, key, idx)
                        if s2 is not None and e2 is not None:
                            start = s2
                            text = doc_text[s2:e2]
            if start >= 0:
                # 选中可能的对象块范围
                s, e = self._find_enclosing_braces(doc_text, start)
                if s is None or e is None:
                    s = start
                    e = start + len(text)
                cur = ed.textCursor()
                cur.setPosition(s)
                cur.setPosition(e, QtGui.QTextCursor.MoveMode.KeepAnchor)
                ed.setTextCursor(cur)
                try:
                    # 确保光标与选区可见并滚动到中心
                    ed.ensureCursorVisible()
                except Exception:
                    pass
                try:
                    ed.centerCursor()
                except Exception:
                    pass
                try:
                    ed.setFocus()
                except Exception:
                    pass

    def _locate_array_element(self, text: str, key: str, index: int) -> tuple[Optional[int], Optional[int]]:
        """在文本中根据属性名 key 找到数组的第 index 个对象的范围。"""
        import re
        m = re.search(rf'"{re.escape(key)}"\s*:\s*\[', text)
        if not m:
            return (None, None)
        i = m.end()
        depth_obj = 0
        in_str = False
        esc = False
        count = -1
        start = None
        while i < len(text):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == '{':
                    depth_obj += 1
                    if depth_obj == 1:
                        count += 1
                        if count == index:
                            start = i
                elif ch == '}':
                    if depth_obj:
                        depth_obj -= 1
                        if depth_obj == 0 and count == index and start is not None:
                            return (start, i + 1)
                elif ch == ']':
                    return (None, None)
            i += 1
        return (None, None)

    def _jump_to_error(self, item: QtWidgets.QListWidgetItem) -> None:
        line = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if line is None:
            return
        ed = self._current_editor()
        if not ed:
            return
        cursor = ed.textCursor()
        block = ed.document().findBlockByNumber(max(0, int(line) - 1))
        if block.isValid():
            cursor.setPosition(block.position())
            ed.setTextCursor(cursor)
            try:
                ed.ensureCursorVisible()
            except Exception:
                pass
            try:
                ed.centerCursor()
            except Exception:
                pass
            try:
                ed.setFocus()
            except Exception:
                pass

    def _check_brackets_and_quotes(self) -> None:
        ed = self._current_editor()
        text = ed.toPlainText()
        stack = []
        pairs = {')': '(', ']': '[', '}': '{'}
        openings = set(pairs.values())
        closes = set(pairs.keys())
        single_open = double_open = False
        problems: list[tuple[int, str]] = []
        line = 1
        for ch in text:
            if ch == '\n':
                line += 1
                continue
            if ch == '"' and not single_open:
                double_open = not double_open
            elif ch == "'" and not double_open:
                single_open = not single_open
            if single_open or double_open:
                continue
            if ch in openings:
                stack.append((ch, line))
            elif ch in closes:
                if not stack or stack[-1][0] != pairs[ch]:
                    problems.append((line, f"括号不匹配: 意外的 {ch}"))
                else:
                    stack.pop()
        for op, ln in stack:
            problems.append((ln, f"括号未闭合: {op}"))
        if single_open:
            problems.append((line, "引号未闭合: '"))
        if double_open:
            problems.append((line, '引号未闭合: "'))
        for ln, msg in problems:
            it = QtWidgets.QListWidgetItem(f"[lint] (行 {ln}) {msg}")
            it.setData(QtCore.Qt.ItemDataRole.UserRole, ln)
            self.err_list.addItem(it)

    def _update_saved_label(self) -> None:
        idx = self.tab_editors.currentIndex()
        path = self._path_map.get(idx)
        self.lbl_path.setText(str(path) if path else "未命名")
        dirty = bool(self._dirty_map.get(idx, False))
        self.lbl_saved.setText("未保存" if dirty else "已保存")
        self.act_save.setEnabled(dirty)

    def _find_enclosing_braces(self, text: str, pos: int) -> tuple[Optional[int], Optional[int]]:
        start = text.rfind('{', 0, pos)
        if start < 0:
            return (None, None)
        depth = 0
        end = None
        i = start
        in_str = False
        esc = False
        while i < len(text):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            i += 1
        return (start, end)
