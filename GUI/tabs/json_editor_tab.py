from PyQt6 import QtCore, QtGui, QtWidgets
from pathlib import Path
import json
from typing import Optional, List, Dict

from src.config import CUSTOM_MISSIONS_DIR
from src.mission_validator import validate_text, ValidationIssue


class LineNumberArea(QtWidgets.QWidget):
    def __init__(self, editor: 'CodeEditor') -> None:
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(self.codeEditor.line_number_area_width(), 0)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        self.codeEditor.line_number_area_paint_event(event)


class CodeEditor(QtWidgets.QPlainTextEdit):
    """简单的代码编辑器，支持行号、实时 JSON 校验、基础折叠、上下文菜单。"""

    cursorPositionChangedDetailed = QtCore.pyqtSignal(int, int)
    validationReady = QtCore.pyqtSignal(list)  # List[ValidationIssue]

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(' '))
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self._emit_cursor_pos)
        self._line_number_area = LineNumberArea(self)
        self._folded_ranges: list[tuple[int, int]] = []
        self._show_indent_guides: bool = True
        self._lint_lines: set[int] = set()

        self._validate_timer = QtCore.QTimer(self)
        self._validate_timer.setInterval(400)
        self._validate_timer.setSingleShot(True)
        self._validate_timer.timeout.connect(self._run_validation)
        self.update_line_number_area_width(0)
        self.textChanged.connect(lambda: self._validate_timer.start())
        QtCore.QTimer.singleShot(0, self._run_validation)

        # 菜单回调（外部注入）
        self._save_cb = None
        self._find_cb = None
        self._replace_cb = None

    # 行号区宽度
    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _newBlockCount: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: QtCore.QRect, dy: int) -> None:
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(QtCore.QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self._line_number_area)
        painter.fillRect(event.rect(), self.palette().alternateBase())

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(self.palette().mid().color())
                fm = self.fontMetrics()
                painter.drawText(0, top, self._line_number_area.width()-6, fm.height(),
                                 QtCore.Qt.AlignmentFlag.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        # 先让基础内容绘制
        super().paintEvent(event)
        # 绘制缩进引导线
        if not self._show_indent_guides:
            return
        painter = QtGui.QPainter(self.viewport())
        color = self.palette().mid().color()
        color.setAlpha(110)
        pen = QtGui.QPen(color, 1, QtCore.Qt.PenStyle.DotLine)
        painter.setPen(pen)
        # 每个可见行绘制引导线
        block = self.firstVisibleBlock()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        space_w = self.fontMetrics().horizontalAdvance(' ')
        tab_w_spaces = max(1, int(self.tabStopDistance() / space_w))
        visible_rect = self.viewport().rect()
        while block.isValid() and top <= visible_rect.bottom():
            if block.isVisible() and bottom >= visible_rect.top():
                text = block.text()
                indent_cols = 0
                for ch in text:
                    if ch == ' ':
                        indent_cols += 1
                    elif ch == '\t':
                        indent_cols += tab_w_spaces
                    else:
                        break
                # 以4空格为一个缩进层级
                level = indent_cols // 4
                for i in range(1, level + 1):
                    x = int(i * 4 * space_w)
                    painter.drawLine(x, top, x, bottom)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())

    def _emit_cursor_pos(self) -> None:
        cursor = self.textCursor()
        self.cursorPositionChangedDetailed.emit(cursor.blockNumber()+1, cursor.columnNumber()+1)

    def set_lint_lines(self, lines: List[int]) -> None:
        """高亮需要注意的行（简单 lint 行）。1-based 行号。"""
        self._lint_lines = set(int(x) for x in lines if isinstance(x, int) and x > 0)
        self._update_extra_selections()

    def _update_extra_selections(self) -> None:
        selections: list[QtWidgets.QTextEdit.ExtraSelection] = []
        # 高亮 lint 行
        for ln in sorted(self._lint_lines):
            block = self.document().findBlockByNumber(max(0, ln - 1))
            if not block.isValid():
                continue
            sel = QtWidgets.QTextEdit.ExtraSelection()
            cur = QtGui.QTextCursor(block)
            sel.cursor = cur
            fmt = QtGui.QTextCharFormat()
            fmt.setBackground(QtGui.QColor(255, 80, 80, 60))
            sel.format = fmt
            selections.append(sel)
        self.setExtraSelections(selections)

    # 校验
    def _run_validation(self) -> None:
        issues = validate_text(self.toPlainText())
        self.validationReady.emit(issues)

    # 折叠：基于简单花括号匹配
    def fold_at_cursor(self) -> None:
        cursor = self.textCursor()
        doc = self.document()
        pos = cursor.position()
        text = self.toPlainText()
        start = text.rfind('{', 0, pos)
        if start == -1:
            return
        depth = 0
        end = -1
        for i in range(start, len(text)):
            ch = text[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end == -1:
            return
        start_block = doc.findBlock(start).blockNumber()
        end_block = doc.findBlock(end).blockNumber()
        if end_block - start_block <= 1:
            return
        block = doc.findBlockByNumber(start_block + 1)
        while block.isValid() and block.blockNumber() < end_block:
            block.setVisible(False)
            block = block.next()
        self._folded_ranges.append((start_block + 1, end_block - 1))
        doc.markContentsDirty(0, doc.characterCount())
        self.update()

    def unfold_all(self) -> None:
        doc = self.document()
        block = doc.begin()
        while block.isValid():
            if not block.isVisible():
                block.setVisible(True)
            block = block.next()
        self._folded_ranges.clear()
        doc.markContentsDirty(0, doc.characterCount())
        self.update()

    def contextMenuEvent(self, e: QtGui.QContextMenuEvent) -> None:
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        act_find = menu.addAction("查找")
        act_replace = menu.addAction("替换")
        act_save = menu.addAction("保存")
        menu.addSeparator()
        act_fold = menu.addAction("折叠当前块")
        act_unfold = menu.addAction("展开全部")
        action = menu.exec(e.globalPos())
        if action == act_find and callable(self._find_cb):
            self._find_cb()
        elif action == act_replace and callable(self._replace_cb):
            self._replace_cb()
        elif action == act_save and callable(self._save_cb):
            self._save_cb()
        elif action == act_fold:
            self.fold_at_cursor()
        elif action == act_unfold:
            self.unfold_all()


class PreviewTree(QtWidgets.QTreeWidget):
    """快速预览树：双击定位编辑器位置；右键复制片段文本。"""
    navigateTo = QtCore.pyqtSignal(int)  # 行号(1-based)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setHeaderLabels(["块", "预览"])
        self.setColumnWidth(0, 200)
        self.setAlternatingRowColors(True)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_menu)
        self.itemDoubleClicked.connect(self._on_double)

    def _on_double(self, item: QtWidgets.QTreeWidgetItem, _col: int) -> None:
        # 若叶子节点携带了片段文本，交由外层处理高亮与跳转；否则仅按行号跳转
        text = item.data(0, QtCore.Qt.ItemDataRole.UserRole + 1)
        if not isinstance(text, str) or not text:
            line = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if isinstance(line, int):
                self.navigateTo.emit(line)

    def _on_menu(self, pos: QtCore.QPoint) -> None:
        item = self.itemAt(pos)
        if not item:
            return
        menu = QtWidgets.QMenu(self)
        act_copy = menu.addAction("复制该块到剪贴板")
        action = menu.exec(self.viewport().mapToGlobal(pos))
        if action == act_copy:
            text = item.data(0, QtCore.Qt.ItemDataRole.UserRole + 1)
            if isinstance(text, str):
                QtWidgets.QApplication.clipboard().setText(text)


