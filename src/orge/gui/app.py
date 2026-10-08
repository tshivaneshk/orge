"""
orge.gui.app - Application Entry Point
Initializes high-DPI scaling, forces native Windows titlebar to light mode (disables DWM dark mode),
builds QApplication with light-only design system, and launches MainWindowShell.
"""
import sys
import ctypes
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from orge.gui.shell import MainWindowShell

# Backwards compatibility alias for test suites and scripts
OrgeGUI = MainWindowShell

def force_light_titlebar(hwnd: int):
    """
    Forces the Windows Desktop Window Manager (DWM) title bar to Light mode
    by clearing DWMWA_USE_IMMERSIVE_DARK_MODE (attribute 20 or 19).
    """
    if sys.platform != "win32":
        return
    try:
        dwm = ctypes.windll.dwmapi
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 11 / Windows 10 20H1+), 19 on earlier builds
        value = ctypes.c_int(0)  # 0 = Light mode
        for attr in (20, 19):
            dwm.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                ctypes.c_uint(attr),
                ctypes.byref(value),
                ctypes.sizeof(value)
            )
    except Exception:
        pass

def main():
    # Enable high-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("ORGE")
    app.setOrganizationName("ORGE")

    window = MainWindowShell()
    window.show()

    # Apply Windows native light title bar
    force_light_titlebar(int(window.winId()))

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
