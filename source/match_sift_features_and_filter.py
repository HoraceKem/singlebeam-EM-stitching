# This is a script that helps you match sift features and filter
# based on Rhoana's rh_aligner[https://github.com/Rhoana/rh_aligner].
# We modified it to support single-beam file structure and updated syntax to python3.

# Notice that you have to modified the path in main function to run the file.

# Raw Author: Harvard VCG Group, Rhoana Project[https://github.com/Rhoana]
# Author: Horace.Kem[https://github.com/horacekem]
# Group: Biomed ssSEM Lab, SIBET

from bounding_box import BoundingBox
import ransac
import utils
import json
import cv2
import h5py
import numpy as np
import multiprocessing as mp
import logging
import re
import os
from rh_renderer.models import Transforms

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")
logger_handler = logging.StreamHandler()
logger_handler.setLevel(logging.DEBUG)
logger_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger_handler.setFormatter(logger_formatter)
logger.addHandler(logger_handler)


def load_features(feature_h5_filename):
    try:
        with h5py.File(feature_h5_filename, 'r') as hf:
            image_url = str(hf["imageUrl"][...])
            locations = hf["points/locations"][...]
            responses = None
            scales = None
            descriptors = hf["descriptors"][...]
    except:
        logger.error("Error when reading file {}".format(feature_h5_filename))
        raise
    return image_url, locations, responses, scales, descriptors


def match_features(descriptors1, descriptors2, rod):
    cv_matcher = cv2.BFMatcher()
    all_matches = cv_matcher.knnMatch(descriptors1, descriptors2, k=2)
    good_matches = []
    for m, n in all_matches:
        if m.distance < rod * n.distance:
            good_matches.append([m])
    return good_matches


def get_tile_specification_transformation(tile_specification):
    transforms = tile_specification["transforms"]
    transform = Transforms.from_tilespec(transforms[0])
    return transform


def create_empty_matches_json_file(output_json_filename, image_url1, image_url2):
    matches_specification = [{
        "mipmapLevel": 0,
        "image_url1": image_url1,
        "image_url2": image_url2,
        "correspondencePointPairs": [],
        "model": []
    }]

    logger.info("Saving matches into {}".format(output_json_filename))
    with open(output_json_filename, 'w') as out:
        json.dump(matches_specification, out, sort_keys=True, indent=4)


def distance_after_model(model, point1_l, point2_l):
    point1_l = np.array(point1_l)
    point2_l = np.array(point2_l)
    point1_l_new = model.apply(point1_l)
    delta = point1_l_new - point2_l
    return np.sqrt(np.sum(delta ** 2))


