[TECH] PySide6 (Qt for Python 6.10/6.11)
[OBJ] Official Qt 6 bindings for professional native desktop apps — widgets, QML/Qt Quick, Qt Designer, system integration.
[RULES]
1. [REQ] Default to PySide6 over PyQt6: LGPL license permits closed-source apps via standard pip wheels (dynamic linking). PyQt6 = GPL or paid commercial license.
2. [REQ] Widgets vs QML: classic forms/tools → Qt Widgets + QSS; branded/animated/touch UIs → Qt Quick (QML) with PySide6 backend. Don't mix casually — pick per screen.
3. [REQ] Threading: never touch UI objects off the GUI thread. `QThreadPool` + `QRunnable` + custom `Signal`s, or `QThread` subclass with `moveToThread`. Decorate receivers with `@Slot`.
4. [REQ] Model/View: `QAbstractTableModel`/`QAbstractListModel` + `QTableView` + `QSortFilterProxyModel` for any tabular/collection UI; delegates for custom cell rendering; `QTableWidget` only for <100-row trivia.
5. [REQ] Theming: keep palette in one dict; generate QSS from a template string (QSS has no variables); `setStyle("Fusion")` base for cross-platform consistency; `QPalette` for native fallbacks; `QApplication.setPalette` for system-aware colors.
6. [REQ] Persistence: `QSettings(org, app)` for window geometry, splitter states, last paths, theme choice — save on `closeEvent`, restore on startup.
7. [REQ] Product shell: `QSystemTrayIcon` + menu, `QShortcut`/`QKeySequenceEdit` for hotkeys, single-instance via `QLocalServer`/`QLockFile`, `QFileDialog` native dialogs, `QStyleHints.colorScheme` for OS dark-mode detection.
8. [REQ] Layout: layouts only (`QVBoxLayout`/`QGridLayout`/`QFormLayout`) + `QSizePolicy` + spacers — never fixed `setGeometry` for resizable windows; Qt6 handles High-DPI automatically.
9. [REQ] Qt Designer: `.ui` files for complex static forms → `pyside6-uic file.ui -o ui_file.py`; NEVER edit generated files; prefer code for dynamic/data-driven UIs.
10. [REQ] Resources: `pyside6-rcc` to bundle icons/fonts/qml into `*_rc.py`; ship `.qrc` for all assets referenced by name.
11. [REQ] Packaging: Nuitka preferred (`--standalone --onefile --enable-plugins=pyside6`) or PyInstaller (`--windowed --name App`); verify Qt platform plugins (`platforms/qwindows.dll` etc.) included; set .ico + version info; test on clean VM.
12. [REQ] Testing: `pytest-qt` (`qtbot`) for widget tests; `QApplication` fixture pattern; test Model data roles not pixel output.
13. [PROHIBIT] Never `time.sleep`/blocking IO on the main thread — freezes the whole UI.
14. [PROHIBIT] Never call `widget.update()`/paint from worker threads — emit a signal instead.
15. [PROHIBIT] No raw `getattr(obj, "attr_" + name)` dynamic widget lookup soup — keep a typed widget map.
16. [CMD] `pyside6-designer` launch Qt Designer; `pyside6-uic` compile .ui; `pyside6-rcc` compile .qrc; `pyside6-deploy` packaging helper.
[COMPAT]
- Latest: 6.11.2 (Aug 2026); stable line 6.10.x (Oct 2025–Apr 2026). Wheels `cp39-abi3`.
- Pair with Python 3.10–3.14 (repo floor: >=3.10). `shiboken6` version must match exactly.
- Docs: doc.qt.io/qtforpython-6 — Context7 `/qt/qtforpython` when available.
[REFS]
- https://doc.qt.io/qtforpython-6/
- https://www.pythonguis.com/ (PySide6 tutorials, mvc/model-view examples)
