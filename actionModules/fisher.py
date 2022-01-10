from dataclasses import dataclass
from enum import Enum, IntEnum, auto
from time import time, time_ns
from random import random

import cv2
import numpy as np
from scipy.signal import convolve2d
import matplotlib.pyplot as plt
from pprint import PrettyPrinter

from rdr2_ai.configWindow.configWindow import ConfigWindow
from rdr2_ai.configWindow.configWindowTemplate import ConfigWindowTemplate,ContentType
from rdr2_ai.controls.actionHandler import ActionType
from rdr2_ai.module import Module
from rdr2_ai.utils.state import StateMachine
from rdr2_ai.utils.utils import allAnyCloseEnough, anyCloseEnough, closeEnough
from rdr2_ai.analysisModules.options import OptionsGetter
from rdr2_ai.analysisModules.pause import PauseMenu


fisherConfigWindowTemplate = ConfigWindowTemplate()
fisherConfigWindowTemplate \
    .setSize(height=1250, width=2200) \
    .addStaticText('Splash (raw)', (10,100), (40,400)) \
    .addContentBox('splashImRaw', ContentType.Image, (60,100), (300,600)) \
    .addStaticText('Splash (MA + globconv + MMAX)', (400+10,100), (40,600)) \
    .addContentBox('splashImThresh', ContentType.Image, (400+60,100), (300,600)) \
    .addStaticText('Calm Score Diff Interpolation', (800+10,100), (40,600)) \
    .addContentBox('fishCalmScorePlot', ContentType.Plot, (800+60,100), (300,600)) \
    .addStaticText('Splash Bounding Box', (10,1500-200), (40,400)) \
    .addContentBox('splashBoundingBox', ContentType.Image, (60,800+100), (600,1200)) \
    .addStaticText('Raw Options Frame', (700,800+100),(40,400)) \
    .addContentBox('optionsFrameRaw', ContentType.Image, (700+60,800+100), (400,400)) \
    .addStaticText('Cleaned Options Frame', (700,800+600+100), (40,400)) \
    .addContentBox('optionsFrameClean', ContentType.Image, (700+60,800+600+100), (400,400)) \
    .addContentBox('isCalm', ContentType.Text, (1200, 100), (30, 200)) \
    .addStaticText('Frames/s:', (1200,400), (30,100)) \
    .addContentBox('fps', ContentType.Text, (1200,500), (30,100)) \
    .addStaticText('Fish/min:', (1200,700), (30,100)) \
    .addContentBox('fishperminute', ContentType.Text, (1200,800), (30,100)) \
    .addStaticText('Fish Caught:', (1200, 1000), (30,200)) \
    .addContentBox('numFishCaught', ContentType.Text, (1200, 1200), (30,100)) \
    .addContentBox('state', ContentType.Text, (1200,1400), (30,300)) \
    .addStaticText('Invalid State Queries:', (1200,1800), (30,200)) \
    .addContentBox('numInvalidQueries', ContentType.Text, (1200, 2000), (30,100))


class FisherState(IntEnum):
    PRE          = auto()
    GRIPPED      = auto()
    SWING_BACK   = auto()
    CAST_OUT     = auto()
    REEL_IN      = auto()
    HOOK_ATTEMPT = auto()
    FISH_HOOKED  = auto()
    DONE_REELING = auto()
    FISH_IN_HAND = auto()

