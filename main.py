import math, operator
import os
from functools import reduce
from tkinter import *

from PIL.Image import Resampling
from screeninfo import get_monitors
from tkinter import ttk, filedialog
from PIL import ImageTk, Image
from os import listdir
from os.path import isfile, join


root = Tk()
monitor_info = get_monitors()[0]
width = 1000
height = 800
root.geometry(f"{width}x{height}+{monitor_info.width//2 - width//2}+{monitor_info.height//2 - height//2}")

root.grid_rowconfigure(index=0, weight=5)
root.grid_rowconfigure(index=1, weight=1)
root.grid_columnconfigure(index=0, weight=2)
root.grid_columnconfigure(index=1, weight=1)


canvas = Canvas(bg="black", width=152, height=152)
canvas.grid(sticky=NSEW, column=0, row=0, padx=0)
path_hor_images = "hor_images"

def image_difference(img1, img2):
    h1 = img1.histogram()
    h2 = img2.histogram()
    rms = math.sqrt(reduce(operator.add,
                           map(lambda a, b: (a - b) ** 2, h1, h2)) / len(h1))
    return rms


class App:
    raw_images_path = "raw_images"
    images = []
    open_image = None
    rotate_image = None
    scale = 4

    def change_images(self):
        next_image = self.images.pop(0)
        self.open_image = Image.open(join(self.raw_images_path, next_image))
        self.rotate_image = ImageTk.PhotoImage(self.open_image.resize((self.open_image.width*self.scale, self.open_image.height*self.scale)))
        canvas.create_image(0, 0, image=self.rotate_image, anchor=NW)
        self.draw_axes()

    def open_img_dir(self):
        if not self.raw_images_path:
            self.raw_images_path = filedialog.askdirectory()
        self.images = [f for f in listdir(self.raw_images_path) if isfile(join(self.raw_images_path, f))]
        self.change_images()

    def save_rotate_image(self):
        # image = pygame.image.load(self.open_image.filename)
        # image.set_colorkey((255, 255, 255))
        # image = pygame.transform.rotate(image, verticalScale.get())
        # pygame.image.save(image, join(path_hor_images, self.open_image.filename.replace('\\', '_')))

        print(image_difference(self.open_image, self.open_image.rotate(verticalScale.get(),
                               fillcolor="#FFFFFF",
                               expand=False,
                               resample=Resampling.BICUBIC)))
        self.open_image.rotate(verticalScale.get(),
                               fillcolor="#FFFFFF",
                               expand=False,
                               resample=Resampling.BICUBIC).save(join(path_hor_images, self.open_image.filename.replace('\\', '_')),
                                                                                           quality=0,
                                                                                           compress_level=0,
                                                                                           method=6)

        # os.remove(join(self.raw_images_path, self.open_image.filename))
        self.change_images()

    def change_angle(self, newVal):
        canvas.delete("all")
        self.rotate_image = ImageTk.PhotoImage(self.open_image.resize((self.open_image.width*self.scale, self.open_image.height*self.scale)).rotate(verticalScale.get()))
        canvas.create_image(0, 0, image=self.rotate_image, anchor=NW)
        self.draw_axes()

    def draw_axes(self):
        canvas_width = self.open_image.width*self.scale
        canvas_height = self.open_image.height*self.scale
        canvas.create_line(0, canvas_height // 2, canvas_width, canvas_height // 2, activefill="red", dash=2, width=2)
        canvas.create_line(canvas_width // 2, 0, canvas_width // 2, canvas_height, activefill="red", dash=2, width=2)

app = App()

verticalScale = ttk.Scale(orient=VERTICAL, length=360, from_=0.0, to=360.0, value=180, command=app.change_angle)
verticalScale.grid(sticky=NSEW, column=1, row=0, padx=0)


btn_choice_img_dir = ttk.Button(text="Выбрать папку с картинками", command=app.open_img_dir)
btn_choice_img_dir.grid(column=0, row=1, sticky=NSEW, padx=0)

btn_save_image = ttk.Button(text="Сохранить картинку", command=app.save_rotate_image)
btn_save_image.grid(column=1, row=1, sticky=NSEW, padx=0)

root.resizable(False, False)

root.mainloop()