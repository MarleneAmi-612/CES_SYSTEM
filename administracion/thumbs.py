from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile
from django.conf import settings
import json

def _load_font(px: int):
    try:
        font_path = Path(settings.BASE_DIR) / "CES_SYSTEM" / "static" / "fonts" / "Inter.ttf"
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size=px)
    except Exception:
        pass
    return ImageFont.load_default()

def _fs_path_from_url(url: str) -> Path | None:
    if not url:
        return None
    try:
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https"):
            return None
        p = Path(parsed.path)

        if str(p).startswith("/static/"):
            if getattr(settings, "STATIC_ROOT", None):
                cand = Path(settings.STATIC_ROOT) / str(p).replace("/static/", "")
                if cand.exists():
                    return cand
            cand = Path(settings.BASE_DIR) / "CES_SYSTEM" / "static" / str(p).replace("/static/", "")
            if cand.exists():
                return cand

        media_url = getattr(settings, "MEDIA_URL", "/media/")
        if str(p).startswith(media_url):
            root = getattr(settings, "MEDIA_ROOT", None)
            if root:
                cand = Path(root) / str(p).replace(media_url, "")
                if cand.exists():
                    return cand

        base = Path(settings.BASE_DIR) / "CES_SYSTEM"
        cand = base / p.relative_to("/")
        if cand.exists():
            return cand
    except Exception:
        return None
    return None

def render_thumb_from_json(data: dict, out_w: int = 640) -> Image.Image:
    page = (data.get("pages") or [{}])[0] if isinstance(data.get("pages"), list) else {}
    pw = int(page.get("width") or 1280)
    ph = int(page.get("height") or 720)
    bg = page.get("background") or "#ffffff"

    scale = out_w / pw
    out_h = int(round(out_w * (ph / pw)))
    img = Image.new("RGB", (out_w, out_h), bg)
    draw = ImageDraw.Draw(img)
    font_cache = {}

    for l in (page.get("layers") or [])[:150]:
        t = l.get("type")
        if t == "rect":
            x, y = int((l.get("x") or 0) * scale), int((l.get("y") or 0) * scale)
            w, h = int((l.get("w") or 0) * scale), int((l.get("h") or 0) * scale)
            fill = l.get("fill") or "#e5e7eb"
            draw.rectangle([x, y, x + w, y + h], fill=fill)
        elif t == "text":
            fs = max(10, int((l.get("fontSize") or 18) * scale))
            if fs not in font_cache:
                font_cache[fs] = _load_font(fs)
            font = font_cache[fs]
            txt = str(l.get("text") or "").replace("{{", "▢").replace("}}", "")
            x, y = int((l.get("x") or 0) * scale), int((l.get("y") or 0) * scale)
            fill = l.get("fill") or "#111111"
            draw.text((x, y), txt, font=font, fill=fill)
        elif t == "image":
            fp = _fs_path_from_url(l.get("url"))
            if fp and fp.exists():
                try:
                    im = Image.open(fp).convert("RGBA")
                    w = int(((l.get("w") or im.width) * scale))
                    h = int(((l.get("h") or im.height) * scale))
                    im = im.resize((w, h))
                    x, y = int((l.get("x") or 0) * scale), int((l.get("y") or 0) * scale)
                    img.paste(im, (x, y), im if im.mode == "RGBA" else None)
                except Exception:
                    continue
    return img

def save_thumb(instance, *, force: bool = False, out_w: int = 640) -> bool:
    """Genera y guarda PNG en instance.thumb desde instance.json_active.
    No pisa una miniatura manual salvo force=True."""
    try:
        if instance.thumb and not force:
            return False
        data = instance.json_active or {}
        if isinstance(data, str):
            data = json.loads(data)
        im = render_thumb_from_json(data, out_w=out_w)
        buf = BytesIO()
        im.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        fname = f"tpl_{instance.pk or 'new'}_thumb.png"
        instance.thumb.save(fname, ContentFile(buf.read()), save=False)
        return True
    except Exception:
        return False
