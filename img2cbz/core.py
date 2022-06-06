import re
import zipfile
from pathlib import Path
from typing import List


def fld2cbz(folder: Path, name: str):
    cbz = folder / f'{name}.cbz'
    files = [file for file in folder.glob(r'*') if re.match(r'.*\.(jpg|png|jpeg|webp)', file.name)]
    files.sort(key=lambda x: x.name)
    img2cbz(files, cbz)
    return cbz


def img2cbz(files: List[Path], out: Path):
    zip_file = zipfile.ZipFile(out, 'w')  # parameter "out" must be a .zip file

    for image_file in files:
        zip_file.write(image_file, compress_type=zipfile.ZIP_DEFLATED)

    zip_file.close()
