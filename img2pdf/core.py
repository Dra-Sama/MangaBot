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


def img2pdf(files: List[Path], out: Path):
    
    im0: Image.Image = Image.open(files[0]).convert(mode='RGB', palette=1)
    img_list = [Image.open(img).convert(mode='RGB', palette=1) for img in files[1:]]
    im0.save(out, "PDF", resolution=100.0, save_all=True, append_images=img_list)
