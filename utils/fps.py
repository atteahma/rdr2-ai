from time import time

from rdr2_ai.module import Module


class FPSCounter(Module):

    def __init__(self, configWindow=None):
        self.configWindow = configWindow
        self.frameStartTime = None
        
    def tick(self):

        if self.frameStartTime:        
            currFPS = round(1/(time() - self.frameStartTime))
            if self.configWindow:
                self.configWindow.drawToTemplate('fps', str(currFPS))
            else:
                self.print(f'Frames/s = {currFPS}')
        
        self.frameStartTime = time()
    
    def cleanup(self):
        pass