# This is a script that helps you create h5 files to store the sift features of images read from
# json files based on Rhoana's rh_aligner[https://github.com/Rhoana/rh_aligner].
# We modified it to support single-beam file structure and updated syntax to python3.

# You have to run this script in terminal(or the terminal embedded in IDE) because of the sys.argv
# Run the following command:
# (Your conda env)user-name@computer-name:~/EM-stitching/source$
#     python create_sift_features.py json_filename output_h5_folder

# Raw Author: Harvard VCG Group, Rhoana Project[https://github.com/Rhoana]
# Author: Horace.Kem[https://github.com/horacekem]
# Group: Biomed ssSEM Lab, SIBET

import cv2
import sys
import numpy as np
import h5py
import os
import re
import utils


def compute_tile_sift_features(tile_specification, output_h5_name, initial_sigma):

    image_path = tile_specification["mipmapLevels"]["0"]["imageUrl"]
    image_file_name = os.path.basename(image_path)
    img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    print("Computing sift features for image: {}".format(image_file_name))

    sift = cv2.xfeatures2d.SIFT_create(sigma=initial_sigma)
    points, descriptors = sift.detectAndCompute(img_gray, None)
    if descriptors is None:
        descriptors = []
        points = []

    descriptors = np.array(descriptors, dtype=np.uint8)

    print("Saving {0} sift features at: {1}".format(len(descriptors), output_h5_name))
    with h5py.File(output_h5_name, 'w') as hf:
        hf.create_dataset("imageUrl", data=np.array(image_path.encode("utf-8"), dtype='S'))
        hf.create_dataset("points/responses", data=np.array([p.response for p in points], dtype=np.float32))
        hf.create_dataset("points/locations", data=np.array([p.pt for p in points], dtype=np.float32))
        hf.create_dataset("points/sizes", data=np.array([p.size for p in points], dtype=np.float32))
        hf.create_dataset("points/octaves", data=np.array([p.octave for p in points], dtype=np.float32))
        hf.create_dataset("descriptors", data=descriptors)


def create_tile_sift_features(json_filename, output_h5_name, index, initial_sigma=1.6):
    tile_specifications = utils.load_tile_specifications(json_filename)
    tile_specification = tile_specifications[index]
    compute_tile_sift_features(tile_specification, output_h5_name, initial_sigma=initial_sigma)


def create_section_sift_features(json_filename, output_h5_folder, initial_sigma=1.6):
    utils.create_dir(output_h5_folder)
    tile_specifications = utils.load_tile_specifications(json_filename)
    for tile_specification in tile_specifications:
        image_path = tile_specification["mipmapLevels"]["0"]["imageUrl"]
        output_h5_basename = re.split('\/|\.', image_path)[-2] + "_sift_features.h5"
        output_h5_name = os.path.join(output_h5_folder, output_h5_basename)
        compute_tile_sift_features(tile_specification, output_h5_name, initial_sigma=initial_sigma)


def main():
    json_filename = sys.argv[1]
    if len(sys.argv) == 3:
        output_h5_folder = sys.argv[2]
        create_section_sift_features(json_filename, output_h5_folder, initial_sigma=1.6)
    else:
        output_h5_name = sys.argv[2]
        index = sys.argv[3]
        create_tile_sift_features(json_filename, output_h5_name, index, initial_sigma=1.6)


if __name__ == '__main__':
    main()