class FisherStateMachine(StateMachine):

    def __init__(self, swingDuration: float = 2,
                       defaultReelSpeed: int = 10,
                       maxReelSpeed: int = 20,
                       pctKeepFish: float = 0.9):
        super().__init__()

        self.actionStateFunctions[FisherState.PRE         ] = self.pre
        self.actionStateFunctions[FisherState.GRIPPED     ] = self.gripped
        self.actionStateFunctions[FisherState.SWING_BACK  ] = self.swingBack
        self.actionStateFunctions[FisherState.CAST_OUT    ] = self.castOut
        self.actionStateFunctions[FisherState.REEL_IN     ] = self.reelIn
        self.actionStateFunctions[FisherState.HOOK_ATTEMPT] = self.hookAttempt
        self.actionStateFunctions[FisherState.FISH_HOOKED ] = self.fishHooked
        self.actionStateFunctions[FisherState.DONE_REELING] = self.doneReeling
        self.actionStateFunctions[FisherState.FISH_IN_HAND] = self.fishInHand

        self.setState(FisherState.PRE)

        # pre
        self.preStartTime = -1
        self.preTimeout = 8

        # swing back
        self.swingDuration = swingDuration
        self.swingStartTime = -1

        # reel in, hook attempt, fish hooked
        self.reelSpeed = defaultReelSpeed
        self.defaultReelSpeed = defaultReelSpeed
        self.maxReelSpeed = maxReelSpeed
        self.hookAttemptStartTime = -1
        self.hookAttemptTimeout = 2.5

        # fish in hand
        self.pctKeepFish = pctKeepFish
        self.numFishCaught = 0
        self.xComp = 1000

    def pre(self, options):
        # this assumes that you have already manually
        # equipped a bait/lure (for now, bait selection ai tbd)

        if self.preStartTime == -1:
            self.preStartTime = time()

        if len(options) == 0:
            # full reset after timeout
            if (time() - self.preStartTime) > self.preTimeout:
                return [(ActionType.RELEASE, 'ALL')], FisherState.PRE
            else:
                return [], FisherState.PRE
        
        if len(options) == 1 and closeEnough('bait', options[0]):
            # not begun fishing yet, but is ready to
            return [(ActionType.HOLD, 'MOUSE_RIGHT')], FisherState.GRIPPED

        if len(options) == 2 and anyCloseEnough('bait', options):
            # equip previous bait/lure
            return [(ActionType.TAP, 'e'), (ActionType.PAUSE, 0.5), (ActionType.MOVE, (600, 0, 1))], FisherState.PRE

        if anyCloseEnough('grip reel', options):
            # we are not gripping  the reel
            return [(ActionType.HOLD, 'MOUSE_RIGHT')], FisherState.GRIPPED
        
    def gripped(self, options):
        if len(options) == 0:
            # start swing back
            return [(ActionType.HOLD, 'MOUSE_LEFT')], FisherState.SWING_BACK
        elif anyCloseEnough('bait', options):
            # we did not grip the rod
            return [(ActionType.RELEASE, 'MOUSE_RIGHT')], FisherState.PRE
    
    def swingBack(self, options):
        if self.swingStartTime == -1:
            self.swingStartTime = time()
        
        if (time() - self.swingStartTime) < self.swingDuration:
            # still swinging
            return [], FisherState.SWING_BACK
        else:
            # done swinging
            return [(ActionType.RELEASE, 'MOUSE_LEFT')], FisherState.CAST_OUT
    
    def castOut(self, options):
        if len(options) == 0:
            # bait/lure has not hit the water yet
            return [], FisherState.CAST_OUT
        
        if len(options) == 2 and allAnyCloseEnough(options, ('reel in','reel lure','reset cast')):
            # bait/lure hit the water
            return [(ActionType.HOLD, 'SPACEBAR')], FisherState.REEL_IN
    
    def reelIn(self, options):

        if ((len(options) > 1 and anyCloseEnough('control', options)) or
            (len(options) == 3 and allAnyCloseEnough(options, ('reel in','reel lure','reset cast', 'hook fish')))):
            # we should not be reeling in, we have a fish hooked or fish just bit
            self.reelSpeed = self.defaultReelSpeed
            return [(ActionType.TAP, 'MOUSE_LEFT'), (ActionType.RELEASE, 'SPACEBAR')], FisherState.HOOK_ATTEMPT
        
        if len(options) == 2 and allAnyCloseEnough(options, ('reel in','reel lure','reset cast')):
            # still reeling in, go as slow as possible
            if self.reelSpeed > 0:
                decreaseAmount = min(2, self.reelSpeed)
                self.reelSpeed -= decreaseAmount
                actions = [(ActionType.TAP, 'f')]*decreaseAmount
            else:
                actions = []

            return actions, FisherState.REEL_IN

        if ((len(options) == 0) or
            (len(options) == 1 and closeEnough(options[0], 'bait')) or
            (len(options) == 2 and anyCloseEnough('bait', options))):
            # fully reeled in and didn't get a fish
            return [(ActionType.RELEASE, 'ALL')], FisherState.DONE_REELING
    
    def hookAttempt(self, options):
        
        self.hookAttemptStartTime = time()

        if len(options) == 3 and allAnyCloseEnough(options, ('reel in','reel lure','reset cast','hook fish')):
            # attempt to hook fish failed, but fish is still nibbling
            return [(ActionType.TAP, 'MOUSE_LEFT')], FisherState.HOOK_ATTEMPT
        
        if len(options) >= 2 and allAnyCloseEnough(options, ('reel in','reel lure','cut line','reset cast')):
            # attempt to hook fish failed, lost fish, but line is not cut
            self.reelSpeed = self.defaultReelSpeed
            return [(ActionType.HOLD, 'SPACEBAR')], FisherState.REEL_IN
        
        if len(options) == 3 and allAnyCloseEnough(options, ('reel in', 'cut line', 'control')):
            # attempt to hook was successful, start off with no reeling
            return [], FisherState.FISH_HOOKED
    
    def fishHooked(self, options):
        if len(options) == 3 and allAnyCloseEnough(options, ('reel in','cut line','control')):
            # reeling in fish
            return [], FisherState.FISH_HOOKED
        
        if len(options) == 2 and anyCloseEnough('reset cast', options):
            # lost fish, but line is not cut
            self.reelSpeed = self.defaultReelSpeed
            return [(ActionType.HOLD, 'SPACEBAR')], FisherState.REEL_IN
        
        if ((len(options) == 0 and time() - self.hookAttemptStartTime > self.hookAttemptTimeout) or
            (len(options) == 1 and closeEnough(options[0], 'bait')) or # fish was lost
            (len(options) == 2 and anyCloseEnough('bait', options)) or # fish was lost
            (len(options) == 2 and allAnyCloseEnough(options, ('keep','throw back'))) or
            (len(options) == 1 and allAnyCloseEnough(options, ('keep','throw back')))): # fish was caught
            # fully reeled in
            return [(ActionType.RELEASE, 'ALL')], FisherState.DONE_REELING
        
    def doneReeling(self, options):
        self.reelSpeed = self.defaultReelSpeed
        self.preStartTime = -1
        self.swingStartTime = -1

        if len(options) == 0:
            # auto-reeling in, wait it out
            return [], FisherState.DONE_REELING
        
        if ((len(options) == 1 and closeEnough(options[0], 'bait')) or
            (len(options) == 2 and anyCloseEnough('bait', options))):
            # didn't catch a fish
            return [], FisherState.PRE
        
        if len(options) == 2 and allAnyCloseEnough(options, ('keep','throw back')):
            return [], FisherState.FISH_IN_HAND
        
    def fishInHand(self, options):
        self.numFishCaught += 1
        decisionKey='e'
        
        if random() > self.pctKeepFish:
            # throw back
            decisionKey = 'f'
        
        a = [(ActionType.TAP, decisionKey),(ActionType.PAUSE,2),(ActionType.MOVE, (self.xComp, 0, 1))]

        if len(options) == 1:
            a = [(ActionType.TAP, 'e'), (ActionType.TAP, 'f'),(ActionType.PAUSE,2),(ActionType.MOVE, (self.xComp, 0, 1))]
        
        return a, FisherState.PRE

