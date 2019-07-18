# Utils for other python scripts

# Author: Horace.Kem[https://github.com/horacekem]
# Group: Biomed ssSEM Lab, SIBET

import os
import cv2
import sys
import glob
import json
from urllib.parse import urljoin
from urllib.request import pathname2url


def path2url(path):
    return urljoin('file:', pathname2url(os.path.abspath(path)))


def read_dimensions(image_file):
    im = cv2.imread(image_file, cv2.IMREAD_GRAYSCALE)
    if im is None:
        print('Cannot read tile images:{}'.format(image_file))
        sys.exit(1)
    return im.shape


def find_image_files(folder_path):
    return glob.glob(os.path.join(folder_path, 'Tile_r*-c*_*.tif'))


def create_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def conf_from_file(conf_filename, tool):
    res = None
    if conf_filename is not None:
        with open(conf_filename, 'r') as conf_file:
            conf = json.load(conf_file)
            if tool in conf:
                return conf[tool]
    return res


def load_tile_specifications(json_filename):
    with open(json_filename, 'r') as data_file:
        tile_specifications = json.load(data_file)
    return tile_specifications
