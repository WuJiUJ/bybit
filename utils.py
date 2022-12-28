import math
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import pickle


def ceil(qty, precision):
    return round(
        math.ceil((qty) * (10**precision)) * (0.1**precision),
        precision,
    )


def floor(qty, precision):
    return round(
        math.floor((qty) * (10**precision)) * (0.1**precision),
        precision,
    )


def to_skl(file_path, obj):
    with open(file_path, "wb") as f:
        pickle.dump(obj, f)


def read_skl(file_path):
    with open(file_path, "rb") as f:
        return pickle.load(f)


class Gdrive:
    def __init__(self):
        gauth = GoogleAuth()
        gauth.LocalWebserverAuth()
        self.drive = GoogleDrive(gauth)

    def upload_file_to_gdrive(self, filepath):
        filename = filepath.split("/")[-1]
        file_list = self.drive.ListFile(
            {"q": "'1p9sW5wJY6oNDcd9bZBm7e6vSxzmhkUoU' in parents and trashed=false"}
        ).GetList()

        for f in file_list:
            if f["title"] == filename:
                gfile1 = self.drive.CreateFile({"id": f["id"]})
                gfile1.Trash()  # Move file to trash.
                gfile1.UnTrash()  # Move file out of trash.
                gfile1.Delete()
        gfile2 = self.drive.CreateFile(
            {
                "parents": [{"id": "1p9sW5wJY6oNDcd9bZBm7e6vSxzmhkUoU"}],
                "title": filename,
            }
        )
        gfile2.SetContentFile(filepath)
        gfile2.Upload()
