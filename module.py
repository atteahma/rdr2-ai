from time import time
import os

# top level module for logging purposes
class Module:

    PR_INDENT_AMT = 16
    PR_MAX_SEC = 10_000
    PR_START_TIME = time()

    def print(self, s, end: str = '\n', flush: bool = False):

        className = type(self).__name__

        whiteSpaceA = ' '*(Module.PR_INDENT_AMT - len(className))

        deltaTime = time() - Module.PR_START_TIME
        timeMilli = int(round(deltaTime, 3) * 1000) % (1000 * Module.PR_MAX_SEC)
        timeStr = str(timeMilli).zfill(len(str(1000 * Module.PR_MAX_SEC)))
        
        whiteSpaceB = ' '*2

        pidStr = str(os.getpid()).zfill(8)

        whiteSpaceC = ' '*2

        outStr = f'[{className}]{whiteSpaceA}{timeStr}{whiteSpaceB}{pidStr}{whiteSpaceC}{s}'
        print(outStr, end=end, flush=flush)
