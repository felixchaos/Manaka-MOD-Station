from PyQt6 import QtWidgets

from GUI.main_window import MainWindow, create_app


def main() -> None:
    app = create_app()
    w = MainWindow()
    w.show()
    app.exec()


if __name__ == "__main__":
    main()
