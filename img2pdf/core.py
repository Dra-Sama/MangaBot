import os
from io import BytesIO
from typing import List, BinaryIO
from pathlib import Path
from fpdf import FPDF
import re

from PIL import Image

from img2pdf.img_size import get_image_size


def fld2pdf(folder: Path, out: str):
    
    files = [file for file in folder.glob(r'*') if re.match(r'.*\.(jpg|png|jpeg|webp)', file.name)]
    files.sort(key=lambda x: x.name)
    thumbnail = Image.open(files[0]).convert('RGB')
    tg_max_size = (300, 300)
    thumbnail.thumbnail(tg_max_size)
    thumb_path = folder / 'thumbnail' / f'thumbnail.jpg'
    os.makedirs(thumb_path.parent, exist_ok=True)
    thumbnail.save(thumb_path)
    thumbnail.close()
    pdf = folder / f'{out}.pdf'
    try:
        img2pdf(files, pdf)
    except BaseException as e:
        print(f'Image to pdf failed with exception: {e}')
        old_img2pdf(files, pdf)
    return pdf, thumb_path


def new_img(path: Path) -> Image.Image:
    img = Image.open(path)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    return img


def old_img2pdf(files: List[Path], out: Path):
    img_list = [new_img(img) for img in files]
    img_list[0].save(out, resolution=100.0, save_all=True, append_images=img_list[1:])
    for img in img_list:
        img.close()


def pil_image(path: Path) -> BytesIO:
    img = Image.open(path)
    try:
        membuf = BytesIO()
        if path.suffix == '.webp':
            img.save(membuf, format='jpeg')
        else:
            img.save(membuf)
    finally:
        img.close()
    return membuf


def img2pdf(files: List[Path], out: Path):
    pdf = FPDF('P', 'pt')
    for imageFile in files:
        width, height = get_image_size(imageFile)
        
        pdf.add_page(format=(width, height))

        img_bytes = pil_image(imageFile)

        pdf.image(img_bytes, 0, 0, width, height)

        img_bytes.close()

    pdf.set_title(out.stem)
    pdf.output(out, "F")
    pdf.close()
