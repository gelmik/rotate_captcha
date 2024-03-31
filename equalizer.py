import base64
import io
import os
from io import BytesIO
from tkinter import *

from PIL.Image import Resampling
from minio import Minio
from screeninfo import get_monitors
from tkinter import ttk
from PIL import ImageTk, Image
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv('URL')
ACCESS_KEY = os.getenv('ACCESS_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
BUCKET = os.getenv('BUCKET')


class App:
    open_image = None
    rotate_image = None
    scale = 4

    def __init__(self):
        self.minioClient = Minio(URL, access_key=ACCESS_KEY, secret_key=SECRET_KEY, secure=True)
        self.root = Tk()
        self.verticalScale = ttk.Scale(orient=VERTICAL, length=720, from_=0.0, to=360.0, value=180, command=self.change_angle)

        monitor_info = get_monitors()[0]
        width = 1000
        height = 800
        self.root.geometry(
            f"{width}x{height}+{monitor_info.width // 2 - width // 2}+{monitor_info.height // 2 - height // 2}")

        self.root.grid_rowconfigure(index=0, weight=5)
        self.root.grid_rowconfigure(index=1, weight=1)
        self.root.grid_columnconfigure(index=0, weight=2)
        self.root.grid_columnconfigure(index=1, weight=1)

        self.canvas = Canvas(bg="black")
        self.canvas.grid(sticky=NSEW, column=0, row=0, padx=0)

        self.label = ttk.Label(text="", font=("Arial", 14))
        self.label.grid(column=0, row=1, sticky=NSEW, padx=0)

        self.verticalScale.grid(sticky=NSEW, column=1, row=0, padx=0)

        self.btn_save_image = ttk.Button(text="Следующая картинка", command=self.save_rotate_image)
        self.btn_save_image.grid(column=1, row=1, sticky=NSEW, padx=0)

        self.root.resizable(False, False)
        self.root.update()
        self.scale = self.canvas.winfo_width()/152
        self.images = []
        self.get_undefined_images()

        self.change_images()
        self.rotate_images = []
        self.root.mainloop()


    def change_images(self):

        if self.images:
            next_image = self.images.pop(0)
            self.open_image = next_image
            self.rotate_image = ImageTk.PhotoImage(self.open_image['image'].resize((int(self.open_image['image'].width*self.scale),
                                                                                    int(self.open_image['image'].height*self.scale))))
            self.canvas.create_image(0, 0, image=self.rotate_image, anchor=NW)
            self.label.config(text=f"{self.open_image['name']} Осталось: {len(self.images)}")
            self.draw_axes()

        if not self.images:
            self.btn_save_image.config(text="Загрузить картинки")
            self.btn_save_image.config(command=self.send_rotate_images)

    def save_rotate_image(self):
        self.rotate_images.append({'name': self.open_image['name'], 'image': self.open_image['image'].rotate(self.verticalScale.get(),
                                                                                                             fillcolor="#FFFFFF",
                                                                                                             expand=False,
                                                                                                             resample=Resampling.BICUBIC)})
        if self.images:
            self.change_images()


    def change_angle(self, newVal):
        self.canvas.delete("all")
        self.rotate_image = ImageTk.PhotoImage(self.open_image['image'].resize((int(self.open_image['image'].width*self.scale), int(self.open_image['image'].height*self.scale))).rotate(self.verticalScale.get()))
        self.canvas.create_image(0, 0, image=self.rotate_image, anchor=NW)
        self.draw_axes()

    def draw_axes(self):
        canvas_width = int(self.open_image['image'].width*self.scale)
        canvas_height = int(self.open_image['image'].height*self.scale)
        self.canvas.create_line(0, canvas_height // 2, canvas_width, canvas_height // 2, activefill="red", dash=2, width=2)
        self.canvas.create_line(canvas_width // 2, 0, canvas_width // 2, canvas_height, activefill="red", dash=2, width=2)

    def get_undefined_images(self):
        self.images = []
        list_undefined_names = self.minioClient.list_objects(BUCKET, "rotate_captcha/undefined_image/", recursive=True)
        for undefined_image_name in list_undefined_names:
            print(f"load {undefined_image_name}")
            response = self.minioClient.get_object(BUCKET, undefined_image_name.object_name)
            self.images.append({"name": undefined_image_name.object_name, 'image': Image.open(BytesIO(base64.b64decode(response.data)))})

    def send_rotate_images(self):
        self.rotate_images.append(
            {'name': self.open_image['name'], 'image': self.open_image['image'].rotate(self.verticalScale.get(),
                                                                                       fillcolor="#FFFFFF",
                                                                                       expand=False,
                                                                                       resample=Resampling.BICUBIC)})
        self.btn_save_image.config(state=["disabled"])

        for image in self.rotate_images:
            image_name = image['name'].split('/')[-1]
            undefened_file_path = f"rotate_captcha/undefined_image/{image_name}"
            hor_file_path = f"rotate_captcha/horizontal_images/{image_name}"
            data = self.pil_to_base64(image['image'])
            file_data = io.BytesIO(data)
            self.minioClient.remove_object(BUCKET, undefened_file_path)
            self.minioClient.put_object(BUCKET, hor_file_path, file_data, len(data))
        self.root.destroy()

    @staticmethod
    def pil_to_base64(pil_img):
        img_buffer = BytesIO()
        pil_img.save(img_buffer, format='PNG')
        byte_data = img_buffer.getvalue()
        base64_str = base64.b64encode(byte_data)
        return base64_str

app = App()



