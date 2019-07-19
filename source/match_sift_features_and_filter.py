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
            locations = hf["pts/locations"][...]
            responses = None
            scales = None
            descs = hf["descs"][...]
    except:
        logger.error("Error when reading file {}".format(feature_h5_filename))
        raise
    return image_url, locations, responses, scales, descs


def match_features(descs1, descs2, rod):
    cv_matcher = cv2.BFMatcher()
    all_matches = cv_matcher.knnMatch(descs1, descs2, k=2)
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


def match_single_pairs(ts1, ts2, feature_h5_filename1, feature_h5_filename2, output_json_filename, rod, iterations,
                       max_epsilon, min_inlier_ratio, min_num_inlier, model_index, max_trust, det_delta):
    logger.info("Loading sift features")
    _, pts1, _, _, descs1 = load_features(feature_h5_filename1)
    _, pts2, _, _, descs2 = load_features(feature_h5_filename2)
    logger.info("Loaded {} features from file: {}".format(pts1.shape[0], feature_h5_filename1))
    logger.info("Loaded {} features from file: {}".format(pts2.shape[0], feature_h5_filename2))

    min_features_sum = 5
    if pts1.shape[0] < min_features_sum or pts2.shape[0] < min_features_sum:
        logger.info("Less than {} features (even before overlap) of one of the tiles, saving an empty match json file")
        create_empty_matches_json_file(output_json_filename, ts1["mipmapLevels"]["0"]["imageUrl"],
                                       ts1["mipmapLevels"]["0"]["imageUrl"])
        return

    # Get the tile specification transforms
    logger.info("Getting transformation")
    ts1_transform = get_tile_specification_transformation(ts1)
    ts2_transform = get_tile_specification_transformation(ts2)

    # Filter the features to ensure that only features that are in the overlapping tile will be matches
    bbox1
