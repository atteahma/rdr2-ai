import cv2
import numpy as np
from desktopmagic.screengrab_win32 import getRectAsImage
from win32 import win32gui

from rdr2_ai.module import Module
from rdr2_ai.utils.winGuiAuto import findTopWindow

class Capture(Module):

    BORDER_CUT = 8
    RIBBON_CUT = 23

    def __init__(self, windowKeyword: str, updateWindow: bool = True):
        self.hwnd = findTopWindow(windowKeyword)
        if updateWindow:
            self.windowPos = None
        else:
            self.windowPos = win32gui.GetWindowRect(self.hwnd)

    def captureWindow(self):
        if self.windowPos:
            position = self.windowPos
        else:
            position = win32gui.GetWindowRect(self.hwnd)
        
        frame = getRectAsImage(position)
        frame = np.array(frame)

        # do this conversion in the return using slicing for speed
        #frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        return frame[Capture.BORDER_CUT+Capture.RIBBON_CUT : -1*Capture.BORDER_CUT,
                     Capture.BORDER_CUT                    : -1*Capture.BORDER_CUT,
                     ::-1] # cut out window ribbon HACK

    def getWindowSize(self):
        boundingBox = win32gui.GetWindowRect(self.hwnd)
        x1,y1,x2,y2 = boundingBox
        xSize = abs(x2 - x1)
        ySize = abs(y2 - y1)

        return (xSize-2*Capture.BORDER_CUT,
                ySize-2*Capture.BORDER_CUT-Capture.TOP_CUT_EXTRA)
