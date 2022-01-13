from math import sqrt

import numpy as np
import cv2

from rdr2_ai.configWindow.configWindow import ConfigWindow
from rdr2_ai.utils.utils import (applyBBox, dilate, erode,
                                 minKernelDifference2D, saveDebugIm)


class MinimapReader:

    def __init__(self, configWindow=None):
        self.configWindow: ConfigWindow = configWindow
        self.minimapBB = None

        D = 8
        P = 12
        self.isolatedCircleKernel = np.zeros((D+2*P,D+2*P))
        for i in range(D):
            for j in range(D):
                x = abs(i - (D-1)/2)
                y = abs(j - (D-1)/2)
                
                if sqrt(x**2 + y**2) < D/2:
                    self.isolatedCircleKernel[P+i,P+j] = 255

        self.targetIcon = cv2.imread('./images/target_icon.png')

    def isolateMinimap(self, frame):
        # crop frame
        if self.minimapBB is None:
            self.updateMinimapBB(frame)
        minimapIm = applyBBox(frame, self.minimapBB)

        self.configWindow.addDrawEvent('rawMinimap', minimapIm)

        return minimapIm

    def getCenterPoint(self, frame=None):
        if self.minimapBB is None:
            if frame is None:
                assert False
            
            self.updateMinimapBB(frame)
        
        x1,y1,x2,y2 = self.minimapBB
        return ((x2-x1)//2 , (y2-y1)//2)

    def getChorePoint(self, frame):
        return self.getPossibleChorePoint(self.isolateMinimap(frame))

    def getPossibleChorePoint(self, minimapIm):
        # only consider black blobs
        blackMask = 255 * np.all(np.isclose(minimapIm, 0, atol=3), axis=2).astype(np.uint8)
        blackMask = dilate(erode(blackMask, i=2), i=2)
        blackMask = 255 * (blackMask > 127).astype(np.uint8)
        
        saveDebugIm(blackMask, desc='blackmask')

        # find best dot
        score, loc = minKernelDifference2D(blackMask, self.isolatedCircleKernel)

        # draw in config
        cv2Loc = np.array(loc[::-1])
        playerLoc = np.array(self.getCenterPoint())
        lineVec = cv2Loc - playerLoc
        unitLineVec = lineVec / sqrt(lineVec[0]**2 + lineVec[1]**2)

        targetIm = np.zeros((*blackMask.shape, 3))
        for c in range(3):
            targetIm[:,:,c] = blackMask

        cv2.circle(targetIm, cv2Loc, 10, (0,0,255), 3)
        lineEnd = (cv2Loc - 25*unitLineVec).astype(int)
        cv2.line(targetIm, playerLoc, lineEnd, (0,255,0), 3)

        # dotIm = np.zeros_like(minimapIm)
        # cnts = cv2.findContours(blackMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        # areaThresh = 25
        # pts = []
        # for c in cnts:
        #     area = cv2.contourArea(c)
        #     if area > areaThresh:
        #         cv2.drawContours(ptsIm, [c], -1, (0,0,255), -1)
        #         moments = cv2.moments(c)
        #         cX = int(moments['m10'] / moments['m00'])
        #         cY = int(moments['m01'] / moments['m00'])
        #         pts.append((cX, cY))
        
        self.configWindow.addDrawEvent('target', targetIm)
        
        return cv2Loc

    def getTargetPoint(self, frame):
        minimapImage = self.isolateMinimap(frame)
        possibleTargetPoint = self.getPossibleTargetPoint(minimapImage)
        return possibleTargetPoint

    def getPossibleTargetPoint(self, minimapIm):
        
        res = cv2.matchTemplate(minimapIm, self.targetIcon, cv2.TM_SQDIFF_NORMED)
        _, _, loc, _ = cv2.minMaxLoc(res)

        topLeft = loc
        bottomRight = (loc[0] + self.targetIcon.shape[1], loc[1] + self.targetIcon.shape[0])

        targetLoc = np.array(((topLeft[0] + bottomRight[0])//2, (topLeft[1] + bottomRight[1])//2))
        playerLoc = np.array(self.getCenterPoint())

        lineVec = targetLoc - playerLoc
        unitLineVec = lineVec / sqrt(lineVec[0]**2 + lineVec[1]**2)
        lineEnd = (targetLoc - 25*unitLineVec).astype(int)

        targetIm = minimapIm.copy()
        cv2.rectangle(targetIm, topLeft, bottomRight, (0,0,255), 3)
        cv2.line(targetIm, playerLoc, lineEnd, (0,255,0), 3)
        self.configWindow.addDrawEvent('target', targetIm)

        return targetLoc

    def updateMinimapBB(self, frame):
        h, w = frame.shape[:2]
        mmSize = 440
        hScale, wScale = h/1417, w/3440

        x1 = int(88 * wScale)
        y1 = int(950 * hScale)
        x2 = x1 + int(mmSize * hScale)
        y2 = y1 + int(mmSize * hScale) # im assuming minimap scales with height?

        self.minimapBB = (x1, y1, x2, y2)
