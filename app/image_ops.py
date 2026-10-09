"""Lógica de imagem (sem dependência de Qt): listagem, miniaturas,
edição, conversão e renomeação, com mensagens de erro amigáveis."""
from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from PIL import Image, ImageOps, UnidentifiedImageError

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
# Rótulo no app -> extensão gravada
OUTPUT_FORMATS = {"JPEG": ".jpeg", "JPG": ".jpg", "PNG": ".png"}
_PIL_FORMAT = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP", ".bmp": "BMP"}

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
_NAT = re.compile(r"(\d+)")


class ImageError(Exception):
    """Erro com mensagem já pronta para exibir ao usuário."""


class ImageEntry(NamedTuple):
    path: Path
    mtime_ns: int
    size: int


@dataclass
class Preview:
    image: Image.Image  # RGBA reduzido, já com orientação EXIF aplicada
    size: tuple[int, int]  # dimensões reais
    has_alpha: bool
    fmt: str
    file_size: int


# --------------------------------------------------------------------- erros
def _friendly(exc: Exception, name: str, action: str = "abrir") -> str:
    if isinstance(exc, FileNotFoundError):
        return f"O arquivo «{name}» não foi encontrado. Ele pode ter sido movido ou apagado."
    if isinstance(exc, PermissionError):
        return f"Sem permissão para {action} «{name}». Verifique as permissões do arquivo ou da pasta."
    if isinstance(exc, (UnidentifiedImageError, Image.DecompressionBombError)):
        return f"«{name}» parece estar corrompido ou não é uma imagem válida."
    if isinstance(exc, OSError):
        return f"Não foi possível {action} «{name}»: {exc.strerror or exc}"
    return f"Erro inesperado ao {action} «{name}»: {exc}"


def format_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}".replace(".", ",")
        size /= 1024
    return f"{n} B"


# ------------------------------------------------------------------ listagem
def _natural_key(name: str) -> list:
    return [int(t) if t.isdigit() else t.casefold() for t in _NAT.split(name)]


def list_images(folder: Path) -> list[ImageEntry]:
    entries: list[ImageEntry] = []
    try:
        with os.scandir(folder) as it:
            for e in it:
                if e.name.startswith("._"):
                    continue
                p = Path(e.path)
                if p.suffix.lower() not in SUPPORTED_EXTS:
                    continue
                try:
                    if not e.is_file():
                        continue
                    st = e.stat()
                except OSError:
                    continue
                entries.append(ImageEntry(p, st.st_mtime_ns, st.st_size))
    except FileNotFoundError:
        raise ImageError("A pasta não foi encontrada. Ela pode ter sido movida ou apagada.")
    except PermissionError:
        raise ImageError("Sem permissão para ler esta pasta.")
    except OSError as exc:
        raise ImageError(f"Não foi possível ler a pasta: {exc.strerror or exc}")
    entries.sort(key=lambda x: _natural_key(x.path.name))
    return entries


# ----------------------------------------------------------------- leitura
def _has_alpha(img: Image.Image) -> bool:
    return img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info


def make_thumbnail(path: Path, size: int) -> Image.Image:
    """Miniatura RGBA. Para JPEG usa 'draft' (decodificação reduzida, bem mais rápida)."""
    try:
        with Image.open(path) as im:
            if im.format == "JPEG":
                im.draft("RGB", (size * 2, size * 2))
            img = ImageOps.exif_transpose(im)
            if img.mode in ("P", "PA", "1"):
                img = img.convert("RGBA")
            img.thumbnail((size, size), Image.Resampling.BICUBIC)
            return img.convert("RGBA")
    except Exception as exc:
        raise ImageError(_friendly(exc, path.name)) from exc


def load_preview(path: Path, max_side: int = 1400) -> Preview:
    try:
        with Image.open(path) as im:
            fmt = im.format or path.suffix.lstrip(".").upper()
            w, h = im.size
            if im.getexif().get(0x0112, 1) in (5, 6, 7, 8):
                w, h = h, w
            if fmt == "JPEG":
                im.draft("RGB", (max_side, max_side))
            img = ImageOps.exif_transpose(im)
            img.load()
            alpha = _has_alpha(img)
            if img.mode in ("P", "PA", "1"):
                img = img.convert("RGBA")
            img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            img = img.convert("RGBA")
        return Preview(img, (w, h), alpha, fmt, path.stat().st_size)
    except Exception as exc:
        raise ImageError(_friendly(exc, path.name)) from exc


