from time import time

from rdr2_ai.module import Module


class Food(Module):

    # this entire architecture will not work with my main architecture
    # whole thing might need a rethink

    def __init__(self, checkInterval: int = 10 * 60):
        self.checkInterval = checkInterval

        self.lastCheckTime: float = -1.0
    
    def tick(self):
        currTime = time()

        if self.lastCheckTime < 0:
            self.lastCheckTime = currTime

        timeSinceLastCheck = currTime - self.lastCheckTime
        if timeSinceLastCheck > self.lastCheckTime:
            self.checkHungerLevels()

    def checkHungerLevels(self):
        self.timeSinceLastCheck = time()

        while self.shouldEat():
            self.print('Player needs to eat.')
            self.doEat()

    def shouldEat(self):
        pass
    
    def doEat(self):
        pass
