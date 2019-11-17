# This is a script for running the complete 2d-stitching of SEM images based on
# Rhoana's rh_aligner[https://github.com/Rhoana/rh_aligner].
# We modified it to run on local machine(not cluster) and support single-beam file structure.

# Raw Author: Harvard VCG Group, Rhoana Project[https://github.com/Rhoana]
# Author: Horace.Kem[https://github.com/horacekem]
# Group: Biomed ssSEM Lab, SIBET

# Modify the arguments in 'arguments.txt' and run this file.
# The arguments are:
# Line 1: The path to single-beam sem images of the sample.
# Line 2: Your workspace where all the step-by-step results will be stored in.
# Line 3: Skipped layers. e.g. 50 layers in total, if you input 11-50, then only 1-10 layers will be computed.
# Line 4: The ratio of down-sampling.

import sys
import os
import itertools
import glob
from utils import create_dir, parse_range, write_list_to_file, load_tile_specifications
from bounding_box import BoundingBox
from resize import resize_sample_folder
from singlebeam_import_tilespec import parse_sample
from create_sift_features import create_tile_sift_features
from match_sift_features_and_filter import match_single_sift_features_and_filter
from optimize_2d_stitching import optimize_2d_stitching
from render_2d import render_tile


def create_folders(workspace):
    # create a workspace directory if not found
    create_dir(workspace)
    # create relevant folders if not found
    spec_dir_path = os.path.join(workspace, "tile_spec")
    sifts_dir_path = os.path.join(workspace, "sifts")
    matched_sifts_dir_path = os.path.join(workspace, "matched_sifts")
    optimized_2d_dir_path = os.path.join(workspace, "optimized_2d")
    create_dir(spec_dir_path)
    create_dir(sifts_dir_path)
    create_dir(matched_sifts_dir_path)
    create_dir(optimized_2d_dir_path)
    return spec_dir_path, sifts_dir_path, matched_sifts_dir_path, optimized_2d_dir_path


