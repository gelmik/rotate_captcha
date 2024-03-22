import base64
import math, operator
import os
import shutil
from functools import reduce
from io import BytesIO

from PIL.Image import Resampling
from PIL import ImageTk, Image
from os import listdir
from os.path import isfile, join

path_groups = "groups"

dirs = [d for d in listdir(path_groups) if not isfile(join(path_groups, d))]

for dir in dirs:
    if not os.path.isdir(f"groups/{dir}/rotated"):
        os.mkdir(f"groups/{dir}/rotated")
    image_path = join(f"groups/{dir}", [f for f in listdir(f"groups/{dir}/") if isfile(join(f"groups/{dir}/", f))][0])
    print(f"open {dir}")
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        image = Image.open(BytesIO(base64.b64decode(encoded_string)))

        for i in range(360):
            image.rotate(i,
                         fillcolor="#FFFFFF",
                         expand=False,
                         resample=Resampling.BICUBIC).save(
                join(f"groups/{dir}/rotated", f"{i}.png"),
                quality=100,
                compress_level=0,
                method=6)

    a = 1
