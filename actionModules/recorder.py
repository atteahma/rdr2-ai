import os

import cv2

from rdr2_ai.module import Module


class Recorder(Module):

    def __init__(self, recordDir, replace=True):
        self.recordDir = os.path.join('.', 'debug_ims', recordDir)
        if not os.path.isdir(self.recordDir):
            os.mkdir(self.recordDir)
        
        self.delim = '_'

        self.frameIndex = 0
        if not replace:
            for file in os.listdir(self.recordDir):
                try:
                    fnum = int(file.rstrip('.jpg').split(self.delim)[-1])
                    self.frameIndex = max(fnum, self.frameIndex)
                except:
                    pass
            self.frameIndex += 1
    
    def getActions(self, frame):
        filename = 'frame'
        filename += self.delim + str(self.frameIndex)
        filename += '.jpg'
        
        filepath = os.path.join(self.recordDir, filename)
        cv2.imwrite(filepath, frame)

        self.print('saved frame')

        self.frameIndex += 1

        return [], True