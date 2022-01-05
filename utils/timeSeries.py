import numpy as np

from timerUtility.timer import Timer

from rdr2_ai.module import Module


'''
future plans...

i got too excited once.
'''


class TimeSeries(Module):

    def __init__(self, bufferLength: int,
                       dtype: type = np.float32):
        self.dataBuffer = np.array([np.NaN for _ in range(bufferLength)])