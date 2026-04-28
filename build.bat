@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo ========================================
echo  PDF 壓縮工具 - 打包流程
echo ========================================
echo.

where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [1/3] 安裝 PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [錯誤] PyInstaller 安裝失敗
        pause
        exit /b 1
    )
) else (
    echo [1/3] PyInstaller 已安裝
)
echo.

echo [2/3] 確認專案依賴...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo [錯誤] 依賴安裝失敗
    pause
    exit /b 1
)
echo.

echo [3/3] 開始打包...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
pyinstaller build.spec --clean --noconfirm
if errorlevel 1 (
    echo [錯誤] 打包失敗
    pause
    exit /b 1
)
echo.

echo ========================================
echo  完成！
echo ========================================
echo  輸出：dist\PDF壓縮工具\PDF壓縮工具.exe
echo ========================================
pause
