# -*- coding: utf-8 -*-
"""
Created on Mon Apr 08 12:25:34 2013

@author: Aman
"""
import numpy as np
import matplotlib.pyplot as plt
from scipy import *
from scipy.signal import *
import Shot
import itertools

def GenerateData(pairs, length):
    aScanArray = np.zeros(length)
    for pair in pairs:
        aScanArray[pair[1]] = pair[0]
    x = linspace(-0.05,0.05,200)

    gaussianFun = (gausspulse(x,100,bw = 0.3))

    fun = np.convolve(aScanArray,gaussianFun, 'same')[:length]
    return fun

def GenerateLayer(num_points,startPoint, endPoint):
    #Create random amplitude data
    amplitude = np.random.randint(low = 100,high = 500,size = num_points)
    position = np.random.randint(low = startPoint , high = endPoint, size = num_points)

    pairData = zip(amplitude,position)
    return pairData

if __name__ == "__main__":
    scan = 100
    index = 20
    num_points = scan * index
    positions = itertools.product(np.arange(0, index, 1), np.arange(0, scan, 1))
    shotwrite = Shot.ShotWriter('test.mdb')
    shotwrite.writeAxisInfo((0, scan, 1), (0, index, 1))
    length = 1352
    spacing = (1,1,1)
    datatype = 'Short'
    dimension = (length,1,1)
    udd = """<?CustomInfo CultureInfo=?><Section Name="Parameters"><Param Name="Version" Value="131072000" /><Param Name="DataFormat" Value="RF" /><Param Name="DataType" Value="Short" /><Section Name="ImageAttributes"><Param Name="NoOfComponents" Value="1" /><Param Name="Modified" Value="True" /><Section Name="Dimensions"><Param Name="X" Value="1352" /><Param Name="Y" Value="1" /><Param Name="Z" Value="1" /></Section><Section Name="Origin"><Param Name="X" Value="%f" /><Param Name="Y" Value="%f" /><Param Name="Z" Value="0" /></Section><Section Name="Spacing"><Param Name="X" Value="1" /><Param Name="Y" Value="1" /><Param Name="Z" Value="1" /></Section></Section></Section>"""

    layer1 = GenerateLayer(num_points,100,120)
    layer2 = GenerateLayer(num_points,250,270)
    layer3 = GenerateLayer(num_points,400,450)
    layer4 = GenerateLayer(num_points,860,930)
    layer5 = GenerateLayer(num_points,1200, 1300)
    layerData = zip(layer1, layer2, layer3, layer4, layer5)
    shotData = zip(positions, layerData)

    for shot in shotData:
        origin, pairs = shot
        filename = '%f %f.dat'%(origin[1], origin[0])
        ascan = GenerateData(pairs, length)
        shotwrite.write(filename, ascan.astype(np.short), (origin[1], 0, origin[0]), spacing, dimension, udd%(origin[1], origin[0]), datatype, 131072000)
        print len(ascan)

    shotwrite.close()