class Fisher(Module):

    SKIP = 2

    def __init__(self, configWindow: ConfigWindow = None):
        self.configWindow = configWindow
        self.optionsGetter = OptionsGetter(configWindow=configWindow, showInConfigWindow=True)
        self.stateMachine = FisherStateMachine(pctKeepFish=1.0)

        self.startTime = time()

        self.mouseControlAmount = 600
        self.lastYankTime = -1
        self.yankPeriod = 5

        self.bufferLength = 15
        self.calmPxMax = np.array([-1 for _ in range(self.bufferLength)], dtype=np.float32)
        self.calmState = False
        self.calmScores = np.array([-1 for _ in range(self.bufferLength)], dtype=np.float32)
        self.splashMean = None

        # disgusting
        KH = 10 / Fisher.SKIP
        KW = 15 / Fisher.SKIP
        filtr_o_h = np.linspace(0,1,int(KH))
        filtr_o_w = np.linspace(0,1,int(KW))
        filtr_h = np.append(np.append(filtr_o_h,[1]),np.flip(filtr_o_h))
        filtr_w = np.append(np.append(filtr_o_w,[1]),np.flip(filtr_o_w))
        filtr = np.add.outer(filtr_h,filtr_w) / 2
        self.splashConvFilter = filtr ** 3
        
        self.optionsRuntimeHistory = [] # temp

    def cleanup(self):
        PrettyPrinter().pprint(self.stateMachine.invalidQueries)
        
        np.savetxt('optionsRuntimeHistory.csv',
                   self.optionsRuntimeHistory,
                   delimiter=', ',
                   fmt='% s')

    def getActions(self, frame):
        
        s = time_ns() # temp

        # use options to get actions
        options = self.optionsGetter.getOptions(frame)

        self.optionsRuntimeHistory.append(time_ns() - s) # temp
        
        # iterate fsm
        actions = self.stateMachine.getActionsAndUpdateState(options)

        # control/optimize the speed of the line while reeling
        if self.stateMachine.state is FisherState.FISH_HOOKED:
            actions += self.getFishReelInStrategyActions(frame)

        self.drawStats()

        return actions
    
    def drawStats(self):
        currState = str(FisherState(self.stateMachine.state))
        numFishCaught = self.stateMachine.numFishCaught
        fishperminute = round(numFishCaught * 60 / (time() - self.startTime), 2)
        numInvalidQueries = len(self.stateMachine.invalidQueries)

        self.print(f'state = {currState}')
        if self.configWindow:
            self.configWindow.drawToTemplate('state', currState)
            self.configWindow.drawToTemplate('fishperminute',str(fishperminute))
            self.configWindow.drawToTemplate('numFishCaught', str(numFishCaught))
            self.configWindow.drawToTemplate('numInvalidQueries', str(numInvalidQueries))
        else:
            self.print(f'fish/min = {fishperminute}')
            self.print(f'fish caught = {numFishCaught}')
            self.print(f'num invalid queries = {numInvalidQueries}')
    
    def getFishReelInStrategyActions(self, frame):
        actions = []
        if self.fishIsCalm(frame):
            actions += [(ActionType.HOLD,'SPACEBAR')]

            if self.stateMachine.reelSpeed < self.stateMachine.maxReelSpeed:
                actions += [(ActionType.TAP,'r')]
                self.stateMachine.reelSpeed += 1
            
            if (self.lastYankTime == -1) or ((time() - self.lastYankTime) > self.yankPeriod):
                actions += [(ActionType.TAP, 'MOUSE_LEFT')]
                self.lastYankTime = time()
            
            if self.configWindow:
                self.configWindow.drawToTemplate('isCalm', 'CALM')
            else:
                self.print('fish is CALM')

        else:
            # fish is freaking out, stop reeling and move the mouse around
            actions += [(ActionType.RELEASE,'SPACEBAR')]
            controlDir = 1 #if (random() < 0.5) else -1
            actions += [(ActionType.MOVE, (-1 * controlDir * self.mouseControlAmount,0,0.25)),
                        (ActionType.MOVE, (     controlDir * self.mouseControlAmount//2,0,0.25))]
            self.currSpeed = 5

            if self.configWindow:
                self.configWindow.drawToTemplate('isCalm', ('NOT CALM', (0,0,255)))
            else:
                self.print('fish is NOT CALM')

        return actions

    def fishIsCalm(self, im):

        score = self.getFishCalmScore(im)

        self.calmScores = np.roll(self.calmScores, 1)
        self.calmScores[0] = score
        
        # lol cancel them... but for python readability and future expandability i will keep it as is
        calmScoreSm2 = np.mean((self.calmScores[1:],self.calmScores[:-1]), axis=0)
        calmScoreDiff = calmScoreSm2[1:] - calmScoreSm2[:-1]

        if calmScoreDiff[0] * calmScoreDiff[1] < 0:
            # we are at a critical point
            if calmScoreSm2[0] < calmScoreSm2[1]:
                # we are at a calm point
                self.calmState = True
            else:
                self.calmState = False

        if self.configWindow:
            self.configWindow.drawToTemplate('fishCalmScorePlot', [self.calmScores, calmScoreSm2])

        return self.calmState

    def getFishCalmScore(self, im):

        im = im[::Fisher.SKIP,::Fisher.SKIP]
        gray_im = cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
        gray_im = gray_im.astype(np.float32) / 255

        L = 0.46
        R = 0.46
        T = 0.50
        B = 0.38

        # no fish bait-water bounding box
        # L = 0.54
        # R = 0.38
        # T = 0.54
        # B = 0.34

        H,W = gray_im.shape
        cT = int(T*H)
        cB = int(B*H)
        cL = int(L*W)
        cR = int(R*W)

        splash_im = gray_im[ cT:-cB , cL:-cR ]
        if self.configWindow:
            self.configWindow.drawToTemplate('splashImRaw',splash_im)
        
            splash_bb_im = im.copy()
            cv2.rectangle(splash_bb_im, (cL,cT), (W-cR,H-cB), (0,0,255), thickness=5)
            self.configWindow.drawToTemplate('splashBoundingBox', splash_bb_im)
            
        if self.splashMean is None:
            # initialize
            self.splashMean = splash_im
        
        norm_im = np.clip(splash_im - self.splashMean, 0, 1)
        self.splashMean = (1/self.bufferLength) * splash_im + (1 - 1/self.bufferLength) * self.splashMean
        
        # convolve to find splotches of white (splash in water)
        conv_im = convolve2d(norm_im,self.splashConvFilter,mode='valid')
        
        if self.configWindow:
            self.calmPxMax = np.roll(self.calmPxMax, 1)
            self.calmPxMax[0] = np.max(conv_im)
            calmNormIm = conv_im / ( 1e-9 + np.max(self.calmPxMax))
            self.configWindow.drawToTemplate('splashImThresh', calmNormIm)

        score = np.sum(conv_im ** 2) ** 0.5 / np.product(conv_im.shape)

        return score
        