if __name__ == '__main__':
    with open('arguments.txt', 'r') as arguments:
        arguments_list = arguments.readlines()
    arguments_list = [argument.replace('\n', '') for argument in arguments_list]
    sample_dir_raw = arguments_list[0]
    workspace_dir = arguments_list[1]

    # Step 1: Create workspace and sub-folders from arguments.
    spec_dir, sifts_dir, matched_sifts_dir, optimized_2d_dir = create_folders(workspace_dir)

    if arguments_list[2] != 'None':
        skip_layers = arguments_list[2]
    else:
        skip_layers = None
    resize_ratio = int(arguments_list[3])

    if resize_ratio != 1:
        sample_dir = os.path.join(workspace_dir, 'images')
        resize_sample_folder(sample_dir_raw, sample_dir, skip_layers, ratio=resize_ratio, invert=True)
    else:
        sample_dir = sample_dir_raw

    # Step 2: Import tile specifications from raw sample images.
    parse_sample(sample_dir, spec_dir, 'cc_BJ')

    # Step 3: Compute and match sift features, optimize the 2d montage.
    # Get all input json files (one per section) into a dictionary
    # {json_fname -> [filtered json fname, sift features file, etc.]}
    json_files = dict((jf, {}) for jf in (glob.glob(os.path.join(spec_dir, '*.json'))))
    skipped_layers = parse_range(skip_layers)
    all_layers = []
    layers_data = {}
    fixed_tile = 0
    render_first = True
    for f in sorted(json_files.keys()):
        tiles_fname_prefix = os.path.splitext(os.path.basename(f))[0]  # cc_Sec001
        cur_tilespec = load_tile_specifications(f)  # content in cc_Sec001.json

        # read the layer from the file
        layer = None
        for tile in cur_tilespec:
            if tile['layer'] is None:
                print("Error reading layer in one of the tiles in: {0}".format(f))
                sys.exit(1)
            if layer is None:
                layer = int(tile['layer'])
            if layer != tile['layer']:
                print("Error when reading tiles from {0} found inconsistent layers numbers: "
                      "{1} and {2}".format(f, layer, tile['layer']))
                sys.exit(1)
        if layer is None:
            print("Error reading layers file: {0}. No layers found.".format(f))
            continue

        # Check if we need to skip the layer
        if layer in skipped_layers:
            print("Skipping layer {}".format(layer))
            continue

        slayer = str(layer)

        if not (slayer in layers_data.keys()):
            layers_data[slayer] = {}
            layers_data[slayer]['ts'] = f
            layers_data[slayer]['sifts'] = {}
            layers_data[slayer]['prefix'] = tiles_fname_prefix
            layers_data[slayer]['matched_sifts'] = []

        layer_sifts_dir = os.path.join(sifts_dir, layers_data[slayer]['prefix'])  # sifts/cc_Sec001
        layer_matched_sifts_dir = os.path.join(matched_sifts_dir, layers_data[slayer]['prefix'])
        # matched sifts/cc_Sec001
        create_dir(layer_sifts_dir)
        create_dir(layer_matched_sifts_dir)

        all_layers.append(layer)

        # Skip the section if already have the optimized result
        opt_montage_json = os.path.join(optimized_2d_dir, "{0}_2d_montage.json".format(tiles_fname_prefix))
        # cc_Sec001_2d_montage.json
        if os.path.exists(opt_montage_json):
            print("Previously optimizing (affine) layer: {0}, skipping all pre-computations".format(slayer))
            continue

        # create the sift features of these tiles
        for i, ts in enumerate(cur_tilespec):
            imgurl = ts["mipmapLevels"]["0"]["imageUrl"]
            tile_fname = os.path.basename(imgurl).split('.')[0]

            # create the sift features of these tiles
            sifts_h5 = os.path.join(layer_sifts_dir, "{0}_sifts_{1}.h5py".format(tiles_fname_prefix, tile_fname))
            if not os.path.exists(sifts_h5):
                print("Computing tile  sifts: {0}".format(tile_fname))
                create_tile_sift_features(f, sifts_h5, i, initial_sigma=1.6)
            layers_data[slayer]['sifts'][imgurl] = sifts_h5

        indices = []
        for pair in itertools.combinations(range(len(cur_tilespec)), 2):
            idx1 = pair[0]
            idx2 = pair[1]
            ts1 = cur_tilespec[idx1]
            ts2 = cur_tilespec[idx2]
            # if the two tiles intersect, match them
            bbox1 = BoundingBox.fromList(ts1["bbox"])
            bbox2 = BoundingBox.fromList(ts2["bbox"])
            if bbox1.overlap(bbox2):
                imageUrl1 = ts1["mipmapLevels"]["0"]["imageUrl"]
                imageUrl2 = ts2["mipmapLevels"]["0"]["imageUrl"]
                tile_fname1 = os.path.basename(imageUrl1).split('.')[0]
                tile_fname2 = os.path.basename(imageUrl2).split('.')[0]
                sifts_1 = os.path.join(layer_sifts_dir, "{0}_sifts_{1}.h5py".format(tiles_fname_prefix, tile_fname1))
                sifts_2 = os.path.join(layer_sifts_dir, "{0}_sifts_{1}.h5py".format(tiles_fname_prefix, tile_fname2))
                index_pair = (int(ts1["tile_index"]), int(ts2["tile_index"]))

                matched_json_basename = "{0}_matches_{1}_{2}.json".format(tiles_fname_prefix, tile_fname1, tile_fname2)
                matched_json = os.path.join(layer_matched_sifts_dir, matched_json_basename)
                # match the features of overlapping tiles
                if not os.path.exists(matched_json):
                    print("Matching sift of tiles: {0} and {1}".format(imageUrl1, imageUrl2))
                    match_single_sift_features_and_filter(f, sifts_1, sifts_2, matched_json, index_pair)
                    layers_data[slayer]['matched_sifts'].append(matched_json)

        matches_list_file = os.path.join(layer_matched_sifts_dir,
                                         "{}_matched_sifts_files.txt".format(tiles_fname_prefix))
        write_list_to_file(matches_list_file, layers_data[slayer]['matched_sifts'])

        # optimize (affine) the 2d layer matches (affine)
        opt_montage_json = os.path.join(optimized_2d_dir, "{0}_montaged.json".format(tiles_fname_prefix))
        if not os.path.exists(opt_montage_json):
            print("Optimizing (affine) layer matches: {0}".format(slayer))
            optimize_2d_stitching(f, matches_list_file, opt_montage_json)
        if render_first:
            render_tile(opt_montage_json)
            render_first = False
            a = input("Rendered right?(Yes/No)")
            if a == 'Yes'or a == 'yes':
                continue
            else:
                sys.exit(1)
