import numpy as np

from timerUtility.timer import Timer

from rdr2_ai.module import Module


class TimeSeries(Module):

    def __init__(self, bufferLength: int,
                       dtype: type = np.float32):
        self.dataBuffer = np.array([0 for _ in range(bufferLength)])
    
    def logDataPoint(self, dataPoint):
        self.dataBuffer = np.roll(self.dataBuffer, 1)
        self.dataBuffer[0] = dataPoint
    
    def raw(self):
        return self.dataBuffer.copy()

    def mean(self):
        return np.mean(self.dataBuffer)
    
    def diff(self):
        return self.dataBuffer[1:] - self.dataBuffer[:-1]
    
    def qStepSmooth(self, q):
        fil = np.ones(q, dtype=float) / q
        return np.convolve(self.dataBuffer, fil, mode='same')
    
    def expSmooth(self, alpha):
    
        fil = np.array(
            [
                (1 - alpha) * alpha**(j-1)
                for j in range(len(self.dataBuffer),0,-1)
            ]
        )
        fullConv = np.convolve(self.dataBuffer, fil, mode='full')
        return fullConv[len(self.dataBuffer)-1:]

