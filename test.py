import os, pickle
from constants import *

if os.path.exists(POSITION_OBJECT_PATH):
    with open(POSITION_OBJECT_PATH, "rb") as f:
        print(pickle.load(f))
