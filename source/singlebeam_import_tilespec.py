# This is a script that helps you import the key information in single-beam serial-section SEM images
# to json files based on Rhoana's rh_aligner[https://github.com/Rhoana/rh_aligner].
# We modified it to support single-beam file structure and updated syntax to python3.

# You have to run this script in terminal(or the terminal embedded in IDE) because of the sys.argv
# Run the following command:
# (Your conda env)user-name@computer-name:~/EM-stitching/source$
#     python singlebeam_import_tilespec.py sample_folder output_folder sample_name

# Raw Author: Harvard VCG Group, Rhoana Project[https://github.com/Rhoana]
# Author: Horace.Kem[https://github.com/horacekem]
# Group: Biomed ssSEM Lab, SIBET

import os
import sys
import glob
import json
import re
from decimal import *
import utils


def filename_decimal_key(tile):
    filename = tile["file_base_name"]
    return Decimal(''.join([c for c in filename if c.isdigit()]))


def parse_image(image_file_path, overlap=0.06):
    image_size = utils.read_dimensions(image_file_path)
    image_file_name = os.path.basename(image_file_path)
    filename_match = re.match('Tile_r([0-9]+)-c([0-9]+)_.*[.]tif+', image_file_name)
    offset_y = (int(filename_match.group(1)) - 1) * image_size[0] * (1.0 - overlap)
    offset_x = (int(filename_match.group(2)) - 1) * image_size[1] * (1.0 - overlap)

    image_info = {}
    image_info["image_file_name"] = image_file_name
    image_info["image_size"] = image_size
    image_info["offset_y"] = int(offset_y)
    image_info["offset_x"] = int(offset_x)
    return image_info


def parse_section(section_folder):
    tiles = []
    section_size = [0, 0]

    for image_file in sorted(utils.find_image_files(section_folder)):
        image_info = parse_image(image_file)
        tile = {}
        tile["file_full_path"] = image_file
        tile["file_base_name"] = image_info["image_file_name"]
        tile["width"] = image_info["image_size"][1]
        tile["height"] = image_info["image_size"][0]
        tile["tx"] = image_info["offset_x"]
        tile["ty"] = image_info["offset_y"]
        tiles.append(tile)

        section_size[0] = max(section_size[0], image_info["image_size"][0] + image_info["offset_y"])
        section_size[1] = max(section_size[1], image_info["image_size"][1] + image_info["offset_x"])

    if len(tiles) == 0:
        print("Nothing to write from directory{}".format(section_folder))

    tiles.sort(key=filename_decimal_key)
    section_info = {}
    section_info["height"] = section_size[0]
    section_info["width"] = section_size[1]
    section_info["tiles"] = tiles
    return section_info


def parse_sample(sample_folder, output_folder, sample_name):
    section_folders = sorted(glob.glob(os.path.join(sample_folder, '*')))
    for section_folder in section_folders:
        if os.path.isdir(section_folder):
            print("Parsing section_folder:{}".format(section_folder))
            section_index = section_folder.split(os.path.sep)[-1]
            output_json_filename = os.path.join(output_folder, "{0}_Sec{1}.json".format(sample_name, section_index))
            layer = int(section_index)

            if os.path.exists(output_json_filename):
                print("Output file {} already found, skipping".format(output_json_filename))
                continue
            current_section_info = parse_section(section_folder)

            export = []

            for tile in current_section_info["tiles"]:
                tile_specification = {
                    "mipmapLevels": {
                        "0": {
                            "imageUrl": "{0}".format(tile["file_full_path"].replace(os.path.sep, '/'))
                        }
                    },
                    "minIntensity": 0.0,
                    "maxIntensity": 255.0,
                    "layer": layer,
                    "transforms": [{
                        "className": "mpicbg.trakem2.transform.TranslationModel2D",
                        "dataString": "{0} {1}".format(tile["tx"], tile["ty"])
                    }],
                    "width": tile["width"],
                    "height": tile["height"],
                    "bbox": [tile["tx"], tile["tx"]+tile["width"],
                             tile["ty"], tile["ty"]+tile["height"]]
                }
                export.append(tile_specification)

                if len(export) > 0:
                    with open(output_json_filename, 'w') as outjson:
                        json.dump(export, outjson, sort_keys=False, indent=4)
                    print("Imported section {0} data to {1}".format(section_index, output_json_filename))
                else:
                    print("Nothing to import.")


def main():
    sample_folder = sys.argv[1]
    output_folder = sys.argv[2]
    sample_name = sys.argv[3]

    utils.create_dir(output_folder)
    parse_sample(sample_folder, output_folder, sample_name)


if __name__ == '__main__':
    main()
