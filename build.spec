# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 規格檔：PDF 壓縮工具

打包指令：
    pyinstaller build.spec --clean --noconfirm

產出：
    dist/PDF壓縮工具/PDF壓縮工具.exe   (onedir 模式，啟動最快、並行壓縮效率最高)

注意：
    - onedir：整個 dist/PDF壓縮工具/ 資料夾就是可攜的應用程式
    - 不使用 onefile：避免 ProcessPoolExecutor 子程序每次都要解壓 exe（極慢）
"""
from PyInstaller.utils.hooks import collect_all

datas = [("app.ico", ".")]
binaries = []
hiddenimports = []

for _pkg in ("tkinterdnd2", "customtkinter", "pikepdf"):
    _d, _b, _h = collect_all(_pkg)
    datas += _d
    binaries += _b
    hiddenimports += _h

hiddenimports += [
    "pikepdf.models.ctm",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pymupdf",
        "fitz",
        "matplotlib",
        "numpy.tests",
        "PIL.ImageQt",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "tkinter.test",
        "test",
        "unittest",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PDF壓縮工具",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="app.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PDF壓縮工具",
)
