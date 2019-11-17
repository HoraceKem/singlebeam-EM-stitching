# EM-stitching
Some scripts for single-beam ssSEM images stitching based on Rhoana's rh-aligner.

## System
Ubuntu 18.04
## Enviroment preparation
+ Download the relevant packages.  
`git clone git@github.com:horacekem/singlebeam-EM-stitching`(this repo)  
`git clone git@github.com:Rhoana/tinyr`  
`git clone git@github.com:Rhoana/rh_renderer`  
+ Create conda environment.  
`conda create single_stitch -n python=3.7`  
`conda activate single_stitch`  
+ Switch to this repo's folder  
`pip install -r requirements.txt`  
`conda install opencv=3.4.2`  
+ Switch to tinyr's folder  
`python setup.py install`  
+ Switch to rh_renderer's folder  
`export PKG_CONFIG_PATH=/home/YOUR_USER_NAME/anaconda3/envs/singe_stitch/lib/pkgconfig/`  
`python setup.py install`  
## How to
+ Switch to this repo's folder/source
+ Modify the arguments in arguments.txt  
+ Run stitching_driver.py
