from typing import List
from pathlib import Path
import re

from PIL import Image


def fld2pdf(folder: Path, out: str):
    
    files = [file for file in folder.glob(r'*') if re.match(r'.*\.(jpg|png|jpeg|webp)', file.name)]
    files.sort(key=lambda x: x.name)
    pdf = folder / f'{out}.pdf'
    img2pdf(files, pdf)
    return pdf


def new_img(path: Path) -> Image.Image:
    img = Image.open(path)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    return img


def img2pdf(files: List[Path], out: Path):
    im0: Image.Image = new_img(files[0])
    img_list = [new_img(img) for img in files[1:]]
    im0.save(out, resolution=100.0, save_all=True, append_images=img_list)
