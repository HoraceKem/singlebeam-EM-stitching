# This is a script for resize and invert SEM images

# Author: Horace.Kem[https://github.com/horacekem]
# Group: Biomed ssSEM Lab, SIBET

import cv2
import glob
import os
import utils
import sys


def resize_section_folder(section_folder, output_folder, ratio=2, invert=True):
    utils.create_dir(output_folder)
    for image_file in sorted(utils.find_image_files(section_folder)):
        image_size = utils.read_dimensions(image_file)
        image_file_name = os.path.basename(image_file)
        image_old = cv2.imread(image_file, cv2.IMREAD_GRAYSCALE)
        image_new = cv2.resize(image_old, (int(image_size[0]/ratio), int(image_size[1]/ratio)))
        if invert:
            image_new = 255 - image_new
        image_file_path_new = os.path.join(output_folder, image_file_name)
        cv2.imwrite(image_file_path_new, image_new)


def resize_sample_folder(sample_folder, output_folder, skip_layers, ratio=2, invert=True):
    section_folders = sorted(glob.glob(os.path.join(sample_folder, '*')))
    layer = 0
    skipped_layers = utils.parse_range(skip_layers)
    for section_folder in section_folders:
        if os.path.isdir(section_folder):
            layer += 1
            if layer in skipped_layers:
                print("Skipping layer {}".format(layer))
                continue
            print("Resizing section_folder:{}".format(section_folder))
            section_folder_name = section_folder.split(os.path.sep)[-1]
            output_section_folder = os.path.join(output_folder, section_folder_name)
            resize_section_folder(section_folder, output_section_folder, ratio=ratio, invert=invert)


if __name__ == '__main__':
    your_sample_folder = sys.argv[1]
    your_output_folder = sys.argv[2]
    skip_layers_test = '10-50'
    resize_sample_folder(your_sample_folder, your_output_folder, skip_layers_test, ratio=10, invert=True )
