from math import ceil

import cv2
import numpy as np
from mss.windows import MSS as mss
from win32 import win32gui

from rdr2_ai.module import Module
from rdr2_ai.utils.winGuiAuto import findTopWindow

class Capture(Module):

    BORDER_CUT = 8
    RIBBON_CUT = 23

    def __init__(self, windowKeyword: str, updateWindow: bool = True):
        self.hwnd = findTopWindow(windowKeyword)
        self.sct = mss()
        if not updateWindow:
            self.windowRect = self.getMSSWindowRect()
        self.updateWindow = updateWindow

    def captureWindow(self):
        if self.updateWindow:
            self.windowRect = self.getMSSWindowRect()
        
        frame = np.asarray(self.sct.grab(self.windowRect))

        # do this conversion in the return using slicing for speed
        #frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        return frame[Capture.BORDER_CUT+Capture.RIBBON_CUT : -1*Capture.BORDER_CUT,
                     Capture.BORDER_CUT                    : -1*Capture.BORDER_CUT,
                     :3] # cut out window ribbon HACK

    def getMSSWindowRect(self):
        x1,y1,x2,y2 = win32gui.GetWindowRect(self.hwnd)
        return {'left': x1, 'top': y1, 'width': x2-x1, 'height': y2-y1}

    def getRawWindowSize(self):
        x1,y1,x2,y2 = win32gui.GetWindowRect(self.hwnd)
        xSize = ceil(abs(x2 - x1) / self.stepSize)
        ySize = ceil(abs(y2 - y1) / self.stepSize)
        return ySize,xSize

    def clean(self):
        self.sct.close()