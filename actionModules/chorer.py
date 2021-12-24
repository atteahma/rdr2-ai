from enum import Enum

import numpy as np

from rdr2_ai.configWindow.configWindowTemplate import ConfigWindowTemplate,ContentType
from rdr2_ai.module import Module
from rdr2_ai.controls.actionHandler import ActionType
from rdr2_ai.analysisModules.options import OptionsGetter
from rdr2_ai.analysisModules.minimap import MinimapReader
from rdr2_ai.utils.utils import calculateAngle, calculateDistance


chorerConfigWindowTemplate = ConfigWindowTemplate()
chorerConfigWindowTemplate \
    .setSize(height=525, width=1600) \
    .addStaticText('Raw Minimap', (25,25), (50,400)) \
    .addContentBox('rawMinimap', ContentType.Image, (100,25), (400,400)) \
    .addStaticText('Target', (25, 425 + 25), (50,400)) \
    .addContentBox('target', ContentType.Image, (100, 425 + 25), (400,400))

class ChoreType(Enum):
    CHOP = 'chop'
    HAUL = 'haul'

class ChoreState(Enum):
    FINDCHORES = 'findchores'
    GOTOCHORE = 'gotochore'
    DOINGCHORE = 'doingchore'

class Chorer(Module):

    def __init__(self, configWindow=None):
        self.configWindow = configWindow
        self.optionsGetter = OptionsGetter(configWindow=configWindow)
        self.minimapReader = MinimapReader(configWindow=configWindow)
        self.currChoreState = ChoreState.GOTOCHORE # change to findchores once implemented
        self.currChoreType = None

    def getActionsForMove(self, playerPoint, targetPoint):
        choreX, choreY = targetPoint
        playerX, playerY = playerPoint

        actions = []
        done = False

        rotationThresh = np.pi / 8
        distanceThresh = 40
        dist = calculateDistance((playerY, playerX), (choreY, choreX))
        angle = calculateAngle((playerY, playerX), (choreY, choreX))
        if abs(angle) > rotationThresh:
            # first make sure we are rotationally aligned
            turnMagnitude = 100
            if angle > 0:
                # turn left
                turnMagnitude *= -1
            
            actions.append((ActionType.RELEASE,'w'))
            numMouseMoves = 10
            for _ in range(numMouseMoves):
                actions.append((ActionType.MOVE,(turnMagnitude//numMouseMoves,0,-1)))

        elif dist > distanceThresh:
            # we are already aligned, move forward
            actions.append((ActionType.HOLD, 'w'))
        else:
            # we are (hopefully) done
            actions.append((ActionType.RELEASE, 'w'))
            done = True
        
        return actions, done

    def getActions(self, frame):
        
        actions = []

        if self.currChoreState is ChoreState.FINDCHORES:
            # walk around until a chore is found
            pass
        elif self.currChoreState is ChoreState.GOTOCHORE:
            targetPoint = self.minimapReader.getChorePoint(frame)
            playerPoint = self.minimapReader.getPlayerPoint(frame)

            moveActions, done = self.getActionsForMove(playerPoint, targetPoint)
            actions.extend(moveActions)

            if done:
                # check options to make sure we are in fact at the chore
                options, _ = self.optionsGetter.getOptions(frame)
                if 'chop' in options or 'pick up' in options:
                    self.currChoreState = ChoreState.DOINGCHORE

                    if 'chop' in options:
                        self.currChoreType = ChoreType.CHOP
                        # actions.append((ActionType.HOLD, ''))
                    elif 'pick up' in options:
                        self.currChoreType = ChoreType.HAUL
                        actions.append((ActionType.HOLD, 'e'))
                        actions.append((ActionType.PAUSE, 1))
                        actions.append((ActionType.RELEASE, 'e'))
                
        elif self.currChoreState is ChoreState.DOINGCHORE:
            if self.currChoreType is ChoreType.CHOP:
                # click stuff
                pass
            elif self.currChoreType is ChoreType.HAUL:
                # move stuff
                
                # find target to bring item to
                targetPoint = self.minimapReader.getTargetPoint(frame)
                playerPoint = self.minimapReader.getPlayerPoint(frame)

                moveActions, done = self.getActionsForMove(playerPoint, targetPoint)
                actions.extend(moveActions)
                
                if done:
                    # check options to make sure we are in fact at the chore
                    options, _ = self.optionsGetter.getOptions(frame)
                    if 'put down' in options:
                        self.currChoreState = ChoreState.FINDCHORES

                        actions.append((ActionType.HOLD, 'e'))
                        actions.append((ActionType.PAUSE, 1))
                        actions.append((ActionType.RELEASE, 'e'))
        
        return actions, True