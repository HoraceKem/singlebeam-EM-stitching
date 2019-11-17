# This is a file copied from Rhoana's rh_renderer[https://github.com/Rhoana/rh_renderer].

# Raw Author: Harvard VCG Group, Rhoana Project[https://github.com/Rhoana]
# Author: Horace.Kem[https://github.com/horacekem]
# Group: Biomed ssSEM Lab, SIBET

# Renders a given tilespec as is in full resolution
from __future__ import print_function
import pylab
from rh_renderer.tilespec_renderer import TilespecRenderer
import numpy as np
import time
import json
from rh_renderer import models


def render_tile(file_name):
    with open(file_name, 'r') as data:
        tilespec = json.load(data)
    # Create the tilespec renderer
    renderer1 = TilespecRenderer(tilespec)
    start_time = time.time()
    img1, start_point1 = renderer1.render()
    print("Start point is at:", start_point1, "image shape:", img1.shape, "took: {} seconds".format(time.time() - start_time))
    pylab.figure()
    pylab.imshow(img1, cmap='gray', vmin=0., vmax=255.)
    pylab.show()
