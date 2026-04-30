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
    - contents_directory='.'：所有 DLL 放在 exe 旁，避免 _internal 路徑下 python3XX.dll 載入失敗
"""
import sys, os
from PyInstaller.utils.hooks import collect_all

datas = [("app.ico", ".")]

# python3.dll（stable ABI）需與 exe 同層，否則某些 Windows 環境 LoadLibrary 失敗
_py_dir = sys.base_prefix
binaries = []
for _dll in ("python3.dll", "python313.dll"):
    _p = os.path.join(_py_dir, _dll)
    if os.path.exists(_p):
        binaries.append((_p, "."))

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

splash = Splash(
    "splash.png",
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
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
    splash.binaries,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PDF壓縮工具",
)
