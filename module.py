from time import time

# top level module for logging purposes
class Module:

    PR_INDENT_AMT = 16
    PR_MAX_SEC = 10_000

    def print(self, s, end: str = '\n', flush: bool = False):

        if not hasattr(self, 'pr_start_time'):
            self.pr_start_time = time()

        className = type(self).__name__

        whiteSpace = ' '*(Module.PR_INDENT_AMT - len(className))

        deltaTime = time() - self.pr_start_time
        timeMilli = int(round(deltaTime, 3) * 1000) % (1000 * Module.PR_MAX_SEC)
        timeStr = str(timeMilli).zfill(len(str(1000 * Module.PR_MAX_SEC)))

        outStr = f'[{className}]{whiteSpace}{timeStr}  {s}'
        print(outStr, end=end, flush=flush)
