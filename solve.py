import math
import operator
import os
import time
from enum import Enum
from functools import reduce
import io
import asyncio

from minio import Minio
from PIL.Image import Resampling
from PIL import Image
from io import BytesIO
import base64

from dotenv import load_dotenv

load_dotenv()

URL = os.getenv('URL')
ACCESS_KEY = os.getenv('ACCESS_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
BUCKET = os.getenv('BUCKET')


async def image_difference(img1, img2):
    h1 = img1.histogram()
    h2 = img2.histogram()
    return math.sqrt(reduce(operator.add,
                            map(lambda a, b: (a - b) ** 2, h1, h2)) / len(h1))


class MethodFragmentation(Enum):
    crop = 0
    cross = 1


class ImageCrops:
    def __init__(self, image, levels=3, window_size=5, method=MethodFragmentation.cross):
        self.levels = levels
        self.window_size = window_size
        self.method_fragmentation = method
        self.fragment_method = self.cross_fragment if self.method_fragmentation == MethodFragmentation.cross else self.crop_fragment
        self.diff_method = self.diff_cross if self.method_fragmentation == MethodFragmentation.cross else self.diff_crop
        self.fragments = self.get_fragments(image)

    def crop_fragment(self, image, center):
        x, y = center
        delta = self.window_size // 2
        return image.crop((x - delta,
                           y - delta,
                           x + delta,
                           y + delta))

    def cross_fragment(self, image, center):
        x, y = center
        delta = self.window_size // 2 + 1
        result = [image.getpixel((x, y))[:3]]
        for i in range(1, delta):
            result.append(image.getpixel((x - i, y - i))[:3])  # 6➡...
            result.append(image.getpixel((x + i, y - i))[:3])  #  2➡3
            result.append(image.getpixel((x + i, y + i))[:3])  #  ⬆1 ⬇
            result.append(image.getpixel((x - i, y + i))[:3])  #  5⬅4
        return result

    def get_fragments(self, image):
        fragments = []
        img_width, img_height = image.size
        delta = int((((img_width + img_height) * 2 ** .5) / 8 - self.window_size * (.5 + self.levels - 1)) / max(
            (self.levels - 1), 1))

        center_x, center_y = img_width // 2, img_height // 2
        for i in range(-((self.levels * 2 - 1) // 2), (self.levels * 2 - 1) // 2 + 1):
            for j in range(-((self.levels * 2 - 1) // 2), (self.levels * 2 - 1) // 2 + 1):
                fragments.append(self.fragment_method(image, (center_x + i * (self.window_size + delta), center_y + j * (self.window_size + delta))))
        return fragments

    async def diff_crop(self, other):
        if len(self.fragments) != len(other.fragments):
            raise Exception("difference len() fragments")

        result = sum([await image_difference(self.fragments[i], other.fragments[i])
                      for i in range(len(self.fragments))]) / len(self.fragments)
        return result

    async def diff_cross(self, other):
        diff_fragment = lambda f1, f2: sum([sum([(f1[i][j] - f2[i][j])**2 for j in range(3)]) / 3 for i in range(len(f1))]) / len(f1)
        if len(self.fragments) != len(other.fragments):
            raise Exception("difference len() fragments")
        result = sum([diff_fragment(self.fragments[i], other.fragments[i]) for i in range(len(self.fragments))]) / len(self.fragments)
        return result

    async def diff(self, other):
        result = await self.diff_method(other)
        return result


class Determinant:
    def __init__(self, levels=3, window_size=5, method_fragmentation=MethodFragmentation.cross):
        self.levels = levels
        self.window_size = window_size
        self.minioClient = Minio(URL, access_key=ACCESS_KEY, secret_key=SECRET_KEY, secure=True)
        self.images = []
        self.groups = {}
        self.success_solve = 0
        self.unsuccess_solve = 0
        self.is_rebuild = False
        self.range_angle = 1
        self.image_size = 152
        self.set_range_angle()
        self.method_fragmentation = method_fragmentation

    def set_range_angle(self):
        r = int((self.image_size * 2 ** .5) / 8)
        angle = 1
        x45 = int(math.cos(math.radians(45)) * self.image_size / 2) - self.window_size // 2
        y45 = int(math.sin(math.radians(45)) * self.image_size / 2) - self.window_size // 2

        curr_in_square = lambda tx, ty: (x45 - self.window_size // 2 <= tx <= x45 + self.window_size // 2
                                         and y45 - self.window_size // 2 <= ty <= y45 + self.window_size // 2)

        for i in range(1, 45):
            x = int(math.cos(math.radians(45 - i)) * self.image_size / 2) - self.window_size // 2
            y = int(math.sin(math.radians(45 - i)) * self.image_size / 2) - self.window_size // 2

            pixel_in_window_count = 0
            for i in range(-((self.window_size - 1) // 2), (self.window_size - 1) // 2 + 1):
                for j in range(-((self.window_size - 1) // 2), (self.window_size - 1) // 2 + 1):
                    if curr_in_square(x + j, y + i):
                        pixel_in_window_count += 1

            if (pixel_in_window_count / self.window_size ** 2) * 100 >= 25.:
                angle += 1
            else:
                break
        self.range_angle = max(self.range_angle, angle)

    async def get_group(self, image):
        diffs = [(group, await image_difference(image, self.groups[group]['horizontal_image'])) for group in
                 self.groups]
        return min(diffs, key=lambda diff: diff[-1])

    async def get_angle(self, image_base_64):
        while self.is_rebuild:
            await asyncio.sleep(5)
        image = Image.open(BytesIO(base64.b64decode(image_base_64)))
        group, diff = await self.get_group(image)
        # print(f"group {group}, diff {diff}")
        if diff < 40:
            image_crop = ImageCrops(image, self.levels, self.window_size)
            if self.method_fragmentation == MethodFragmentation.crop:
                angle_diffs = [(angle, await image_crop.diff(self.groups[group]['angles'][angle])) for angle in
                               range(0, 360, self.range_angle)]

                periodic_min_diff_angle, diff = min(angle_diffs, key=lambda diff: diff[-1])

                data_result = min([(angle, await image_crop.diff(self.groups[group]['angles'][angle])) for angle in
                                   range(max(0, periodic_min_diff_angle - self.range_angle),
                                         min(360, periodic_min_diff_angle + self.range_angle))], key=lambda diff: diff[-1])
            elif self.method_fragmentation == MethodFragmentation.cross:
                angle_diffs = [(angle, await image_crop.diff(self.groups[group]['angles'][angle])) for angle in
                               range(360)]

                data_result = min(angle_diffs, key=lambda diff: diff[-1])

            # print(periodic_min_diff_angle)
            result = {"angle": data_result[0], "diff": data_result[1]}

            self.success_solve += 1
        else:
            result = {"angle": -1, "diff": 0}
            list_undefined_names = self.minioClient.list_objects(BUCKET, "rotate_captcha/undefined_image/",
                                                                 recursive=True)
            is_undefined_image = False

            undefined_images = []
            for undefined_image_name in list_undefined_names:
                # print(f"load {undefined_image_name}")
                response = self.minioClient.get_object(BUCKET, undefined_image_name.object_name)
                undefined_images.append(Image.open(BytesIO(base64.b64decode(response.data))))

            if undefined_images:
                min_diff = min([await image_difference(image, undefined_image) for undefined_image in undefined_images])
                if min_diff > 40:
                    is_undefined_image = True
            else:
                is_undefined_image = True

            if is_undefined_image:
                image_name = f"{len(self.images) + len(undefined_images)}.txt"
                self.send_undefined_image(image_base_64, image_name)
            self.unsuccess_solve += 1
        return result

    def create_groups(self):
        for index_group, image in enumerate(self.images):
            print(f"create group {index_group}")
            self.groups[index_group] = {'horizontal_image': image, 'angles': {}}
            for angle in range(360):
                self.groups[index_group]['angles'][angle] = ImageCrops(image.rotate(angle,
                                                                                    fillcolor="#FFFFFF",
                                                                                    expand=False,
                                                                                    resample=Resampling.BICUBIC),
                                                                       self.levels,
                                                                       self.window_size,
                                                                       self.method_fragmentation)

    def send_undefined_image(self, image_base_64, image_name):
        file_path = f"rotate_captcha/undefined_image/{image_name}"
        data = image_base_64.encode('utf-8')
        file_data = io.BytesIO(data)
        self.minioClient.put_object(BUCKET, file_path, file_data, len(data))

    def load_images(self):
        print(f"LOAD IMAGES")
        list_images_names = self.minioClient.list_objects(BUCKET, "rotate_captcha/horizontal_images/", recursive=True)
        for image_name in list_images_names:
            print(f"load {image_name}")
            response = self.minioClient.get_object(BUCKET, image_name.object_name)
            self.images.append(Image.open(BytesIO(base64.b64decode(response.data))))

    async def info(self):
        return {
            "groups": len(self.groups),
            "levels": self.levels,
            "window_size": self.window_size,
            "success_solve": self.success_solve,
            "unsuccess_solve": self.unsuccess_solve
        }

    async def change_settings(self, data):
        if levels := data.get('levels'):
            self.levels = levels
        if window_size := data.get('window_size'):
            self.window_size = window_size
        self.rebuild()

    def rebuild(self):
        self.is_rebuild = True
        self.images = []
        self.load_images()
        self.groups = {}
        self.create_groups()
        self.set_range_angle()
        self.is_rebuild = False

# im = Image.open("groups/0.png")
# im2 = Image.open("groups/10.png")
#
# ic1 = ImageCrops(im)
# ic2 = ImageCrops(im2)
#
# ic1.diff(ic2)