from PyQt6 import QtCore, QtGui, QtWidgets
from datetime import datetime
import webbrowser

from src.update_checker import check_for_updates_github


class AboutTab(QtWidgets.QWidget):
    """关于标签页（布局与占位控件）。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        title = QtWidgets.QLabel("Practice - 任务与Mod管理器", self)
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        root.addWidget(title)

        info = QtWidgets.QLabel(
            "版本：1.0.3\n作者：FelixChaos\n版权：© 2025 Manaka-MOD-Station", self
        )
        info.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        root.addWidget(info)

        link_layout = QtWidgets.QHBoxLayout()
        btn_check_update = QtWidgets.QPushButton("检查更新", self)
        btn_home = QtWidgets.QPushButton("官方网站", self)
        btn_forum = QtWidgets.QPushButton("支持论坛", self)
        link_layout.addWidget(btn_check_update)
        link_layout.addWidget(btn_home)
        link_layout.addWidget(btn_forum)
        link_layout.addStretch(1)
        root.addLayout(link_layout)

        # 绑定按钮信号
        btn_check_update.clicked.connect(self._check_update)
        btn_home.clicked.connect(self._open_homepage)
        btn_forum.clicked.connect(self._open_forum)

        root.addStretch(1)

        # 底部状态栏
        bottom = QtWidgets.QFrame(self)
        bottom.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        b = QtWidgets.QHBoxLayout(bottom)
        self.lbl_version = QtWidgets.QLabel("当前版本：1.0.3", bottom)
        self.lbl_last_check = QtWidgets.QLabel("最后检查：从未", bottom)
        b.addWidget(self.lbl_version)
        b.addStretch(1)
        b.addWidget(self.lbl_last_check)
        root.addWidget(bottom)


    def _check_update(self) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_last_check.setText(f"最后检查：{now}")
        # 从界面读取当前版本号（期望格式：x.y.z）
        cur_text = self.lbl_version.text().strip()
        # 尝试提取版本号
        cur_ver = "0.0.0"
        try:
            if ":" in cur_text:
                cur_ver = cur_text.split(":", 1)[1].strip()
            else:
                cur_ver = cur_text
        except Exception:
            cur_ver = "0.0.0"

        # 查询 GitHub releases latest
        repo = "felixchaos/Manaka-MOD-Station"
        try:
            res = check_for_updates_github(repo, cur_ver)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "检查更新失败", f"无法检查更新：{e}")
            return

        if not res.get("update_available"):
            QtWidgets.QMessageBox.information(self, "已是最新", f"当前版本 {cur_ver} 已经是最新。")
            return

        latest = res.get("latest_version") or "?"
        assets = res.get("assets", [])

        # 构建消息并提供打开 Releases 页或打开第一个资产下载链接
        msg = f"检测到新版本：{latest}\n当前版本：{cur_ver}\n\n请选择操作："
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("发现新版本")
        dlg.setText(msg)
        open_releases = dlg.addButton("打开 Releases 页面", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        if assets:
            open_asset = dlg.addButton(f"下载：{assets[0]['name']}", QtWidgets.QMessageBox.ButtonRole.ActionRole)
        cancel = dlg.addButton(QtWidgets.QMessageBox.StandardButton.Cancel)
        dlg.exec()

        clicked = dlg.clickedButton()
        if clicked == open_releases:
            webbrowser.open(f"https://github.com/{repo}/releases/latest")
        elif assets and clicked == open_asset:
            # 打开第一个资产下载链接
            try:
                url = assets[0]['url']
                webbrowser.open(url)
            except Exception:
                webbrowser.open(f"https://github.com/{repo}/releases/latest")

    def _open_homepage(self) -> None:
        webbrowser.open("https://github.com/felixchaos/Manaka-MOD-Station")

    def _open_forum(self) -> None:
        # 暂时将支持论坛按钮指向 issues 页面
        webbrowser.open("https://github.com/felixchaos/Manaka-MOD-Station/issues")
