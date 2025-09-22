from PyQt6 import QtCore, QtGui, QtWidgets
from datetime import datetime


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
            "版本：0.1.0\n作者：Practice Team\n版权：© 2025 Practice", self
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

        root.addStretch(1)

        # 底部状态栏
        bottom = QtWidgets.QFrame(self)
        bottom.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        b = QtWidgets.QHBoxLayout(bottom)
        self.lbl_version = QtWidgets.QLabel("当前版本：0.1.0", bottom)
        self.lbl_last_check = QtWidgets.QLabel("最后检查：从未", bottom)
        b.addWidget(self.lbl_version)
        b.addStretch(1)
        b.addWidget(self.lbl_last_check)
        root.addWidget(bottom)

        # 信号：占位检查更新
        btn_check_update.clicked.connect(self._check_update)

    def _check_update(self) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_last_check.setText(f"最后检查：{now}")
