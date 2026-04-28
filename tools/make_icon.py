"""產生 app.ico（多解析度）— PDF 壓縮工具。

執行：python tools/make_icon.py
輸出：app.ico（含 16/24/32/48/64/128/256 各尺寸）
"""
import os
from PIL import Image, ImageDraw, ImageFont


CYAN = (0, 209, 255, 255)
CYAN_DIM = (0, 168, 204, 255)
BG_DARK = (10, 18, 26, 255)
BG_LIGHT = (22, 48, 64, 255)
WHITE = (255, 255, 255, 255)


def _try_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\seguibl.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 圓角方形背景（深色）
    radius = max(2, size // 6)
    d.rounded_rectangle(
        (1, 1, size - 2, size - 2),
        radius=radius,
        fill=BG_DARK,
        outline=CYAN,
        width=max(1, size // 64),
    )

    # 內部漸層感（再畫一層稍亮的圓角矩形作 highlight）
    inner_pad = max(2, size // 14)
    d.rounded_rectangle(
        (inner_pad, inner_pad, size - inner_pad - 1, size - inner_pad - 1),
        radius=max(1, radius - inner_pad // 2),
        fill=BG_LIGHT,
    )

    # 「PDF」文字
    text = "PDF"
    font_size = max(8, int(size * 0.36))
    font = _try_font(font_size)
    bbox = d.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = int(size * 0.22) - bbox[1]
    d.text((tx, ty), text, fill=WHITE, font=font)

    # 壓縮箭頭：兩條向中央夾擠的粗線（▼ 上、▲ 下）
    cx = size // 2
    arrow_y = int(size * 0.72)
    arrow_w = int(size * 0.38)
    arrow_h = max(2, int(size * 0.10))
    line_w = max(2, size // 22)

    # 上箭頭 ▼
    d.line(
        [(cx - arrow_w // 2, arrow_y - arrow_h),
         (cx, arrow_y),
         (cx + arrow_w // 2, arrow_y - arrow_h)],
        fill=CYAN, width=line_w, joint="curve",
    )
    # 下箭頭 ▲
    d.line(
        [(cx - arrow_w // 2, arrow_y + arrow_h * 2),
         (cx, arrow_y + arrow_h),
         (cx + arrow_w // 2, arrow_y + arrow_h * 2)],
        fill=CYAN, width=line_w, joint="curve",
    )

    # 中央橫線（被夾擠的物體）
    bar_w = int(size * 0.30)
    bar_h = max(1, size // 32)
    d.rectangle(
        (cx - bar_w // 2, arrow_y + arrow_h - bar_h // 2 - bar_h,
         cx + bar_w // 2, arrow_y + arrow_h - bar_h // 2),
        fill=CYAN_DIM,
    )

    return img


def main() -> None:
    out_path = os.path.join(os.path.dirname(__file__), "..", "app.ico")
    out_path = os.path.normpath(out_path)

    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [render(s) for s in sizes]
    images[0].save(
        out_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )

    # 也輸出大張 PNG 作預覽
    preview_path = os.path.join(os.path.dirname(out_path), "app_icon_preview.png")
    render(512).save(preview_path, format="PNG")

    print(f"OK -> {out_path}")
    print(f"預覽 -> {preview_path}")


if __name__ == "__main__":
    main()
