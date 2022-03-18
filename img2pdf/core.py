from typing import List, BinaryIO
from pathlib import Path
from fpdf import FPDF
import re

from PIL import Image

from img2pdf.img_size import get_image_size


def fld2pdf(folder: Path, out: str):
    
    files = [file for file in folder.glob(r'*') if re.match(r'.*\.(jpg|png|jpeg|webp)', file.name)]
    files.sort(key=lambda x: x.name)
    pdf = folder / f'{out}.pdf'
    try:
        img2pdf(files, pdf)
    except BaseException as e:
        print(f'Image to pdf failed with exception: {e}')
        old_img2pdf(files, pdf)
    return pdf


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


def img2pdf(files: List[Path], out: Path):
    pdf = FPDF('P', 'pt')
    for imageFile in files:
        width, height = get_image_size(imageFile)
        
        pdf.add_page(format=(width, height))

        pdf.image(imageFile, 0, 0, width, height)

    pdf.output(out, "F")
    del pdf
