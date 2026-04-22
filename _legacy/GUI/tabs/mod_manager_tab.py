from PyQt6 import QtCore, QtGui, QtWidgets
from typing import Optional, Dict, List, Tuple

from src.mod_manager import scan_mods, delete_mod
from src.settings_manager import load_settings
from src.game_sync import is_enabled_in_game, enable_mod, disable_mod
from src.config import CUSTOM_MISSIONS_DIR


class ModManagerTab(QtWidgets.QWidget):
    """Mod 管理标签页。
    变更：
    - 左侧列表显示 JSON 内的 title
    - 右侧任务流程描述汇总 checkpoints 内的 description
    - 移除启用/禁用按钮（仅保留列表勾选）
    - 刷新按钮位于任务列表区域右上方
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal, self)

        # 左侧：顶部工具行 + 列表（分组树）
        left_panel = QtWidgets.QWidget(self)
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_toolbar = QtWidgets.QHBoxLayout()
        self.search_edit = QtWidgets.QLineEdit(left_panel)
        self.search_edit.setPlaceholderText("搜索（标题/文件名）…")
        left_toolbar.addWidget(self.search_edit)
        self.btn_select_all = QtWidgets.QPushButton("全选启用", left_panel)
        self.btn_unselect_all = QtWidgets.QPushButton("全不选/禁用", left_panel)
        left_toolbar.addWidget(self.btn_select_all)
        left_toolbar.addWidget(self.btn_unselect_all)
        left_toolbar.addStretch(1)
        self.btn_refresh = QtWidgets.QPushButton("刷新", left_panel)
        left_toolbar.addWidget(self.btn_refresh)
        left_layout.addLayout(left_toolbar)
        self.tree_mods = QtWidgets.QTreeWidget(left_panel)
        # 仅一列展示任务名称；勾选状态仍使用第0列的复选框
        self.tree_mods.setHeaderLabels(["任务"])
        self.tree_mods.setRootIsDecorated(True)
        self.tree_mods.setAlternatingRowColors(True)
        self.tree_mods.itemChanged.connect(self._on_tree_check_changed)
        self.tree_mods.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self.tree_mods.itemDoubleClicked.connect(self._on_tree_double_clicked)
        self._mods_cache = []  # type: List[Tuple[str, str, bool, Optional[str], Optional[str], list[str], Optional[str], bool]]
        left_layout.addWidget(self.tree_mods)
        splitter.addWidget(left_panel)

        # 右侧：详细信息
        right_panel = QtWidgets.QWidget(self)
        form_layout = QtWidgets.QFormLayout(right_panel)
        self.lbl_name = QtWidgets.QLabel("-", right_panel)
        self.lbl_version = QtWidgets.QLabel("-", right_panel)
        self.lbl_author = QtWidgets.QLabel("-", right_panel)
        self.txt_description = QtWidgets.QTextEdit(right_panel)
        self.txt_description.setPlaceholderText("任务流程描述…")
        self.txt_description.setReadOnly(True)
        # 开始条件
        self.txt_start_condition = QtWidgets.QPlainTextEdit(right_panel)
        self.txt_start_condition.setPlaceholderText("开始条件（subconditions[0].condition）…")
        self.txt_start_condition.setReadOnly(True)

        form_layout.addRow("任务名称:", self.lbl_name)
        form_layout.addRow("版本:", self.lbl_version)
        form_layout.addRow("作者:", self.lbl_author)
        form_layout.addRow("任务流程描述:", self.txt_description)
        form_layout.addRow("开始条件:", self.txt_start_condition)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter, 1)

        # 底部状态
        status_frame = QtWidgets.QFrame(self)
        status_frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        status_layout = QtWidgets.QHBoxLayout(status_frame)
        self.lbl_status = QtWidgets.QLabel("Mod 总数: 0 | 启用: 0", status_frame)
        status_layout.addWidget(self.lbl_status)
        status_layout.addStretch(1)
        root.addWidget(status_frame)

        # 交互
        self.search_edit.textChanged.connect(self._render_tree)
        self.btn_refresh.clicked.connect(self._reload_mods)
        self.btn_select_all.clicked.connect(lambda: self._bulk_enable(True))
        self.btn_unselect_all.clicked.connect(lambda: self._bulk_enable(False))
        self.tree_mods.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_mods.customContextMenuRequested.connect(self._show_tree_menu)

        self._reload_mods()

    def _on_tree_selection_changed(self) -> None:
        items = self.tree_mods.selectedItems()
        current = items[0] if items else None
        if current is None or current.data(0, QtCore.Qt.ItemDataRole.UserRole) is None:
            self.lbl_name.setText("-")
            self.lbl_version.setText("-")
            self.lbl_author.setText("-")
            self.txt_description.setPlainText("")
            self.txt_start_condition.setPlainText("")
            return
        title = current.text(0)
        self.lbl_name.setText(title)
        version = current.data(0, QtCore.Qt.ItemDataRole.UserRole + 1) or "-"
        author = current.data(0, QtCore.Qt.ItemDataRole.UserRole + 2) or "-"
        self.lbl_version.setText(str(version))
        self.lbl_author.setText(str(author))
        descs = current.data(0, QtCore.Qt.ItemDataRole.UserRole + 3) or []
        self.txt_description.setPlainText("\n\n".join(descs) if isinstance(descs, list) else "")
        # 开始条件
        fn = current.data(0, QtCore.Qt.ItemDataRole.UserRole)
        try:
            if fn:
                from pathlib import Path
                import json
                p = Path(CUSTOM_MISSIONS_DIR) / fn
                obj = json.loads(p.read_text(encoding="utf-8"))
                start_text = ""
                # 优先：subconditions[0].condition
                scs = obj.get("subconditions")
                if isinstance(scs, list) and scs:
                    first = scs[0]
                    if isinstance(first, dict):
                        cond = first.get("condition")
                        if isinstance(cond, dict):
                            start_text = json.dumps(cond, ensure_ascii=False, indent=2)
                # 回退：第一个 checkpoints[*].condition 或 travelcondition
                if not start_text:
                    cps = obj.get("checkpoints")
                    if isinstance(cps, list):
                        for c in cps:
                            if not isinstance(c, dict):
                                continue
                            for key in ("condition", "travelcondition"):
                                blk = c.get(key)
                                if isinstance(blk, dict):
                                    start_text = json.dumps(blk, ensure_ascii=False, indent=2)
                                    break
                            if start_text:
                                break
                # 仍无：尝试 checkpoints[*] 内 description 作为参考
                if not start_text and isinstance(obj, dict):
                    cps = obj.get("checkpoints")
                    if isinstance(cps, list):
                        for c in cps:
                            if isinstance(c, dict):
                                for key in ("condition", "travelcondition"):
                                    blk = c.get(key)
                                    if isinstance(blk, dict) and isinstance(blk.get("description"), str):
                                        start_text = json.dumps({"description": blk.get("description")}, ensure_ascii=False, indent=2)
                                        break
                            if start_text:
                                break
                self.txt_start_condition.setPlainText(start_text)
        except Exception:
            self.txt_start_condition.setPlainText("")

    def _reload_mods(self) -> None:
        mods = scan_mods()
        self._mods_cache = [(m.path.name, m.name, False, m.version, m.author, m.descriptions, m.stage, m.is_warp) for m in mods]
        # 结合游戏目录状态
        s = load_settings()
        gdir = s.get("gameDir")
        if gdir:
            enabled_set = set()
            try:
                for i, (fn, *_rest) in enumerate(self._mods_cache):
                    if is_enabled_in_game(fn, gdir):
                        enabled_set.add(fn)
                self._mods_cache = [
                    (fn, name, fn in enabled_set, ver, au, descs, stage, is_warp)
                    for (fn, name, _en, ver, au, descs, stage, is_warp) in self._mods_cache
                ]
            except Exception:
                pass
        self._render_tree()
        total = len(mods)
        enabled = sum(1 for _ in filter(lambda x: x[2], self._mods_cache))
        self.lbl_status.setText(f"Mod 总数: {total} | 启用: {enabled}")

    def _render_tree(self) -> None:
        q = (self.search_edit.text() or "").lower().strip()
        self.tree_mods.blockSignals(True)
        self.tree_mods.clear()
        # 分组：传送门、按 stage、其他
        group_warp = QtWidgets.QTreeWidgetItem(["传送门"])
        group_warp.setFlags(group_warp.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
        group_warp.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
        group_map: Dict[str, QtWidgets.QTreeWidgetItem] = {}
        group_other = QtWidgets.QTreeWidgetItem(["其他"])
        group_other.setFlags(group_other.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
        group_other.setCheckState(0, QtCore.Qt.CheckState.Unchecked)

        def matches(text: str, filename: str) -> bool:
            if not q:
                return True
            return q in (text or "").lower() or q in (filename or "").lower()

        for filename, title, enabled, version, author, descs, stage, is_warp in self._mods_cache:
            text = title or filename
            if not matches(text, filename):
                continue
            node = QtWidgets.QTreeWidgetItem([text])
            node.setData(0, QtCore.Qt.ItemDataRole.UserRole, filename)
            node.setData(0, QtCore.Qt.ItemDataRole.UserRole + 1, version)
            node.setData(0, QtCore.Qt.ItemDataRole.UserRole + 2, author)
            node.setData(0, QtCore.Qt.ItemDataRole.UserRole + 3, descs)
            node.setFlags(node.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable | QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
            node.setCheckState(0, QtCore.Qt.CheckState.Checked if enabled else QtCore.Qt.CheckState.Unchecked)
            if is_warp:
                group_warp.addChild(node)
            elif stage:
                grp = group_map.get(stage)
                if not grp:
                    grp = QtWidgets.QTreeWidgetItem([self._display_group_name(stage)])
                    grp.setData(0, QtCore.Qt.ItemDataRole.UserRole + 10, stage)  # 保存原始 stage
                    grp.setFlags(grp.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                    grp.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
                    group_map[stage] = grp
                grp.addChild(node)
            else:
                group_other.addChild(node)

        # 添加到树
        if group_warp.childCount() > 0:
            self.tree_mods.addTopLevelItem(group_warp)
        for stage, grp in sorted(group_map.items(), key=lambda x: x[0].lower()):
            self.tree_mods.addTopLevelItem(grp)
        if group_other.childCount() > 0:
            self.tree_mods.addTopLevelItem(group_other)
        self.tree_mods.expandAll()
        # 渲染后根据子项勾选情况设置分组为三态（全选/部分选/不选）
        self._update_group_states()
        self.tree_mods.blockSignals(False)

    def _display_group_name(self, stage: str) -> str:
        mapping = {
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
        # 仅替换展示，不改动原值
        return mapping.get(stage, stage)

    def _on_tree_check_changed(self, item: QtWidgets.QTreeWidgetItem, _col: int) -> None:
        filename = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        # 若为分组项（无文件名），级联到子节点
        if not filename:
            self._apply_group_check(item)
            return
        want_enabled = item.checkState(0) == QtCore.Qt.CheckState.Checked
        s = load_settings()
        gdir = s.get("gameDir")
        ok = True
        if not gdir:
            QtWidgets.QMessageBox.information(self, "缺少游戏目录", "请先在设置中选择游戏目录。")
            ok = False
        else:
            if want_enabled:
                ok = enable_mod(filename, gdir)
                if not ok:
                    QtWidgets.QMessageBox.warning(self, "启用失败", f"复制 {filename} 到游戏目录失败。")
            else:
                ok = disable_mod(filename, gdir)
                if not ok:
                    QtWidgets.QMessageBox.warning(self, "禁用失败", f"从游戏目录删除 {filename} 失败。")
        if not ok:
            # 还原勾选状态
            item.setCheckState(0, QtCore.Qt.CheckState.Checked if not want_enabled else QtCore.Qt.CheckState.Unchecked)
        # 更新状态计数
        total_nodes = 0
        enabled_count = 0
        def walk(parent: QtWidgets.QTreeWidgetItem | None):
            nonlocal total_nodes, enabled_count
            n = self.tree_mods.topLevelItemCount() if parent is None else parent.childCount()
            for i in range(n):
                it = self.tree_mods.topLevelItem(i) if parent is None else parent.child(i)
                fn = it.data(0, QtCore.Qt.ItemDataRole.UserRole)
                if fn:
                    total_nodes += 1
                    if it.checkState(0) == QtCore.Qt.CheckState.Checked:
                        enabled_count += 1
                walk(it)
        walk(None)
        self.lbl_status.setText(f"Mod 总数: {total_nodes} | 启用: {enabled_count}")
        # 同步分组三态
        self._update_group_states()

    def _apply_group_check(self, group_item: QtWidgets.QTreeWidgetItem) -> None:
        # 分组项勾选/取消，批量应用到其子任务
        want_enabled = group_item.checkState(0) == QtCore.Qt.CheckState.Checked
        s = load_settings()
        gdir = s.get("gameDir")
        if not gdir:
            QtWidgets.QMessageBox.information(self, "缺少游戏目录", "请先在设置中选择游戏目录。")
            # 还原复选
            group_item.setCheckState(0, QtCore.Qt.CheckState.Unchecked if want_enabled else QtCore.Qt.CheckState.Checked)
            return
        self.tree_mods.blockSignals(True)
        try:
            for i in range(group_item.childCount()):
                it = group_item.child(i)
                fn = it.data(0, QtCore.Qt.ItemDataRole.UserRole)
                if not fn:
                    continue
                if want_enabled:
                    enable_mod(fn, gdir)
                    it.setCheckState(0, QtCore.Qt.CheckState.Checked)
                else:
                    disable_mod(fn, gdir)
                    it.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
        finally:
            self.tree_mods.blockSignals(False)
        # 更新分组三态与状态计数（不立即重载树，避免勾选被还原）
        self._update_group_states()
        # 计算状态显示
        total_nodes = 0
        enabled_count = 0
        def walk(parent: QtWidgets.QTreeWidgetItem | None):
            nonlocal total_nodes, enabled_count
            n = self.tree_mods.topLevelItemCount() if parent is None else parent.childCount()
            for i in range(n):
                it = self.tree_mods.topLevelItem(i) if parent is None else parent.child(i)
                fn = it.data(0, QtCore.Qt.ItemDataRole.UserRole)
                if fn:
                    total_nodes += 1
                    if it.checkState(0) == QtCore.Qt.CheckState.Checked:
                        enabled_count += 1
                walk(it)
        walk(None)
        self.lbl_status.setText(f"Mod 总数: {total_nodes} | 启用: {enabled_count}")

    def _update_group_states(self) -> None:
        # 根据子项勾选情况，设置分组复选框为 Checked / PartiallyChecked / Unchecked
        self.tree_mods.blockSignals(True)
        try:
            for i in range(self.tree_mods.topLevelItemCount()):
                grp = self.tree_mods.topLevelItem(i)
                # 跳过没有子节点的顶层
                if grp.childCount() == 0:
                    continue
                # 分组没有文件名数据
                all_checked = True
                any_checked = False
                has_child = False
                for j in range(grp.childCount()):
                    ch = grp.child(j)
                    fn = ch.data(0, QtCore.Qt.ItemDataRole.UserRole)
                    if not fn:
                        continue
                    has_child = True
                    st = ch.checkState(0)
                    if st == QtCore.Qt.CheckState.Checked:
                        any_checked = True
                    else:
                        all_checked = False
                if not has_child:
                    grp.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
                elif all_checked:
                    grp.setCheckState(0, QtCore.Qt.CheckState.Checked)
                elif any_checked:
                    grp.setCheckState(0, QtCore.Qt.CheckState.PartiallyChecked)
                else:
                    grp.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
        finally:
            self.tree_mods.blockSignals(False)

    def _on_tree_double_clicked(self, item: QtWidgets.QTreeWidgetItem, _col: int) -> None:
        fn = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not fn:
            return
        from pathlib import Path
        p = Path(CUSTOM_MISSIONS_DIR) / fn
        # 打开到编辑器页
        w = self.parent()
        while w and not isinstance(w, QtWidgets.QMainWindow):
            w = w.parent()
        if w and hasattr(w, "json_editor_tab"):
            try:
                w.json_editor_tab.open_path(p)
                if hasattr(w, "tab_widget"):
                    w.tab_widget.setCurrentWidget(w.json_editor_tab)
            except Exception:
                pass

    def _bulk_enable(self, enable: bool) -> None:
        # 对可见的所有子项批量操作
        s = load_settings()
        gdir = s.get("gameDir")
        if not gdir:
            QtWidgets.QMessageBox.information(self, "缺少游戏目录", "请先在设置中选择游戏目录。")
            return
        # 遍历
        def walk(parent: QtWidgets.QTreeWidgetItem | None):
            n = self.tree_mods.topLevelItemCount() if parent is None else parent.childCount()
            for i in range(n):
                it = self.tree_mods.topLevelItem(i) if parent is None else parent.child(i)
                fn = it.data(0, QtCore.Qt.ItemDataRole.UserRole)
                if fn:
                    if enable:
                        enable_mod(fn, gdir)
                        it.setCheckState(0, QtCore.Qt.CheckState.Checked)
                    else:
                        disable_mod(fn, gdir)
                        it.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
                walk(it)
        walk(None)
        # 结束后刷新状态
        self._reload_mods()

    def _get_selected_filename(self) -> Optional[str]:
        items = self.tree_mods.selectedItems()
        if not items:
            return None
        return items[0].data(0, QtCore.Qt.ItemDataRole.UserRole)

    # 勾选直接生效；此辅助方法已不需要

    def _delete_selected(self) -> None:
        # 删除当前选中子项对应的本地文件
        items = self.tree_mods.selectedItems()
        if not items:
            return
        cur = items[0]
        filename = cur.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not filename:
            return
        title = cur.text(0)
        ret = QtWidgets.QMessageBox.question(self, "删除确认", f"确认删除任务‘{title}’？")
        if ret != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        if delete_mod(filename):
            self._reload_mods()

    def _add_placeholder(self) -> None:
        target = CUSTOM_MISSIONS_DIR / "new_mission.json"
        if not target.exists():
            target.write_text("{\n  \"title\": \"New Mission\"\n}", encoding="utf-8")
        self._reload_mods()

    def _show_tree_menu(self, pos: QtCore.QPoint) -> None:
        item = self.tree_mods.itemAt(pos)
        if item is None:
            return
        menu = QtWidgets.QMenu(self)
        act_open_loc = menu.addAction("打开任务文件位置")
        act_del = menu.addAction("删除")
        action = menu.exec(self.tree_mods.viewport().mapToGlobal(pos))
        if action == act_open_loc:
            fn = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if fn:
                from pathlib import Path
                p = Path(CUSTOM_MISSIONS_DIR) / fn
                try:
                    QtCore.QProcess.startDetached("explorer", ["/select,", str(p)])
                except Exception:
                    QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(p.parent)))
        elif action == act_del:
            self._delete_selected()
