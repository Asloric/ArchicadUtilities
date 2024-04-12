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
threshold = 1
gridmin = 250


FilePath = 'D:\\parcelle.TIF'
ResultPath = 'C:\\tmp\\raster.xyz'

#List = np.array((open(FilePath,"r").read()))
List = np.asarray(Image.open(FilePath))
Newlist = []


def convert(img, target_type_min, target_type_max, target_type):
    for x in range(0,img.shape[1]):
        for y in range(0,img.shape[0]):
            if img[y,x] == -99999.0:
                img[y,x] = 0
    imin = img.min()
    print(imin)
    imax = img.max()

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