# ------------------------------------------------------------------ edição
def apply_flips(img: Image.Image, flip_h: bool, flip_v: bool) -> Image.Image:
    if flip_h:
        img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if flip_v:
        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return img


def flatten_on_white(img: Image.Image) -> Image.Image:
    """Converte para RGB preenchendo transparência com fundo branco."""
    if img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.getchannel("A"))
        return bg
    return img.convert("RGB")


def _name_taken(folder: Path, name: str, exclude: str | None = None) -> bool:
    try:
        return any(o.casefold() == name.casefold() and o != exclude for o in os.listdir(folder))
    except OSError:
        return False


def save_edited(
    path: Path,
    flip_h: bool,
    flip_v: bool,
    target_ext: str | None = None,
    target_stem: str | None = None,
) -> Path:
    """Aplica as edições e substitui o original. Se a extensão mudar, o arquivo
    antigo é removido e o novo é gravado. Retorna o caminho final."""
    ext = (target_ext or path.suffix).lower()
    if ext not in _PIL_FORMAT:
        raise ImageError(f"Formato não suportado: {ext}")
    stem = (target_stem or path.stem).strip()
    if target_stem is not None:
        err = check_new_stem(stem, path)
        if err:
            raise ImageError(err)
    target = path.with_name(f"{stem}{ext}")
    if target.name != path.name and _name_taken(path.parent, target.name, exclude=path.name):
        raise ImageError(f"Já existe um arquivo chamado «{target.name}» nesta pasta.")

    fmt = _PIL_FORMAT[ext]
    tmp = path.with_name(f".{uuid.uuid4().hex}.tmp")
    try:
        with Image.open(path) as im:
            im.load()
            icc = im.info.get("icc_profile")
            img = ImageOps.exif_transpose(im)
        img = apply_flips(img, flip_h, flip_v)

        params: dict = {}
        if fmt == "JPEG":
            img = flatten_on_white(img)
            params = {"quality": 95, "optimize": True}
        elif fmt == "PNG":
            params = {"optimize": True}
        elif fmt == "WEBP":
            params = {"quality": 95}
        elif fmt == "BMP" and img.mode not in ("RGB", "RGBA", "L", "P", "1"):
            img = img.convert("RGB")
        if icc and fmt in ("JPEG", "PNG", "WEBP"):
            params["icc_profile"] = icc

        img.save(tmp, format=fmt, **params)
        os.replace(tmp, target)
        if os.path.normcase(str(target)) != os.path.normcase(str(path)) and path.exists():
            os.remove(path)
        return target
    except ImageError:
        raise
    except Exception as exc:
        raise ImageError(_friendly(exc, path.name, "salvar")) from exc
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


# -------------------------------------------------------------- renomeação
def check_new_stem(stem: str, path: Path) -> str | None:
    """Valida o novo nome (sem extensão). Retorna a mensagem de erro, ou None se válido."""
    s = stem.strip()
    if not s:
        return "O nome não pode ficar em branco."
    if _INVALID_CHARS.search(s):
        return 'O nome não pode conter: < > : " / \\ | ? *'
    if s.endswith(".") or s in (".", ".."):
        return "O nome não pode terminar com ponto."
    if s.split(".")[0].upper() in _RESERVED:
        return "Esse nome é reservado pelo sistema."
    if len(s) > 200:
        return "O nome é longo demais (máximo de 200 caracteres)."
    if Path(s).suffix.lower() in SUPPORTED_EXTS:
        return "Digite o nome sem a extensão; ela é mantida automaticamente."
    target = s + path.suffix
    if target != path.name and _name_taken(path.parent, target, exclude=path.name):
        return "Já existe um arquivo com esse nome nesta pasta."
    return None


def rename_image(path: Path, stem: str) -> Path:
    err = check_new_stem(stem, path)
    if err:
        raise ImageError(err)
    new = path.with_name(stem.strip() + path.suffix)
    if new == path:
        return path
    try:
        os.rename(path, new)
    except Exception as exc:
        raise ImageError(_friendly(exc, path.name, "renomear")) from exc
    return new
