from time import time
from math import floor
from enum import IntEnum,auto
import asyncio

from pyKey import press, pressKey, releaseKey
import pydirectinput as pdi

from rdr2_ai import config
from rdr2_ai.configWindow.configWindow import ConfigWindow
from rdr2_ai.module import Module
from rdr2_ai.controls.mouse import MouseMoveTo


class ActionType(IntEnum):
    TAP     = auto()
    HOLD    = auto()
    RELEASE = auto()
    MOVE    = auto()
    PAUSE   = auto()
    DONE    = auto()

class ActionHandler(Module):

    def __init__(self, configWindow: ConfigWindow,
                       showInConfigWindow: bool = False,
                       printHeld = False):
        self.keyPressLength = config.keyPressLength
        self.mousePressLength = config.mousePressLength
        
        self.mouseMoveMinTime = 1/50
        self.mouseMoveMinDist = 10

        self.heldKeys = {}
        self.pressedKeys = {}
        
        self.printHeld = printHeld
        self.configWindow = configWindow
        self.showInConfigWindow = showInConfigWindow

    def isDoneAction(self,action):
        return action[0] == ActionType.DONE
    
    def handleActions(self, actions):
        return asyncio.run(self.handleActionsAsync(actions))

    async def handleActionsAsync(self, actions):
        cont = True

        for i, action in enumerate(actions):
            if self.isDoneAction(action):
                self.print(f'got done action.')
                cont = False
                lastIndex = i
                break
        else:
            lastIndex = len(actions)
        
        # ensure no actions after 'done' are run
        actions = actions[:lastIndex]

        if actions:
            await asyncio.gather(*[self.doAction(action) for action in actions])

        if self.printHeld:
            self.printHeldKeys()

        return cont            

    async def doAction(self, action):
        # whole thing needs a refactor

        actionType, key = action

        self.print(f'doing action ({actionType},{key})')

        if actionType == ActionType.TAP:
            if key in self.heldKeys:
                self.print(f'attempted to tap key already held [key={key}]')
                return False
            
            self.pressedKeys[key] = time()
            if key.startswith('MOUSE'):
                if key == 'MOUSE_LEFT':
                    pdiButton = pdi.LEFT
                elif key == 'MOUSE_RIGHT':
                    pdiButton = pdi.RIGHT
                else:
                    self.print(f'unknown mouse button {key} in actionHandler')
                    return False
                
                pdi.mouseDown(button=pdiButton)
                await asyncio.sleep(self.mousePressLength)
                pdi.mouseUp(button=pdiButton)
            else:
                pressKey(key=key)
                await asyncio.sleep(self.keyPressLength)
                releaseKey(key=key)

        elif actionType == ActionType.HOLD:
            if key in self.heldKeys:
                self.print(f'attempted to hold key already held [key={key}]')
            else:
                if key.startswith('MOUSE'):
                    if key == 'MOUSE_LEFT':
                        pdiButton = pdi.LEFT
                    elif key == 'MOUSE_RIGHT':
                        pdiButton = pdi.RIGHT
                    else:
                        self.print(f'unknown mouse button {key} in actionHandler')
                        return False
                    
                    pdi.mouseDown(button=pdiButton)
                else:
                    pressKey(key=key)
                
                self.heldKeys[key] = time()
        
        elif actionType == ActionType.RELEASE:
            if key == 'ALL':
                self.releaseAll()
            elif key not in self.heldKeys:
                self.print(f'attemped to release key not held [key={key}]')
            else:
                if key.startswith('MOUSE'):
                    if key == 'MOUSE_LEFT':
                        pdiButton = pdi.LEFT
                    elif key == 'MOUSE_RIGHT':
                        pdiButton = pdi.RIGHT
                    else:
                        self.print(f'unknown mouse button {key} in actionHandler')
                        return False
                    
                    pdi.mouseUp(button=pdiButton)
                else:
                    releaseKey(key=key)
                
                self.heldKeys.pop(key)

        elif actionType == ActionType.MOVE:
            xOff,yOff,dt,iters = await self.getMouseMoveParams(key)
            for _ in range(iters):
                st = time()
                MouseMoveTo(xOff, yOff, 0)
                await asyncio.sleep(max(dt - (time()-st),0))
            
        elif actionType == ActionType.PAUSE:
            await asyncio.sleep(key)

        return True
    
    async def getMouseMoveParams(self, reqParams):
        xOff,yOff,dur = reqParams

        dist = (xOff ** 2 + yOff ** 2) ** 0.5

        # the following must hold:
        # dist / numDiv > self.mouseMoveMinDist
        # dur / numDiv > self.mouseMoveMinTime

        numDiv = floor(min(dist / self.mouseMoveMinDist,
                           dur  / self.mouseMoveMinTime))
        
        divXOff = int(round(xOff / numDiv))
        divYOff = int(round(yOff / numDiv))
        dt = dur / numDiv

        return divXOff,divYOff,dt,numDiv
    
    def getHeldKeysByTime(self):
        keysAndTimePressed = self.heldKeys.items()
        keysByTimePressed = map(lambda t: t[0],
                                sorted(keysAndTimePressed, key=lambda t: t[1]))
        return list(keysByTimePressed)

    def printHeldKeys(self):
        keysByTimePressed = self.getHeldKeysByTime()
        self.print(f'held keys = {keysByTimePressed}')

    def showHeldKeysInConfigWindow(self):
        keysByTimePressed = self.getHeldKeysByTime()
        keysStr = '\n'.join(keysByTimePressed)

        self.configWindow.drawToTemplate('heldKeys', keysStr)

    def releaseAll(self):
        for key in list(self.heldKeys.keys()):
            if key.startswith('MOUSE'):
                if key == 'MOUSE_LEFT':
                    pdiButton = pdi.LEFT
                elif key == 'MOUSE_RIGHT':
                    pdiButton = pdi.RIGHT
                else:
                    self.print(f'unknown mouse button {key} in actionHandler releaseAll')
                
                pdi.mouseUp(button=pdiButton)
            else:
                releaseKey(key=key)

            self.heldKeys.pop(key)