def match_single_pair(tilespec1, tilespec2, feature_h5_filename1, feature_h5_filename2, output_json_filename, rod,
                      iterations, max_epsilon, min_inlier_ratio, min_num_inlier, model_index, max_trust, det_delta):
    logger.info("Loading sift features")
    _, points1, _, _, descriptors1 = load_features(feature_h5_filename1)
    _, points2, _, _, descriptors2 = load_features(feature_h5_filename2)
    logger.info("Loaded {0} features from file: {1}".format(points1.shape[0], feature_h5_filename1))
    logger.info("Loaded {0} features from file: {1}".format(points2.shape[0], feature_h5_filename2))

    min_features_sum = 5
    if points1.shape[0] < min_features_sum or points2.shape[0] < min_features_sum:
        logger.info("Less than {} features (even before overlap) of one of the tiles, saving an empty match json file")
        create_empty_matches_json_file(output_json_filename, tilespec1["mipmapLevels"]["0"]["imageUrl"],
                                       tilespec2["mipmapLevels"]["0"]["imageUrl"])
        return

    # Get the tile specification transforms
    logger.info("Getting transformation")
    tilespec1_transform = get_tile_specification_transformation(tilespec1)
    tilespec2_transform = get_tile_specification_transformation(tilespec2)

    # Filter the features to ensure that only features that are in the overlapping tile will be matches
    bbox1 = BoundingBox.fromList(tilespec1["bbox"])
    logger.info("bbox1 {}".format(bbox1))
    bbox2 = BoundingBox.fromList(tilespec2["bbox"])
    logger.info("bbox2 {}".format(bbox2))
    overlap_bbox = bbox1.intersect(bbox2).expand(offset=50)
    logger.info("overlap_bbox {}".format(overlap_bbox))

    features_mask1 = overlap_bbox.contains(tilespec1_transform.apply(points1))
    features_mask2 = overlap_bbox.contains(tilespec2_transform.apply(points2))

    points1 = points1[features_mask1]
    points2 = points2[features_mask2]
    descriptors1 = descriptors1[features_mask1]
    descriptors2 = descriptors2[features_mask2]
    logger.info("Found {0} features in the overlap from file: {1}".format(points1.shape[0], feature_h5_filename1))
    logger.info("Found {0} features in the overlap from file: {1}".format(points2.shape[0], feature_h5_filename2))

    min_features_sum = 5
    if points1.shape[0] < min_features_sum or points2.shape[0] < min_features_sum:
        logger.info("Less than {} features in the overlap of one of the tiles, saving an empty match json file")
        create_empty_matches_json_file(output_json_filename, tilespec1["mipmapLevels"]["0"]["imageUrl"],
                                       tilespec2["mipmapLevels"]["0"]["imageUrl"])
        return

    logger.info("Matching sift features")
    matches = match_features(descriptors1, descriptors2, rod)
    logger.info("Found {0} possible matches between {1} and {2}".
                format(len(matches), feature_h5_filename1, feature_h5_filename2))

    match_points = np.array([
        np.array([points1[[m[0].queryIdx for m in matches]]][0]),
        np.array([points2[[m[0].trainIdx for m in matches]]][0])
    ])

    model, filtered_matches = ransac.filter_matches(match_points, model_index, iterations, max_epsilon,
                                                    min_inlier_ratio, min_num_inlier, max_trust, det_delta)
    model_json = []
    if model is None:
        filtered_matches = [[], []]
    else:
        model_json = model.to_modelspec()

    out_data = [{
        "mipmapLevel": 0,
        "url1": tilespec1["mipmapLevels"]["0"]["imageUrl"],
        "url2": tilespec2["mipmapLevels"]["0"]["imageUrl"],
        "correspondencePointPairs": [
            {
                "p1": {"w": np.array(tilespec1_transform.apply(p1)[:2]).tolist(),
                       "l": np.array([p1[0], p1[1]]).tolist()},
                "p2": {"w": np.array(tilespec2_transform.apply(p2)[:2]).tolist(),
                       "l": np.array([p2[0], p2[1]]).tolist()},
            } for p1, p2 in zip(filtered_matches[0], filtered_matches[1])
        ],
        "model": model_json
    }]

    logger.info("Saving matches into {}".format(output_json_filename))
    with open(output_json_filename, 'w') as out:
        json.dump(out_data, out, sort_keys=True, indent=4)

    return True


def match_single_sift_features_and_filter(tiles_file, feature_h5_filename1, feature_h5_filename2,
                                          output_json_filename, index_pair):
    parameters = {}
    rod = parameters.get("rod", 0.92)
    iterations = parameters.get("iterations", 1000)
    max_epsilon = parameters.get("maxEpsilon", 100.0)
    min_inlier_ratio = parameters.get("minInlierRatio", 0.01)
    min_num_inlier = parameters.get("minNumInlier", 7)
    model_index = parameters.get("modelIndex", 1)
    max_trust = parameters.get("maxTrust", 3)
    det_delta = parameters.get("delDelta", 0.3)

    logger.info("Matching sift features of tilespecs file: {}, indices: {}".format(tiles_file, index_pair))
    indexed_tilespecs = utils.index_tilespec(utils.load_tile_specifications(tiles_file))
    if index_pair[0] not in indexed_tilespecs:
        logger.info("The given tile_index {0} was not found in the tilespec: {1}".format(index_pair[0], tiles_file))
        return
    if index_pair[1] not in indexed_tilespecs:
        logger.info("The given tile_index {0} was not found in the tilespec: {1}".format(index_pair[1], tiles_file))
        return

    tilespec1 = indexed_tilespecs[index_pair[0]]
    tilespec2 = indexed_tilespecs[index_pair[1]]

    match_single_pair(tilespec1, tilespec2, feature_h5_filename1, feature_h5_filename2, output_json_filename, rod,
                      iterations, max_epsilon, min_inlier_ratio, min_num_inlier, model_index, max_trust, det_delta)


