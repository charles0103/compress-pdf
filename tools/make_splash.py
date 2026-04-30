"""產生 splash.png — PyInstaller 啟動畫面。

執行：python tools/make_splash.py
輸出：splash.png（480x300，深色背景 + 青藍主題，與 app.ico 風格一致）
"""
import os
from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 480, 300

CYAN = (0, 209, 255, 255)
CYAN_DIM = (0, 168, 204, 255)
BG_TOP = (13, 28, 38, 255)
BG_BOTTOM = (8, 18, 26, 255)
WHITE = (240, 248, 255, 255)
GRAY = (140, 160, 175, 255)


def _try_font(size: int, bold: bool = True, cjk: bool = False) -> ImageFont.ImageFont:
    if cjk:
        candidates = [
            r"C:\Windows\Fonts\msjhbd.ttc" if bold else r"C:\Windows\Fonts\msjh.ttc",
            r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\simhei.ttf",
        ]
    else:
        candidates = [
            r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _vertical_gradient(w: int, h: int, top: tuple, bottom: tuple) -> Image.Image:
    img = Image.new("RGBA", (w, h), top)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        d.line([(0, y), (w, y)], fill=(r, g, b, 255))
    return img


def render() -> Image.Image:
    img = _vertical_gradient(WIDTH, HEIGHT, BG_TOP, BG_BOTTOM)
    d = ImageDraw.Draw(img)

    # 邊框
    d.rectangle((0, 0, WIDTH - 1, HEIGHT - 1), outline=CYAN, width=2)

    # 主標題「PDF 壓縮工具」
    title = "PDF 壓縮工具"
    title_font = _try_font(36, bold=True, cjk=True)
    bbox = d.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    tx = (WIDTH - tw) // 2 - bbox[0]
    ty = 80
    d.text((tx, ty), title, fill=WHITE, font=title_font)

    # 副標題
    subtitle = "PDF Compression Tool"
    sub_font = _try_font(14, bold=False)
    sbbox = d.textbbox((0, 0), subtitle, font=sub_font)
    sw = sbbox[2] - sbbox[0]
    sx = (WIDTH - sw) // 2 - sbbox[0]
    sy = ty + 50
    d.text((sx, sy), subtitle, fill=CYAN_DIM, font=sub_font)

    # 中央分隔線
    d.line([(WIDTH // 2 - 60, sy + 36), (WIDTH // 2 + 60, sy + 36)], fill=CYAN, width=2)

    # 載入提示
    loading = "載入中，請稍候..."
    load_font = _try_font(13, bold=False, cjk=True)
    lbbox = d.textbbox((0, 0), loading, font=load_font)
    lw = lbbox[2] - lbbox[0]
    lx = (WIDTH - lw) // 2 - lbbox[0]
    ly = sy + 60
    d.text((lx, ly), loading, fill=GRAY, font=load_font)

    # 右下角公司名稱
    publisher = "FU RONG DEVELOPMENT"
    pub_font = _try_font(10, bold=False)
    pbbox = d.textbbox((0, 0), publisher, font=pub_font)
    pw = pbbox[2] - pbbox[0]
    d.text((WIDTH - pw - 16, HEIGHT - 24), publisher, fill=GRAY, font=pub_font)

    return img


def main() -> None:
    out_path = os.path.join(os.path.dirname(__file__), "..", "splash.png")
    out_path = os.path.normpath(out_path)
    img = render()
    img.save(out_path, format="PNG")
    print(f"OK -> {out_path}  ({WIDTH}x{HEIGHT})")


if __name__ == "__main__":
    main()
