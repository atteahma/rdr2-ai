import numpy as np

from rdr2_ai.module import Module

class PauseMenu(Module):

    RED_THRESH = 150
    OTHER_THRESH = 5
    PX_THRESH = 0.75
    SKIP = 10

    def __init__(self):
        pass

    def gameIsPaused(self, frame):
        
        # menu should take up all left 500 px
        leftFrame = frame[:   :PauseMenu.SKIP,
                          :500:PauseMenu.SKIP]
        H, W, C = leftFrame.shape
        leftPx = leftFrame.reshape((H * W, C))
        
        # get counts of unique pixels
        pxs, cnts = np.unique(leftPx, axis=0, return_counts=True)
        
        # get number of red pixels
        redMask = (pxs[:,0] < PauseMenu.OTHER_THRESH) & (pxs[:,1] < PauseMenu.OTHER_THRESH) & (pxs[:,2] > PauseMenu.RED_THRESH)
        numRedPx = np.sum(cnts[redMask])
        numTotPx = H*W

        # if over PX_THRESH are red, then we are in the pause menu
        return (numRedPx / numTotPx) > PauseMenu.PX_THRESH
    