from itertools import combinations
from time import time
import math

import cv2
import numpy as np
from numba import njit

from rdr2_ai.config import freqMistakes

def applyBBox(frame, boundingBox):
    x1,y1,x2,y2 = boundingBox
    boundedFrame = frame[y1:y2,x1:x2]
    return boundedFrame

def dilate(image, k=3, i=3):
    kernel = np.ones((k,k),np.uint8)
    return cv2.dilate(image, kernel, iterations=i)

def erode(image, k=3, i=3):
    kernel = np.ones((k,k),np.uint8)
    return cv2.erode(image, kernel, iterations=i)

def segmentImage(im,minGap=25,pad=5,bgColor=0,axis=0):
    h = im.shape[0]

    hor_lines = np.nonzero(np.all((im == bgColor),axis=~axis))[0]
    bottom_edges = (hor_lines-1)[1:]
    upper_edges = (hor_lines+1)[:-1]
    
    mask = (bottom_edges - minGap) > upper_edges
    upper_edges = np.clip(upper_edges[mask] - pad,0,h)
    bottom_edges = np.clip(bottom_edges[mask] + pad,0,h)
    
    seperators = np.sort(np.concatenate((upper_edges,bottom_edges)))
    
    return np.split(im,seperators,axis=axis)[1::2]

def cropCenter(im,scale=-1,scaleW=-1,scaleH=-1):

    if scale > 0:
        scaleW = scale
        scaleH = scale
    
    h,w = im.shape[:2]
    xOff = w - int(scaleW * w)
    yOff = h - int(scaleH * h)

    return im[yOff:-yOff,xOff:-xOff]

def closeEnough(A,B,n=1):

    if abs(len(A) - len(B)) > n:
        return False

    for r in range(1,len(freqMistakes)+1):
        for replacements in combinations(freqMistakes,r):

            Atemp = A[:]
            for replacement in replacements:
                Atemp = Atemp.replace(*replacement)
            
            if Atemp == B:
                return True
        
        for replacements in combinations(freqMistakes,r):

            Btemp = B[:]
            for replacement in replacements:
                Btemp = Btemp.replace(*replacement)
            
            if A == Btemp:
                return True

    if len(A) == len(B):
        minW,minL = A,len(A)
        maxW,maxL = B,len(B)
    else:
        minW,minL = min([(A,len(A)),(B,len(B))] , key=lambda p: p[1])
        maxW,maxL = max([(A,len(A)),(B,len(B))] , key=lambda p: p[1])
    
    for i in range(maxL - minL):
        subW = maxW[ i : i+minL ]

        numWrong = 0
        for a,b in zip(subW,minW):
            if a != b:
                numWrong += 1
        
        if numWrong <= n:
            return True

    return False

def anyCloseEnough(a,lst,n=1):
    for b in lst:
        if closeEnough(a,b,n=n):
            return True
    return False

def allAnyCloseEnough(lstA,lstB,n=1,k=0):
    numWrong = 0
    for a in lstA:
        if not anyCloseEnough(a,lstB,n=n):
            numWrong += 1
    return numWrong <= k

@njit
def minKernelDifference2D(im, kernel):
    imH, imW = im.shape
    keH, keW = kernel.shape

    minDiff = 1e20
    minIndex = (-1, -1)
    for i in range(imH - keH):
        for j in range(imW - keW):
            subIm = im[i:i+keH , j:j+keW]
            diff = np.sum(np.square(subIm - kernel))

            if diff < minDiff:
                minDiff = diff
                minIndex = (keH//2 + i, keW//2 + j)

    return minDiff, minIndex

def saveDebugIm(im, desc=''):
    fname = f'./debug_ims/frame_{desc}_{time()}.jpg'
    cv2.imwrite(fname, im)

def calculateDistance(base, other):
    base = np.array(base)
    other = np.array(other)
    dirVec = other - base
    return  np.linalg.norm(dirVec)

def calculateAngle(base, other):
    base = np.array(base) * -1
    other = np.array(other) * -1
    dirVec = other - base
    dirVecNorm = dirVec / np.linalg.norm(dirVec)
    angle = np.arctan2(dirVecNorm[1],dirVecNorm[0])
    return angle

def getRelative(base,vec):
    return np.divide(vec,base.shape[:2])

def rotate(vec, rads):

    x = vec[1]
    y = vec[0]

    newX = x*math.cos(rads) - y*math.sin(rads)
    newY = y*math.sin(rads) + y*math.cos(rads)

    return np.array((newY,newX), np.uint8)