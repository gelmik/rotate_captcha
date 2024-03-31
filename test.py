from minio import Minio
import os
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv('URL')
ACCESS_KEY = os.getenv('ACCESS_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
BUCKET = os.getenv('BUCKET')


minioClient = Minio(URL, access_key=ACCESS_KEY, secret_key=SECRET_KEY, secure=True)


minioClient.remove_object(BUCKET, f"rotate_captcha/horizontal_images/36.png")