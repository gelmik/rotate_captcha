import math, operator
import os
import shutil
from functools import reduce

from PIL.Image import Resampling
from PIL import ImageTk, Image
from os import listdir
from os.path import isfile, join

path_hor_images = "hor_images"

def image_difference(img1, img2):
    h1 = img1.histogram()
    h2 = img2.histogram()
    rms = math.sqrt(reduce(operator.add,
                           map(lambda a, b: (a - b) ** 2, h1, h2)) / len(h1))
    return rms


images = [Image.open(join(path_hor_images, f)) for f in listdir(path_hor_images) if isfile(join(path_hor_images, f))]

image = images.pop(0)

groups = []

while images:
    image = images.pop(0)
    new_group = [image]
    index_image = 0
    while index_image < len(images):
        if image_difference(image, images[index_image]) < 30:
            new_group.append(images[index_image])
            del images[index_image]
        else:
            index_image += 1
    groups.append(new_group)

diff = sorted([image_difference(image, img2) for img2 in images])

for i in range(len(groups)):
    if not os.path.isdir(f"groups/{i}"):
        os.mkdir(f"groups/{i}")
    group = groups[i]
    for index, image in enumerate(group):
        shutil.copy(image.filename.replace("\\", '/'), f"groups/{i}/" + image.filename.replace("\\", '/').split('/')[-1])
