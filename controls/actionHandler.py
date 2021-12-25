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
                       showInConfigWindow: bool = False):
        self.keyPressLength = config.keyPressLength
        self.mousePressLength = config.mousePressLength
        
        self.mouseMoveMinTime = 1/50
        self.mouseMoveMinDist = 10

        self.heldKeys = {}
        self.pressedKeys = {}
        
        self.configWindow = configWindow
        self.showInConfigWindow = showInConfigWindow

    async def isDoneAction(self,action):
        return action[0] == ActionType.DONE
    
    async def handleActions(self, actions):
        cont = True
        for action in actions:
            isDone = await self.isDoneAction(action)
            if isDone:
                self.print(f'finished!')
                cont = False
                break

            success = await self.doAction(action)
            if not success:
                self.print(f'error in doAction [action={action}]')
        return cont


    """
    returns success
    """
    async def doAction(self,action):

        actionType,key = action

        self.print(f'doing action ({actionType},{key})')

        if actionType == ActionType.TAP:
            if key in self.heldKeys:
                self.print(f'attempted to tap key already held [key={key}]')
            else:
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
                    press(key=key,sec=self.keyPressLength)

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
                await self.releaseAll()
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

        # if self.showInConfigWindow and self.configWindow:
        #     self.showHeldKeysInConfigWindow()

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

    async def releaseAll(self):
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