class JsonEditorTab(QtWidgets.QWidget):
    """任务 Json 编辑标签页"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # 顶部：文件操作按钮
        toolbar = QtWidgets.QToolBar(self)
        toolbar.setMovable(False)
        self.act_open = toolbar.addAction("打开")
        self.act_save = toolbar.addAction("保存")
        self.act_save_as = toolbar.addAction("另存为")
        toolbar.addSeparator()
        self.act_undo = toolbar.addAction("撤销")
        self.act_redo = toolbar.addAction("重做")
        toolbar.addSeparator()
        self.act_find = toolbar.addAction("查找")
        self.act_replace = toolbar.addAction("替换")
        # 快捷键
        self.act_save.setShortcut(QtGui.QKeySequence.StandardKey.Save)
        self.act_find.setShortcut(QtGui.QKeySequence.StandardKey.Find)
        self.act_replace.setShortcut(QtGui.QKeySequence.StandardKey.Replace)
        self.act_undo.setShortcut(QtGui.QKeySequence.StandardKey.Undo)
        self.act_redo.setShortcut(QtGui.QKeySequence.StandardKey.Redo)
        root.addWidget(toolbar)

        # 中间：分栏（上：主界面 | 下：错误面板 可折叠/可调高）
        self._v_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical, self)
        self._v_splitter.setHandleWidth(6)
        # 顶部主区域容器
        center_wrap = QtWidgets.QWidget(self)
        center_v = QtWidgets.QVBoxLayout(center_wrap)
        center_v.setContentsMargins(0, 0, 0, 0)
        center_v.setSpacing(6)

        # 主区域内部：分栏（左：快速预览 | 中：编辑器 | 右：文件浏览）
        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal, center_wrap)
        self._splitter.setHandleWidth(4)

        # 左侧：快速预览
        preview_box = QtWidgets.QGroupBox("快速预览", self)
        sn_layout = QtWidgets.QVBoxLayout(preview_box)
        self.tree_preview = PreviewTree(preview_box)
        self.tree_preview.navigateTo.connect(self._goto_line)
        self.tree_preview.itemDoubleClicked.connect(self._on_preview_item_double_clicked)
        sn_layout.addWidget(self.tree_preview)
        self._splitter.addWidget(preview_box)

        # 中间：编辑器区 + 竖向折叠按钮
        editor_wrap = QtWidgets.QWidget(self)
        editor_h = QtWidgets.QHBoxLayout(editor_wrap)
        editor_h.setContentsMargins(0, 0, 0, 0)
        editor_h.setSpacing(0)
        editor_panel = QtWidgets.QWidget(editor_wrap)
        editor_layout = QtWidgets.QVBoxLayout(editor_panel)
        self.tab_editors = QtWidgets.QTabWidget(editor_panel)
        self.tab_editors.setTabsClosable(True)
        editor_layout.addWidget(self.tab_editors)
        side_bar = QtWidgets.QWidget(editor_wrap)
        side_layout = QtWidgets.QVBoxLayout(side_bar)
        side_layout.setContentsMargins(2, 2, 2, 2)
        side_layout.addStretch(1)
        self.btn_mid_toggle = QtWidgets.QToolButton(side_bar)
        self.btn_mid_toggle.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.btn_mid_toggle.setText("展\n开")
        self.btn_mid_toggle.setFixedWidth(16)
        self.btn_mid_toggle.setCheckable(True)
        self.btn_mid_toggle.setChecked(False)
        self.btn_mid_toggle.clicked.connect(lambda: self._toggle_browser(self.btn_mid_toggle.isChecked()))
        side_layout.addWidget(self.btn_mid_toggle)
        side_layout.addStretch(1)
        editor_h.addWidget(editor_panel, 1)
        editor_h.addWidget(side_bar, 0)
        self._splitter.addWidget(editor_wrap)

        # 右侧：文件浏览（可折叠）
        right_wrap = QtWidgets.QWidget(self)
        right_v = QtWidgets.QVBoxLayout(right_wrap)
        self.browser_container = QtWidgets.QGroupBox("文件浏览", self)
        br_layout = QtWidgets.QVBoxLayout(self.browser_container)
        self.search_box = QtWidgets.QLineEdit(self.browser_container)
        self.search_box.setPlaceholderText("搜索文件名或标题…")
        br_layout.addWidget(self.search_box)
        self.tree = QtWidgets.QTreeWidget(self.browser_container)
        self.tree.setHeaderLabels(["组/文件", "标题"])
        self.tree.setRootIsDecorated(True)
        self.tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_menu)
        br_layout.addWidget(self.tree)
        self._populate_tree()
        self.browser_container.setVisible(False)
        right_v.addWidget(self.browser_container)
        self._splitter.addWidget(right_wrap)

        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 4)
        self._splitter.setStretchFactor(2, 2)
        center_v.addWidget(self._splitter, 1)
        # 设置一个合理的初始尺寸，避免预览区域占满
        QtCore.QTimer.singleShot(0, lambda: self._splitter.setSizes([260, 900, 360]))

        # 主区域底部：状态栏
        status = QtWidgets.QFrame(center_wrap)
        status.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        st_layout = QtWidgets.QHBoxLayout(status)
        self.lbl_cursor = QtWidgets.QLabel("Ln 1, Col 1", status)
        self.lbl_saved = QtWidgets.QLabel("未保存", status)
        self.lbl_encoding = QtWidgets.QLabel("UTF-8", status)
        st_layout.addWidget(self.lbl_cursor)
        st_layout.addWidget(self.lbl_saved)
        st_layout.addStretch(1)
        st_layout.addWidget(self.lbl_encoding)
        center_v.addWidget(status)

        # 错误面板（可折叠/可调高）
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
        # 初始收起错误面板
        QtCore.QTimer.singleShot(0, lambda: self._set_error_panel_visible(False))

        # 信号
        self.tab_editors.currentChanged.connect(self._on_tab_changed)
        self.tab_editors.tabCloseRequested.connect(self._close_tab)
        self.tree.itemDoubleClicked.connect(self._open_from_item)
        self.search_box.textChanged.connect(self._apply_browser_filter)
        self.act_open.triggered.connect(self._action_open_dialog)
        self.act_save.triggered.connect(self._action_save)
        self.act_save_as.triggered.connect(self._action_save_as)
        self.act_undo.triggered.connect(self._on_trigger_undo)
        self.act_redo.triggered.connect(self._on_trigger_redo)
        # 状态
        self._dirty_map = {}  # tab index -> bool
        self._path_map = {}   # tab index -> Path|None

        # 初始隐藏右侧浏览器（不调整分割比例）
        self._toggle_browser(False)
        # 初始化按钮状态
        self._update_action_states()

    def _create_editor_tab(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget(self)
        v = QtWidgets.QVBoxLayout(page)
        editor = CodeEditor(page)
        editor.cursorPositionChangedDetailed.connect(self._on_cursor_changed)
        editor.textChanged.connect(lambda: self._on_editor_text_changed(editor))
        editor.validationReady.connect(self._update_errors)
        editor.validationReady.connect(self._maybe_refresh_preview)
        # 让 editor 的菜单可调用 Tab 的行为，及撤销/重做状态联动
        editor._save_cb = self._action_save
        editor._find_cb = self._find_text
        editor._replace_cb = self._replace_text
        try:
            editor.undoAvailable.connect(lambda _v: self._update_action_states())
            editor.redoAvailable.connect(lambda _v: self._update_action_states())
        except Exception:
            pass
        v.addWidget(editor)
        page.setProperty("editor", editor)
        return page

    def _on_cursor_changed(self, line: int, col: int) -> None:
        self.lbl_cursor.setText(f"Ln {line}, Col {col}")
        self._update_action_states()

    def _on_tab_changed(self, _idx: int) -> None:
        idx = self.tab_editors.currentIndex()
        self._update_saved_label(idx)
        try:
            self._update_action_states()
        except Exception:
            pass

    # 事件与动作
    def _current_editor(self) -> Optional[CodeEditor]:
        page = self.tab_editors.currentWidget()
        if not page:
            return None
        ed = page.property("editor")
        return ed

    def _on_trigger_undo(self) -> None:
        ed = self._current_editor()
        if ed:
            ed.undo()

    def _on_trigger_redo(self) -> None:
        ed = self._current_editor()
        if ed:
            ed.redo()

    def _open_from_item(self, item: QtWidgets.QTreeWidgetItem, _col: int) -> None:
        data = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(data, str):
            path = Path(data)
            if path.is_file() and path.suffix.lower() == ".json":
                self._open_file(path)

    def _action_open_dialog(self) -> None:
        file, _ = QtWidgets.QFileDialog.getOpenFileName(self, "打开 JSON", str(CUSTOM_MISSIONS_DIR), "JSON Files (*.json)")
        if file:
            self._open_file(Path(file))

    def _action_new(self) -> None:
        # 弹出对话框输入标题与文件名
        title, ok1 = QtWidgets.QInputDialog.getText(self, "新建任务", "任务标题:")
        if not ok1:
            return
        fname, ok2 = QtWidgets.QInputDialog.getText(self, "新建任务", "文件名(不含扩展名):")
        if not ok2:
            return
        CUSTOM_MISSIONS_DIR.mkdir(parents=True, exist_ok=True)
        path = CUSTOM_MISSIONS_DIR / f"{(fname or 'new_mission').strip()}.json"
        # 最小可编辑结构
        data = {
            "title": (title or "New Mission").strip() or "New Mission",
            "listmission": True,
            "addtitleinlist": True,
            "addtitleinpanel": True,
            "zones": [],
            "subconditions": [],
            "checkpoints": [],
        }
        try:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "创建失败", str(e))
            return
        self._open_file(path)

    def _display_group_name(self, stage: Optional[str]) -> str:
        if not stage:
            return "其他"
        m: Dict[str, str] = {
            "Alley": "小巷Alley",
            "Apartment": "公寓Apartment",
            "Convenience": "便利店Convenience",
            "Downtown": "市中心Downtown",
            "Mall": "商场Mall",
            "Park": "公园Park",
            "Residential": "住宅Residential",
            "Shop": "商店Shop",
            "Toilet": "厕所Toilet",
        }
        return m.get(stage, stage)

    def _populate_tree(self) -> None:
        # 使用与 Mod 管理相同的分组逻辑（但无复选框）
        from src.mod_manager import scan_mods
        self.tree.clear()
        CUSTOM_MISSIONS_DIR.mkdir(parents=True, exist_ok=True)

        # 组：传送门、各 stage、其他
        groups: Dict[str, QtWidgets.QTreeWidgetItem] = {}
        warp_group = QtWidgets.QTreeWidgetItem(["传送门", ""])
        warp_group.setFlags(warp_group.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable)
        groups["__warp__"] = warp_group
        self.tree.addTopLevelItem(warp_group)

        # 普通分组
        mods = scan_mods()
        stage_groups: Dict[str, QtWidgets.QTreeWidgetItem] = {}
        others_group = QtWidgets.QTreeWidgetItem(["其他", ""])
        others_group.setFlags(others_group.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable)

        for m in mods:
            if m.is_warp:
                parent = warp_group
            elif m.stage:
                key = m.stage
                if key not in stage_groups:
                    gname = self._display_group_name(key)
                    grp = QtWidgets.QTreeWidgetItem([gname, ""])
                    grp.setFlags(grp.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable)
                    stage_groups[key] = grp
                    self.tree.addTopLevelItem(grp)
                parent = stage_groups[key]
            else:
                parent = others_group

            leaf = QtWidgets.QTreeWidgetItem([m.path.name, m.name or ""])
            leaf.setData(0, QtCore.Qt.ItemDataRole.UserRole, str(m.path))
            leaf.setData(0, QtCore.Qt.ItemDataRole.UserRole + 1, m.name or "")
            parent.addChild(leaf)

        if others_group.childCount() > 0:
            self.tree.addTopLevelItem(others_group)
        self.tree.expandAll()

    def _open_file(self, path: Path) -> None:
        # 若已打开相同文件，则切换到该标签
        for i, pth in list(self._path_map.items()):
            if pth and Path(pth) == Path(path):
                self.tab_editors.setCurrentIndex(i)
                self._update_action_states()
                return
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError:
            return
        page = self._create_editor_tab()
        editor: CodeEditor = page.property("editor")
        editor.setPlainText(text)
        editor.validationReady.connect(self._update_errors)
        editor.validationReady.connect(self._maybe_refresh_preview)
        idx = self.tab_editors.addTab(page, path.name)
        self.tab_editors.setCurrentIndex(idx)
        self._path_map[idx] = path
        self._dirty_map[idx] = False
        self._update_saved_label(idx)
        self._update_action_states()

    def _action_save(self) -> None:
        idx = self.tab_editors.currentIndex()
        if idx < 0:
            return
        path: Optional[Path] = self._path_map.get(idx)
        if path is None:
            return self._action_save_as()
        self._save_to_path(idx, path)
        self._update_action_states()

    def _action_save_as(self) -> None:
        idx = self.tab_editors.currentIndex()
        if idx < 0:
            return
        file, _ = QtWidgets.QFileDialog.getSaveFileName(self, "另存为", str(CUSTOM_MISSIONS_DIR), "JSON Files (*.json)")
        if not file:
            return
        path = Path(file)
        self._path_map[idx] = path
        self.tab_editors.setTabText(idx, path.name)
        self._save_to_path(idx, path)

    def _save_to_path(self, idx: int, path: Path) -> None:
        page = self.tab_editors.widget(idx)
        editor: CodeEditor = page.property("editor")
        text = editor.toPlainText()
        try:
            json.loads(text)
            path.write_text(text, encoding="utf-8")
            self._dirty_map[idx] = False
            self._update_saved_label(idx)
        except Exception:
            self.lbl_saved.setText("未保存（解析失败）")

    def _close_tab(self, idx: int) -> None:
        # 仅在脏时提示保存；已命名直接保存，未命名给出选择
        self.tab_editors.setCurrentIndex(idx)
        dirty = self._dirty_map.get(idx, False)
        path: Optional[Path] = self._path_map.get(idx)
        if dirty:
            if path is not None:
                ret = QtWidgets.QMessageBox.question(
                    self, "保存更改", f"保存对 {path.name} 的更改？",
                    QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No | QtWidgets.QMessageBox.StandardButton.Cancel)
                if ret == QtWidgets.QMessageBox.StandardButton.Cancel:
                    return
                if ret == QtWidgets.QMessageBox.StandardButton.Yes:
                    self._save_to_path(idx, path)
            else:
                ret = QtWidgets.QMessageBox.question(
                    self, "保存更改", "保存未命名文件？",
                    QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No | QtWidgets.QMessageBox.StandardButton.Cancel)
                if ret == QtWidgets.QMessageBox.StandardButton.Cancel:
                    return
                if ret == QtWidgets.QMessageBox.StandardButton.Yes:
                    before = self._path_map.get(idx)
                    self._action_save_as()
                    after = self._path_map.get(idx)
                    # 如果用户取消另存为，则不关闭
                    if before is after and before is None:
                        return
        self.tab_editors.removeTab(idx)
        self._dirty_map.pop(idx, None)
        self._path_map.pop(idx, None)

    def _on_text_changed(self) -> None:
        ed = self._current_editor()
        if ed:
            self._on_editor_text_changed(ed)

    def _update_saved_label(self, idx: int) -> None:
        dirty = self._dirty_map.get(idx, False)
        self.lbl_saved.setText("未保存" if dirty else "已保存")

    # 右侧文件浏览折叠
    def _toggle_browser(self, checked: bool) -> None:
        # 控制右侧文件浏览显示；展开/收起时同步调整 splitter 面板尺寸
        right_panel = None
        try:
            right_panel = self._splitter.widget(2)
        except Exception:
            pass
        self.btn_mid_toggle.setText("收\n起" if checked else "展\n开")
        if checked:
            if right_panel:
                right_panel.setVisible(True)
            try:
                # 确保内部浏览容器也显示
                self.browser_container.setVisible(True)
            except Exception:
                pass
            try:
                self._splitter.setSizes([240, 640, 300])
            except Exception:
                pass
        else:
            try:
                sizes = self._splitter.sizes()
                total = sum(sizes) if sizes else 1000
                # 将第三列收为 0，前两列按比例分配
                self._splitter.setSizes([int(total * 0.3), int(total * 0.7), 0])
            except Exception:
                pass
            if right_panel:
                right_panel.setVisible(False)
            try:
                self.browser_container.setVisible(False)
            except Exception:
                pass

    def _on_editor_text_changed(self, editor: CodeEditor) -> None:
        # 根据触发的编辑器定位其所属标签索引，避免新建标签 setPlainText 期间把其他页标记为脏
        idx = -1
        for i in range(self.tab_editors.count()):
            page = self.tab_editors.widget(i)
            if page and page.property("editor") is editor:
                idx = i
                break
        if idx >= 0:
            self._dirty_map[idx] = True
            self._update_saved_label(idx)

    def _on_preview_item_double_clicked(self, item: QtWidgets.QTreeWidgetItem) -> None:
        # 双击预览块：跳转并高亮该块文本（优先括号范围，其次子串）
        ed = self._current_editor()
        if not ed:
            return
        text = item.data(0, QtCore.Qt.ItemDataRole.UserRole + 1)
        line = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        found = False
        if isinstance(text, str) and text:
            doc_text = ed.toPlainText()
            start = doc_text.find(text)
            if start < 0:
                anchor = item.data(0, QtCore.Qt.ItemDataRole.UserRole + 2)
                if isinstance(anchor, str) and anchor:
                    # 允许冒号两侧任意空白的锚点匹配（id/description）
                    try:
                        import re
                        m = re.match(r'\s*"([^\"]+)"\s*:\s*"(.*)"\s*$', anchor)
                        if m:
                            k, v = m.group(1), m.group(2)
                            pat = rf'"{re.escape(k)}"\s*:\s*"{re.escape(v)}"'
                            rm = re.search(pat, doc_text)
                            if rm:
                                start = rm.start()
                        if start < 0:
                            # 后备：直接子串查找（万一完全一致）
                            idx2 = doc_text.find(anchor)
                            if idx2 >= 0:
                                start = idx2
                    except Exception:
                        pass
            if start < 0:
                key = item.data(0, QtCore.Qt.ItemDataRole.UserRole + 3)
                idx = item.data(0, QtCore.Qt.ItemDataRole.UserRole + 4)
                if isinstance(key, str) and isinstance(idx, int):
                    s2, e2 = self._locate_array_element(doc_text, key, idx)
                    if s2 is not None and e2 is not None:
                        start = s2
                        text = doc_text[s2:e2]
            if start >= 0:
                s, e = self._find_enclosing_braces(doc_text, start)
                if s is None or e is None:
                    s = start
                    e = start + len(text)
                cur = ed.textCursor()
                cur.setPosition(s)
                cur.setPosition(e, QtGui.QTextCursor.MoveMode.KeepAnchor)
                ed.setTextCursor(cur)
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
                found = True
        if not found and isinstance(line, int) and line > 0:
            self._goto_line(line)

    def _apply_browser_filter(self, _text: str) -> None:
        q = (self.search_box.text() or "").lower().strip()
        def filter_item(item: QtWidgets.QTreeWidgetItem) -> bool:
            is_leaf = item.childCount() == 0 and item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if is_leaf:
                fname = item.text(0).lower()
                title = str(item.data(0, QtCore.Qt.ItemDataRole.UserRole + 1) or "").lower()
                visible = True if not q else (q in fname or q in title)
                item.setHidden(not visible)
                return visible
            any_child_visible = False
            for j in range(item.childCount()):
                if filter_item(item.child(j)):
                    any_child_visible = True
            item.setHidden(not any_child_visible)
            return any_child_visible
        for i in range(self.tree.topLevelItemCount()):
            filter_item(self.tree.topLevelItem(i))
        self.tree.expandAll()

    # 错误面板交互
    def _update_errors(self, issues: List[ValidationIssue]) -> None:
        self.err_list.clear()
        for it in issues:
            line = f"(行 {it.line}) " if it.line else ""
            item = QtWidgets.QListWidgetItem(f"[{it.kind}] {line}{it.message}")
            item.setData(QtCore.Qt.ItemDataRole.UserRole, int(it.line) if it.line else None)
            self.err_list.addItem(item)
        # 同时执行括号/引号检查并把错误附加到列表
        self._check_brackets_and_quotes()
        # 根据是否有错误，自动展开/收起错误面板
        has_errors = self.err_list.count() > 0
        self._set_error_panel_visible(has_errors)
        # 若有错误，记忆展开高度不在这里更新（由用户拖拽时改变）

    def _set_error_panel_visible(self, show: bool) -> None:
        # 使用垂直分割器的尺寸来控制错误面板高度
        try:
            sizes = self._v_splitter.sizes()
            if not sizes or len(sizes) < 2:
                return
            total = sum(sizes)
            # 当前错误面板高度
            cur_err_h = sizes[1]
            if show:
                if cur_err_h == 0:
                    err_h = max(80, self._error_panel_last_size)
                    self._v_splitter.setSizes([max(1, total - err_h), err_h])
                self._err_container.setVisible(True)
            else:
                # 记录当前高度
                if cur_err_h > 0:
                    self._error_panel_last_size = cur_err_h
                self._v_splitter.setSizes([total, 0])
                self._err_container.setVisible(False)
        except Exception:
            pass

    # 预览重建
    def _maybe_refresh_preview(self, issues: List[ValidationIssue]) -> None:
        if any(it.kind == "syntax" for it in issues):
            return
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        ed = self._current_editor()
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
                # 使用与编辑器相同缩进，便于子串定位，并记录锚点
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
        """尝试用多个候选模式估算所在行：优先锚点，其次完整片段，最后返回 1。"""
        for p in patterns:
            if not p:
                continue
            idx = big.find(p)
            if idx >= 0:
                return big[:idx].count('\n') + 1
        return 1

    def _find_enclosing_braces(self, text: str, pos: int) -> tuple[Optional[int], Optional[int]]:
        """从 pos 向左找到最近的 '{'，然后向右匹配 '}'，考虑字符串与转义。"""
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

    def _find_line_of_substring(self, big: str, small: str) -> int:
        idx = big.find(small)
        if idx < 0:
            return 1
        return big[:idx].count('\n') + 1

    def _goto_line(self, line: int) -> None:
        ed = self._current_editor()
        if not ed:
            return
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

    # 括号与引号检查 + 缩进引导线
    def _check_brackets_and_quotes(self) -> None:
        ed = self._current_editor()
        if not ed:
            return
        text = ed.toPlainText()
        stack = []
        pairs = {')': '(', ']': '[', '}': '{'}
        openings = set(pairs.values())
        closes = set(pairs.keys())
        # 简单引号匹配：不考虑转义的粗略检测
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
        # 高亮问题行
        ed.set_lint_lines([ln for (ln, _msg) in problems])

    # 对外 API：打开空白或指定路径
    def open_blank(self) -> None:
        page = self._create_editor_tab()
        idx = self.tab_editors.addTab(page, f"未命名 {self.tab_editors.count()+1}")
        self.tab_editors.setCurrentIndex(idx)
        self._path_map[idx] = None
        self._dirty_map[idx] = False
        self._update_saved_label(idx)
        try:
            self._update_action_states()
        except Exception:
            pass

    def open_path(self, path: Path) -> None:
        self._open_file(path)

    # 文件树右键菜单
    def _on_tree_menu(self, pos: QtCore.QPoint) -> None:
        item = self.tree.itemAt(pos)
        if item is None:
            return
        menu = QtWidgets.QMenu(self)
        act_open = menu.addAction("打开")
        act_rename = menu.addAction("重命名")
        act_delete = menu.addAction("删除")
        menu.addSeparator()
        act_explorer = menu.addAction("在资源管理器中打开")
        action = menu.exec(self.tree.viewport().mapToGlobal(pos))
        path_str = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not path_str:
            return
        p = Path(path_str)
        if action == act_open:
            self._open_file(p)
        elif action == act_rename:
            new_name, ok = QtWidgets.QInputDialog.getText(self, "重命名", "新文件名:", text=p.name)
            if ok and new_name and new_name != p.name:
                target = p.with_name(new_name)
                try:
                    p.rename(target)
                    self._populate_tree()
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "重命名失败", str(e))
        elif action == act_delete:
            if QtWidgets.QMessageBox.question(self, "删除确认", f"删除 {p.name}？此操作不可撤销。") == QtWidgets.QMessageBox.StandardButton.Yes:
                try:
                    p.unlink()
                    self._populate_tree()
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "删除失败", str(e))
        elif action == act_explorer:
            try:
                QtCore.QProcess.startDetached("explorer", ["/select,", str(p)])
            except Exception:
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(p.parent)))

    # 简易查找/替换
    def _find_text(self) -> None:
        ed = self._current_editor()
        text, ok = QtWidgets.QInputDialog.getText(self, "查找", "内容:")
        if not ok or not text:
            return
        if not ed.find(text):
            cursor = ed.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Start)
            ed.setTextCursor(cursor)
            ed.find(text)

    def _replace_text(self) -> None:
        ed = self._current_editor()
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

    def _update_action_states(self) -> None:
        has_tab = self.tab_editors.count() > 0
        ed = self._current_editor()
        can_undo = bool(ed.document().isUndoAvailable()) if ed else False
        can_redo = bool(ed.document().isRedoAvailable()) if ed else False
        is_dirty = False
        if has_tab:
            idx = self.tab_editors.currentIndex()
            is_dirty = bool(self._dirty_map.get(idx, False))
        # 更新按钮
        self.act_save.setEnabled(has_tab and is_dirty)
        self.act_save_as.setEnabled(has_tab)
        self.act_find.setEnabled(has_tab)
        self.act_replace.setEnabled(has_tab)
        self.act_undo.setEnabled(has_tab and can_undo)
        self.act_redo.setEnabled(has_tab and can_redo)
