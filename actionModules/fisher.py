from enum import Enum
from time import time
from random import random

import cv2
import numpy as np
from scipy.signal import convolve2d
import matplotlib.pyplot as plt

from rdr2_ai.configWindow.configWindow import ConfigWindow
from rdr2_ai.configWindow.configWindowTemplate import ConfigWindowTemplate,ContentType
from rdr2_ai.controls.actionHandler import ActionType
from rdr2_ai.module import Module
from rdr2_ai.utils.utils import allAnyCloseEnough, closeEnough
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
    .addContentBox('numFishCaught', ContentType.Text, (1200, 1200), (30,100))


class FisherState(Enum):
    PRE      = 'PRE'
    GRIPPED  = 'GRIPPED'
    SWINGING = 'SWINGING'
    CASTOUT  = 'CASTOUT'
    REELIN   = 'REELIN'
    FISHNIB  = 'FISHNIB'
    FISHGOT  = 'FISHGOT'
    CUT      = 'CUT'

class Fisher(Module):

    SKIP = 2

    def __init__(self, configWindow: ConfigWindow = None):
        self.configWindow = configWindow
        self.optionsGetter = OptionsGetter(configWindow=configWindow, showInConfigWindow=True)
        self.pauseMenu = PauseMenu()

        self.swingBackDuration = 2

        self.swingBackStartTime = -1
        self.state = FisherState.PRE
        self.currSpeed = 5

        self.splashMean = None
        self.lastYankTime = -1

        self.calmPxMax = np.array([-1 for _ in range(20)], dtype=np.float32)

        self.calmState = False
        self.calmScores = np.array([-1 for _ in range(20)],dtype=np.float32)
        self.convMax = -1

        self.numFishCaught = 0
        self.pctFishKeep = 1.0

        self.startTime = None

        # disgusting
        KH = 10 / Fisher.SKIP
        KW = 15 / Fisher.SKIP
        filtr_o_h = np.linspace(0,1,int(KH))
        filtr_o_w = np.linspace(0,1,int(KW))
        filtr_h = np.append(np.append(filtr_o_h,[1]),np.flip(filtr_o_h))
        filtr_w = np.append(np.append(filtr_o_w,[1]),np.flip(filtr_o_w))
        filtr = np.add.outer(filtr_h,filtr_w) / 2

        self.splashConvFilter = filtr ** 3

    def getActions(self, frame):

        if self.startTime is None:
            self.startTime = time()

        actions, success = [], False

        # if game is paused, instantly exit
        isPaused = self.pauseMenu.gameIsPaused(frame)
        if isPaused:
            cv2.imwrite('./temp_issue.jpg', frame)
            self.print('game is paused.')
            return [(ActionType.DONE, '')]

        # get options
        options = self.optionsGetter.getOptions(frame)

        if len(options) == 0:

            if self.state == FisherState.FISHGOT:
                # line got cut
                self.state = FisherState.CUT
                actions,success = [(ActionType.RELEASE,'MOUSE_RIGHT')],True

            elif self.state == FisherState.REELIN:
                # did not get a fish last swing, mouse right still held, reset
                self.state = FisherState.GRIPPED
                success = True

            elif self.state == FisherState.GRIPPED:
                # have not swung back yet
                self.swingBackStartTime = time()
                self.state = FisherState.SWINGING
                self.currSpeed = 5
                actions,success = [(ActionType.HOLD,'MOUSE_LEFT')],True

            elif self.state == FisherState.SWINGING:
                success = True
                if (time() - self.swingBackStartTime) > self.swingBackDuration:
                    # done swinging back
                    self.swingBackStartTime = -1
                    self.state = FisherState.CASTOUT
                    actions,success = [(ActionType.RELEASE,'MOUSE_LEFT')],True
            elif self.state == FisherState.PRE:
                success = True
            elif self.state == FisherState.CUT:
                success = True

        elif len(options) == 1:
            option = options[0]

            if closeEnough(option,'bait'):
                # not begun fishing yet
                if self.state not in (FisherState.CUT,FisherState.PRE,FisherState.GRIPPED):
                    self.print(f'invalid state change {self.state} -> {FisherState.GRIPPED}')
                
                self.state = FisherState.GRIPPED
                actions,success = [(ActionType.PAUSE, 0.5),
                                   (ActionType.HOLD,'MOUSE_RIGHT')],True
        
        elif len(options) == 2:

            if closeEnough(options[0],'bait'): # a bit hacky
                # option to use previous lure, do it
                actions,success = [(ActionType.TAP,'e')],True

            elif allAnyCloseEnough(options,['grip reel','reset cast']):
                # we mistakenly let go of right mouse at some point, this should never happen
                self.state = FisherState.REELIN
                self.currSpeed = 5
                actions,success = [(ActionType.RELEASE,'MOUSE_RIGHT'),(ActionType.HOLD,'MOUSE_RIGHT')],True
            
            elif allAnyCloseEnough(options,['reel in','reset cast']) or allAnyCloseEnough(options,['reel lure','reset cast']):
                # reeling in phase, no fish
                if self.state not in (FisherState.CASTOUT,FisherState.REELIN,FisherState.FISHNIB,FisherState.FISHGOT):
                    self.print(f'invalid state change {self.state} -> {FisherState.REELIN}')
                
                actions,success = [(ActionType.HOLD,'SPACEBAR')],True

                success = True
                self.state = FisherState.REELIN
            
            elif allAnyCloseEnough(options,['keep','throw back']):
                # we caught a fish and it's in our hands
                if self.state not in (FisherState.PRE,FisherState.FISHGOT):
                    self.print(f'invalid state change {self.state} -> {FisherState.PRE}')
                
                self.state = FisherState.PRE
                
                self.numFishCaught += 1

                keepFish = True
                if random() > self.pctFishKeep:
                    keepFish = False
                    self.print('throwing away fish for honor')
                else:
                    self.print('keeping fish for money')

                keepThrowChr = 'e' if keepFish else 'f'
                actions,success = [
                    (ActionType.RELEASE, 'SPACEBAR'),
                    (ActionType.RELEASE, 'MOUSE_RIGHT'),
                    (ActionType.TAP, keepThrowChr)
                ],True # e to keep, f to throw back

        elif len(options) == 3:
            if allAnyCloseEnough(options,['reel lure','reset cast','hook fish']) or allAnyCloseEnough(options,['reel in','reset cast','hook fish']):
                # fish just bit
                if self.state not in (FisherState.REELIN,FisherState.FISHNIB):
                    self.print(f'invalid state change {self.state} -> {FisherState.FISHNIB}')
                
                self.state = FisherState.FISHNIB
                self.currSpeed = 5
                actions,success = [
                    (ActionType.RELEASE,'SPACEBAR'),
                    (ActionType.TAP,'MOUSE_LEFT'),
                    (ActionType.PAUSE, 1),
                ],True

            elif allAnyCloseEnough(options,['reel in','cut line','control']):
                # fish is caught on
                if self.state not in (FisherState.FISHNIB,FisherState.FISHGOT):
                    self.print(f'invalid state change {self.state} -> {FisherState.FISHGOT}')

                self.state = FisherState.FISHGOT
                actions,success = [],True

        if not success:
            self.print(f'could not understand options [len(options)={len(options)}]')
        else:
            strategyActions = self.getFishReelInStrategyActions(frame)
            actions += strategyActions

        self.print(f'state = {self.state}')

        fishperminute = round(self.numFishCaught * 60 / (time() - self.startTime),2)
        if self.configWindow:
            self.configWindow.drawToTemplate('fishperminute',str(fishperminute))
            self.configWindow.drawToTemplate('numFishCaught', str(self.numFishCaught))
        else:
            self.print(f'fish/min = {fishperminute}')
            self.print(f'fish caught = {self.numFishCaught}')

        return actions
    
    def getFishReelInStrategyActions(self, frame):
        
        actions = []

        if self.state == FisherState.REELIN:
            if self.currSpeed > 0:
                actions += [(ActionType.TAP,'f')]
                self.currSpeed -= 1
            
            self.fishIsCalm(frame,nofish=True)
        
        elif self.state == FisherState.FISHGOT:
            if self.fishIsCalm(frame):
                actions += [(ActionType.HOLD,'SPACEBAR')]
 
                if self.currSpeed < 10:
                    actions += [(ActionType.TAP,'r')]
                    self.currSpeed += 1
                
                if (self.lastYankTime == -1) or ((time() - self.lastYankTime) > 5):
                    actions += [(ActionType.TAP, 'MOUSE_LEFT')]
                    self.lastYankTime = time()
                
                if self.configWindow:
                    self.configWindow.drawToTemplate('isCalm', 'CALM')
                else:
                    self.print('fish is CALM')

            else:
                # fish is freaking out, stop reeling and move the mouse around
                actions += [(ActionType.RELEASE,'SPACEBAR')]
                controlDir = 1 if (random() < 0.5) else -1
                actions += [(ActionType.MOVE, (-1 * controlDir * 800,0,0.25)),
                            (ActionType.MOVE, (     controlDir * 800,0,0.25))]
                self.currSpeed = 5

                if self.configWindow:
                    self.configWindow.drawToTemplate('isCalm', ('NOT CALM', (0,0,255)))
                else:
                    self.print('fish is NOT CALM')

        return actions

    def fishIsCalm(self, im, nofish=False):

        score = self.getFishCalmScore(im)

        self.calmScores = np.roll(self.calmScores, 1)
        self.calmScores[0] = score

        if nofish:
            return None
        
        # lol cancel them... but for python readability and future expandability i will keep it as is
        calmScoreSm2 = np.mean((self.calmScores[1:],self.calmScores[:-1]), axis=0)
        calmScoreDiff = calmScoreSm2[1:] - calmScoreSm2[:-1]

        if calmScoreDiff[0] * calmScoreDiff[1] < 0:
            # we are at a critical point
            if self.calmScores[0] < self.calmScores[1]:
                # we are at a calm point
                self.calmState = True
            else:
                self.calmState = False

        if self.configWindow:
            fig = plt.figure()
            plt.plot(self.calmScores)
            plt.plot(calmScoreSm2)
            self.configWindow.drawToTemplate('fishCalmScorePlot', fig)
        

        return self.calmState

        # if nofish:
        #     # update calmScores
        #     self.calmScores = np.roll(self.calmScores,1)
        #     self.calmScores[0] = score

        #     return None

        # # calculate middle distribution of calm scores
        # validCalmScores = self.calmScores[self.calmScores != -1]
        # if validCalmScores.size < 10:
        #     # hack so that the first throw isn't volatile
        #     self.print('CALM (hack)')
        #     return True
        
        # calmScoreThresh = np.max(validCalmScores)

        # # update prevScores
        # self.prevScores = np.roll(self.prevScores,1)
        # self.prevScores[0] = score
        
        # # apply threshold
        # isNotCalm = score > calmScoreThresh
        
        # # make plot
        # fig = plt.figure()
        # plt.plot(self.prevScores)
        # plt.hlines(calmScoreThresh,0,3,colors='red')
        # self.configWindow.drawToTemplate('fishCalmScorePlot',fig)

        # if isNotCalm: # effectively when num > 1 due to current time window length
        #     self.print('NOT CALM')
        #     return False

        # self.print('CALM')
        # return True


    def getFishCalmScore(self, im):

        im = im[::Fisher.SKIP,::Fisher.SKIP]

        gray_im = cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)

        if np.amax(gray_im) > 2:
            gray_im = gray_im.astype(np.float32) / 255

        if self.state is FisherState.FISHGOT:
            # the camera moves when you get a fish
            L = 0.46
            R = 0.46
            T = 0.50
            B = 0.38
        else:
            L = 0.54
            R = 0.38
            T = 0.54
            B = 0.34

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
            self.splashMean = splash_im.mean()
        norm_im = np.clip(splash_im - self.splashMean, 0, 1)
        windowLen = 25
        self.splashMean = (1/windowLen) * splash_im.mean() + (1 - 1/windowLen) * self.splashMean

        # # normalize and cut low values
        # norm_im = (splash_im - splash_im.mean()) / splash_im.std()
        # norm_max = norm_im.max()
        # norm_min = norm_im.min()
        # sf = max(abs(norm_max),abs(norm_min))
        # norm_im = np.clip(norm_im / sf,0,1)
        
        # convolve to find splotch of white (splash in water)
        conv_im = convolve2d(norm_im,self.splashConvFilter,mode='valid')
        
        if self.configWindow:
            self.calmPxMax = np.roll(self.calmPxMax, 1)
            self.calmPxMax[0] = np.max(conv_im)
            self.configWindow.drawToTemplate('splashImThresh',conv_im / max(self.calmPxMax))

        score = np.sum(conv_im ** 2) ** 0.5 / np.product(conv_im.shape)

        return score
        