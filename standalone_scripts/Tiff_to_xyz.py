# Tiff_to_xyz.py - Standalone terrain heightmap converter.
# NOT part of the Blender addon. Run directly as a Python script.
#
# Purpose: Convert a GeoTIFF or heightmap TIFF image to an XYZ point cloud text file
# which can be imported into Archicad or other tools as a terrain surface.
#
# Strategy:
#   1. Load TIFF as a numpy array (may contain float elevations or 16-bit values)
#   2. Normalize pixel values 0-255 (handles nodata sentinel -99999 → 0)
#   3. Gaussian blur + diff = edge detection (high-change areas = important terrain features)
#   4. Write edge pixels + a sparse grid (every gridmin pixels) to reduce total point count
#
# NOTE: Paths are hardcoded below. Change before use.
import os
import math
import numpy as np
import subprocess
import sys
import pip

import PIL
from PIL import Image
from PIL import ImageFilter
from PIL import ImageChops
threshold = 1    # Pixel difference > threshold → classified as edge point (included in output)
gridmin = 250    # Sparse grid step: output one point every gridmin pixels for terrain base coverage


FilePath = 'D:\\parcelle.TIF'
ResultPath = 'C:\\tmp\\raster.xyz'

#List = np.array((open(FilePath,"r").read()))
List = np.asarray(Image.open(FilePath))
Newlist = []


def convert(img, target_type_min, target_type_max, target_type):
    # Replace nodata sentinel value -99999 (common in GIS rasters) with 0 before normalizing.
    for x in range(0,img.shape[1]):
        for y in range(0,img.shape[0]):
            if img[y,x] == -99999.0:
                img[y,x] = 0
    imin = img.min()
    print(imin)
    imax = img.max()
    # Linear normalization: maps [imin, imax] → [target_type_min, target_type_max]
    a = (target_type_max - target_type_min) / (imax - imin)
    b = target_type_max - a * imax
    new_img = (a * img + b).astype(target_type)
    return new_img

newimage = Image.fromarray(convert(List, 0, 255, np.uint8))


blurImage = newimage.filter(ImageFilter.GaussianBlur(2))
Diff = PIL.ImageChops.difference(blurImage, newimage)
Diff = Diff.point(lambda p: p > threshold and 255)  
#Diff.save('D:\\Users\\Asloric\\Documents\\Workspace\\Work\\Ensam\\S8\\Projet\\archicad\\Emprise projet blur.tif')
Mask = np.asarray(Diff)
Diff.show()
for x in range(0,List.shape[1]):
    print(x)
    for y in range(0,List.shape[0]):
        if Mask[x,y] == 255:
            Newlist.append(f"{x} {y} {List[x,y]}\n")

for x in range(0,List.shape[1],gridmin):
    print(x)
    for y in range(0,List.shape[0],gridmin):
        Newlist.append(f"{x} {y} {List[x,y]}\n")
        
f = open(ResultPath,"w")                         
for w in range(len(Newlist)):
    #print(Newlist[w])
    f.write(Newlist[w])
f.close()
