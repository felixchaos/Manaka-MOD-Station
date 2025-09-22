from PyQt6 import QtCore, QtGui, QtWidgets

from .tabs.mod_manager_tab import ModManagerTab
from .tabs.json_editor_tab import JsonEditorTab
from .tabs.json_creator_tab import JsonCreatorTab
from .tabs.settings_tab import SettingsTab
from .tabs.about_tab import AboutTab


class MainWindow(QtWidgets.QMainWindow):
    """主窗口，包含五个标签页。
    仅实现布局和占位控件，后续逐步填充具体功能。
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("SecretFlasherManaka-Mod管理器")
        self.resize(1200, 800)
        self._init_ui()
        # 初始语言/主题从设置读取并应用
        try:
            from src.settings_manager import load_settings
            s = load_settings()
            self.apply_language(s.get("language", "zh-CN"))
            self.apply_theme(s.get("theme", "light"))
        except Exception:
            pass

    def _init_ui(self) -> None:
        # 使用中央的 TabWidget
        self.tab_widget = QtWidgets.QTabWidget(self)
        self.setCentralWidget(self.tab_widget)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.setTabsClosable(False)

        # 添加各个标签页
        self.mod_manager_tab = ModManagerTab(self)
        self.json_editor_tab = JsonEditorTab(self)
        self.json_creator_tab = JsonCreatorTab(self)
        self.settings_tab = SettingsTab(self)
        self.about_tab = AboutTab(self)

        self.tab_widget.addTab(self.mod_manager_tab, "Mod管理")
        self.tab_widget.addTab(self.json_editor_tab, "任务Json编辑")
        self.tab_widget.addTab(self.json_creator_tab, "新任务Json创建")
        self.tab_widget.addTab(self.settings_tab, "设置")
        self.tab_widget.addTab(self.about_tab, "关于")

        # 状态栏
        self.statusBar().showMessage("就绪")

    # 运行时主题切换
    def apply_theme(self, theme: str) -> None:
        app = QtWidgets.QApplication.instance()
        if not app:
            return
        if theme == "dark":
            app.setStyle("Fusion")
            pal = app.palette()
            pal.setColor(pal.ColorRole.Window, QtGui.QColor(53, 53, 53))
            pal.setColor(pal.ColorRole.WindowText, QtGui.QColor(220, 220, 220))
            pal.setColor(pal.ColorRole.Base, QtGui.QColor(35, 35, 35))
            pal.setColor(pal.ColorRole.AlternateBase, QtGui.QColor(53, 53, 53))
            pal.setColor(pal.ColorRole.ToolTipBase, QtGui.QColor(220, 220, 220))
            pal.setColor(pal.ColorRole.ToolTipText, QtGui.QColor(220, 220, 220))
            pal.setColor(pal.ColorRole.Text, QtGui.QColor(220, 220, 220))
            pal.setColor(pal.ColorRole.Button, QtGui.QColor(53, 53, 53))
            pal.setColor(pal.ColorRole.ButtonText, QtGui.QColor(220, 220, 220))
            pal.setColor(pal.ColorRole.BrightText, QtGui.QColor(255, 0, 0))
            pal.setColor(pal.ColorRole.Highlight, QtGui.QColor(142, 45, 197).lighter())
            pal.setColor(pal.ColorRole.HighlightedText, QtGui.QColor(0, 0, 0))
            app.setPalette(pal)
        elif theme == "light":
            app.setStyle("Fusion")
            app.setPalette(app.style().standardPalette())
        else:
            # system 默认
            app.setPalette(QtWidgets.QApplication.style().standardPalette())

    # 运行时语言切换（简易手动翻译）
    def apply_language(self, lang: str) -> None:
        # Tab 标题
        if lang == "en-US":
            self.tab_widget.setTabText(0, "Mods")
            self.tab_widget.setTabText(1, "JSON Editor")
            self.tab_widget.setTabText(2, "New Mission")
            self.tab_widget.setTabText(3, "Settings")
            self.tab_widget.setTabText(4, "About")
            self.statusBar().showMessage("Ready")
            self.setWindowTitle("SecretFlasherManaka - Mod Manager")
        else:
            self.tab_widget.setTabText(0, "Mod管理")
            self.tab_widget.setTabText(1, "任务Json编辑")
            self.tab_widget.setTabText(2, "新任务Json创建")
            self.tab_widget.setTabText(3, "设置")
            self.tab_widget.setTabText(4, "关于")
            self.statusBar().showMessage("就绪")
            self.setWindowTitle("SecretFlasherManaka-Mod管理器")
        # 允许各页自行刷新文案 — 更鲁棒的实现：遍历 tab_widget 中的实际页面并调用 retranslate
        if hasattr(self, "tab_widget") and self.tab_widget is not None:
            try:
                for i in range(self.tab_widget.count()):
                    tab = self.tab_widget.widget(i)
                    if hasattr(tab, "retranslate"):
                        try:
                            tab.retranslate(lang)
                        except Exception:
                            # 单页面重译失败不影响其它页面
                            pass
            except Exception:
                # 保底：若遍历失败，则忽略，避免抛出到调用方
                pass


def create_app() -> QtWidgets.QApplication:
    import sys
    app = QtWidgets.QApplication(sys.argv)
    # 可在此设置全局外观，如浅色/深色等
    app.setOrganizationName("Practice")
    app.setApplicationName("Practice GUI")
    # 主题将在 MainWindow 构造后应用
    return app
