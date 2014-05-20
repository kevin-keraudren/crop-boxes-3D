#!/usr/bin/python

import sys
import os
import numpy as np
import SimpleITK as sitk
import cv2
from glob import glob
import re
import gc

from scipy.stats.mstats import mquantiles
from scipy.ndimage.interpolation import zoom

######################################################################

def projections(data, transform ):
    data = zoom( data, transform, order=0)
      
    step = 2
    shape = np.array(data.shape).max()
    output = np.ones((shape,shape*3+step*(3-1)))*255

    offset1 = (shape - data.shape[1])/2
    offset2 = (shape - data.shape[2])/2
    output[offset1:offset1+data.shape[1],offset2:offset2+data.shape[2]] = data[data.shape[0]/2,:,:]
    
    offset1 = (shape - data.shape[0])/2
    offset2 = shape + step + (shape - data.shape[2])/2
    output[offset1:offset1+data.shape[0],offset2:offset2+data.shape[2]] = data[:,data.shape[1]/2,:]
    
    offset1 = (shape - data.shape[0])/2
    offset2 = 2*shape + 2*step + (shape - data.shape[1])/2
    output[offset1:offset1+data.shape[0],offset2:offset2+data.shape[1]] = data[:,:,data.shape[2]/2]

    return output

class Cropper:
    def __init__(self, raw_file, output_dir, zyx=None, dhw=None ):
        print "Initialising..."
        self.output_dir = output_dir
        self.raw_file = raw_file

        sitk_img = sitk.ReadImage( self.raw_file )
        self.raw_spacing = sitk_img.GetSpacing()
        self.raw_size = sitk_img.GetSize()

        data = sitk.GetArrayFromImage( sitk_img ).astype("float")
        if zyx is None:
            zyx = np.zeros(3,dtype=int)
            dhw = data.shape

        ## Contrast-stretch with saturation
        q = mquantiles(data.flatten(),[0.01,0.99])
        data[data<q[0]] = q[0]
        data[data>q[1]] = q[1]
        data -= data.min()
        data /= data.max()
        data *= 255

        self.raw_data = data.astype('uint8').copy()
        
        data = zoom( data, [self.raw_spacing[2],
                            self.raw_spacing[1],
                            self.raw_spacing[0]], order=0)
        self.data = data.astype('uint8')

        self.zyx = np.array( map( round, [ zyx[0]*self.raw_spacing[2],
                                           zyx[1]*self.raw_spacing[1],
                                           zyx[2]*self.raw_spacing[0]] ), dtype=int )
        dhw = np.array( map( round, [ dhw[0]*self.raw_spacing[2],
                                      dhw[1]*self.raw_spacing[1],
                                      dhw[2]*self.raw_spacing[0]] ), dtype=int )

        self.x_min = self.zyx[2]
        self.x_max = self.zyx[2]+dhw[2]
        self.y_min = self.zyx[1]
        self.y_max = self.zyx[1]+dhw[1]
        self.z_min = self.zyx[0]
        self.z_max = self.zyx[0]+dhw[0]
        
        self.zyx += dhw/2

        self.show()

        cv2.createTrackbar('Z', 'XY', self.zyx[0],
                           self.data.shape[0]-1, self.XY_trackbar_callback)
        cv2.createTrackbar('Y', 'XZ', self.zyx[1],
                           self.data.shape[1]-1, self.XZ_trackbar_callback)
        cv2.createTrackbar('X', 'YZ', self.zyx[2],
                           self.data.shape[2]-1, self.YZ_trackbar_callback)        
        
        cv2.setMouseCallback("XY", self.XY_callback)
        cv2.setMouseCallback("XZ", self.XZ_callback)
        cv2.setMouseCallback("YZ", self.YZ_callback)

        print "done"

    def save(self):
        name = os.path.basename( raw_file )
        output_name = self.output_dir + "/" + name
        z,y,x,d,h,w = map( lambda x: int(round(x)),
                           [ self.z_min / self.raw_spacing[2],
                             self.y_min / self.raw_spacing[1],
                             self.x_min / self.raw_spacing[0],
                             (self.z_max - self.z_min) / self.raw_spacing[2],
                             (self.y_max - self.y_min) / self.raw_spacing[1],
                             (self.x_max - self.x_min) / self.raw_spacing[0] ]
                           )
        output_name += '_' + '_'.join( map(str,[z,y,x,d,h,w]) )
        output_name += ".png"

        img = projections( self.raw_data[z:z+d+1,
                                         y:y+h+1,
                                         x:x+w+1],
                           [self.raw_spacing[2],
                            self.raw_spacing[1],
                            self.raw_spacing[0]])


        print "Writing:", output_name
        cv2.imwrite( output_name, img )
        
    def show(self):
        opacity = 0.5

        XY = cv2.cvtColor( self.data[self.zyx[0],:,:],
                           cv2.COLOR_GRAY2BGR )
        if self.z_min <= self.zyx[0] <= self.z_max:
            XY[self.y_min:self.y_max+1,
               self.x_min:self.x_max+1] *= (1-opacity)
            XY[self.y_min:self.y_max+1,
               self.x_min:self.x_max+1] += opacity * np.array([0,255,0])
        cv2.imshow( "XY", XY )
        
        XZ = cv2.cvtColor( self.data[:,self.zyx[1],:],
                           cv2.COLOR_GRAY2BGR )
        if self.y_min <= self.zyx[1] <= self.y_max:
            XZ[self.z_min:self.z_max+1,
               self.x_min:self.x_max+1] *= (1-opacity)
            XZ[self.z_min:self.z_max+1,
               self.x_min:self.x_max+1] += opacity * np.array([0,255,0])        
        cv2.imshow( "XZ", XZ )
        
        YZ = cv2.cvtColor( self.data[:,:,self.zyx[2]],
                           cv2.COLOR_GRAY2BGR )
        if self.x_min <= self.zyx[2] <= self.x_max:
            YZ[self.z_min:self.z_max+1,
               self.y_min:self.y_max+1] *= (1-opacity)
            YZ[self.z_min:self.z_max+1,
               self.y_min:self.y_max+1] += opacity * np.array([0,255,0])          
        cv2.imshow( "YZ", YZ )

    def XY_trackbar_callback(self,pos):
        self.zyx[0] = pos # update z
        self.show()
    def XZ_trackbar_callback(self,pos):
        self.zyx[1] = pos # update y
        self.show()
    def YZ_trackbar_callback(self,pos):
        self.zyx[2] = pos # update x
        self.show()        

    def XY_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.pt = (x, y)
        elif (event == cv2.EVENT_MOUSEMOVE) and (flags & cv2.EVENT_FLAG_LBUTTON):
            dx = x - self.pt[0]
            dy = y - self.pt[1]
            self.pt = (x, y)
            if x < self.x_min + (self.x_max - self.x_min)/2:
                self.x_min += dx
            if x > self.x_max - (self.x_max - self.x_min)/2:
                self.x_max += dx
            if y < self.y_min + (self.y_max - self.y_min)/2:
                self.y_min += dy
            if y > self.y_max - (self.y_max - self.y_min)/2:
                self.y_max += dy
            self.x_min = max(0,self.x_min)
            self.y_min = max(0,self.y_min)
            self.x_max = min(self.data.shape[2]-1,self.x_max)
            self.y_max = min(self.data.shape[1]-1,self.y_max)
            self.show()

    def XZ_callback(self, event, x, z, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.pt = (x, z)
        elif (event == cv2.EVENT_MOUSEMOVE) and (flags & cv2.EVENT_FLAG_LBUTTON):
            dx = x - self.pt[0]
            dz = z - self.pt[1]
            self.pt = (x, z)
            if x < self.x_min + (self.x_max - self.x_min)/2:
                self.x_min += dx
            if x > self.x_max - (self.x_max - self.x_min)/2:
                self.x_max += dx
            if z < self.z_min + (self.z_max - self.z_min)/2:
                self.z_min += dz
            if z > self.z_max - (self.z_max - self.z_min)/2:
                self.z_max += dz
            self.x_min = max(0,self.x_min)
            self.z_min = max(0,self.z_min)
            self.x_max = min(self.data.shape[2]-1,self.x_max)
            self.z_max = min(self.data.shape[0]-1,self.z_max)
            self.show()

    def YZ_callback(self, event, y, z, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.pt = (y, z)
        elif (event == cv2.EVENT_MOUSEMOVE) and (flags & cv2.EVENT_FLAG_LBUTTON):
            dy = y - self.pt[0]
            dz = z - self.pt[1]
            self.pt = (y, z)
            if y < self.y_min + (self.y_max - self.y_min)/2:
                self.y_min += dy
            if y > self.y_max - (self.y_max - self.y_min)/2:
                self.y_max += dy
            if z < self.z_min + (self.z_max - self.z_min)/2:
                self.z_min += dz
            if z > self.z_max - (self.z_max - self.z_min)/2:
                self.z_max += dz
            self.y_min = max(0,self.y_min)
            self.z_min = max(0,self.z_min)
            self.y_max = min(self.data.shape[1]-1,self.y_max)
            self.z_max = min(self.data.shape[0]-1,self.z_max)
            self.show()             
                    
######################################################################

data_folder = sys.argv[1]
output_folder = sys.argv[2]

all_files = sorted( glob( data_folder + '/*' ) )

already_fixed = map( lambda x :
                         os.path.basename(x).split(".nii.gz")[0]+".nii.gz",
                     glob( output_folder + "/*") )

for raw_file in all_files:
    print raw_file

    name = os.path.basename(raw_file)

    if name in already_fixed:
        print "already done:", name
        continue
    else:
        cropper = Cropper( raw_file, output_folder )
    cropper.show()
    
    while True:
        ch = 0xFF & cv2.waitKey()         
        if ch == 27 or ch == ord('q'): # ESC
            exit(0)
        if ch == ord(' '): # SPACE
            cropper.save()
            break
        if ch == ord('\n'): # ENTER save nothing
            break

    cv2.destroyAllWindows() 
    gc.collect() # force garbage collection to free memory