def match_multiple_sift_features_and_filter(tiles_file, features_h5_filename_list1, features_h5_filename_list2,
                                            output_json_filenames, index_pairs, processes_num=10):
    parameters = {}
    rod = parameters.get("rod", 0.92)
    iterations = parameters.get("iterations", 1000)
    max_epsilon = parameters.get("maxEpsilon", 100.0)
    min_inlier_ratio = parameters.get("minInlierRatio", 0.01)
    min_num_inlier = parameters.get("minNumInlier", 7)
    model_index = parameters.get("modelIndex", 1)
    max_trust = parameters.get("maxTrust", 3)
    det_delta = parameters.get("delDelta", 0.3)

    assert (len(index_pairs) == len(features_h5_filename_list1))
    assert (len(index_pairs) == len(features_h5_filename_list2))
    assert (len(index_pairs) == len(output_json_filenames))
    logger.info("Create a pool of {} processed".format(processes_num))
    pool = mp.Pool(processes=processes_num)

    indexed_tilespecs = utils.index_tilespec(utils.load_tile_specifications(tiles_file))
    pool_results = []
    for i, index_pair in enumerate(index_pairs):
        features_h5_filename1 = features_h5_filename_list1[i]
        features_h5_filename2 = features_h5_filename_list2[i]
        output_json_filename = output_json_filenames[i]

        logger.info("Matching sift features of tilespecs file: {}, indices: {}".format(tiles_file, index_pair))
        if index_pair[0] not in indexed_tilespecs:
            logger.info("The given tile_index {0} was not found in the tilespec: {1}".format(index_pair[0], tiles_file))
            continue
        if index_pair[1] not in indexed_tilespecs:
            logger.info("The given tile_index {0} was not found in the tilespec: {1}".format(index_pair[1], tiles_file))
            continue

        tilespec1 = indexed_tilespecs[index_pair[0]]
        tilespec2 = indexed_tilespecs[index_pair[1]]

        res = pool.apply_async(match_single_pair, (tilespec1, tilespec2, features_h5_filename1, features_h5_filename2,
                                                   output_json_filename, rod, iterations, max_epsilon, min_inlier_ratio,
                                                   min_num_inlier, model_index, max_trust, det_delta))
        pool_results.append(res)

        for res in pool_results:
            res.get()

        pool.close()
        pool.join()


def main():
    result_path = '/home/horacekem/Desktop/Stitching/singlebeam/compute_data/down_10/'
    tiles_file = os.path.join(result_path, 'tile_spec/cc_Sec001.json')
    features_filename1 = os.path.join(result_path, 'sift/001/Tile_r2-c2_001_sift_features.h5')
    features_filename2 = os.path.join(result_path, 'sift/001/Tile_r2-c1_001_sift_features.h5')
    output_json_filename = os.path.join(result_path, 'matched_sift/matched_sift_4_3.json')
    index_pairs = ['4:3']
    wait_time = 2

    if len(index_pairs) == 1:
        utils.wait_after_file(features_filename1, wait_time)
        utils.wait_after_file(features_filename2, wait_time)

        m = re.match('([0-9]+):([0-9]+)', index_pairs[0])
        index_pair = (int(m.group(1)), int(m.group(2)))
        match_single_sift_features_and_filter(tiles_file, features_filename1, features_filename2, output_json_filename,
                                              index_pair)
    else:
        with open(features_filename1, 'r') as features_filenames:
            features_h5_filename_list1 = [fname.strip() for fname in features_filenames.readlines()]
        with open(features_filename2, 'r') as features_filenames:
            features_h5_filename_list2 = [fname.strip() for fname in features_filenames.readlines()]
        for feature_file in zip(features_h5_filename_list1, features_h5_filename_list2):
            utils.wait_after_file(feature_file[0], wait_time)
            utils.wait_after_file(feature_file[1], wait_time)
        with open(output_json_filename, 'r') as out_filenames:
            output_json_filenames = [fname.strip() for fname in out_filenames.readlines()]

        for index_pair in index_pairs:
            m = re.match('([0-9]+):([0-9]+)', index_pair)
            index_pairs.append = (int(m.group(1)), int(m.group(2)))
        match_multiple_sift_features_and_filter(tiles_file, features_h5_filename_list1, features_h5_filename_list2,
                                                output_json_filenames, index_pairs, processes_num=10)

    print("Done.")


if __name__ == '__main__':
    main()
