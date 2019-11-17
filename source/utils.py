# Utils for other python scripts

# Raw Author: Harvard VCG Group, Rhoana Project[https://github.com/Rhoana]
# Author: Horace.Kem[https://github.com/horacekem]
# Group: Biomed ssSEM Lab, SIBET

import os
import cv2
import sys
import glob
import json
import time
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


def index_tilespec(tile_specification):
    index = {}
    for ts in tile_specification:
        index[ts["tile_index"]] = ts
    return index


def wait_after_file(filename, timeout_seconds):
    if timeout_seconds > 0:
        cur_time = time.time()
        mod_time = os.path.getmtime(filename)
        end_wait_time = mod_time + timeout_seconds
        while cur_time < end_wait_time:
            print("Waiting for file: {}".format(filename))
            cur_time = time.time()
            mod_time = os.path.getmtime(filename)
            end_wait_time = mod_time + timeout_seconds
            if cur_time < end_wait_time:
                time.sleep(end_wait_time - cur_time)


def parse_range(s):
    result = set()
    if s is not None and len(s) != 0:
        for part in s.split(','):
            x = part.split('-')
            result.update(range(int(x[0]), int(x[-1]) + 1))
    return sorted(result)


def write_list_to_file(file_name, lst):
    with open(file_name, 'w') as out_file:
        for item in lst:
            out_file.write("%s\n" % item)
