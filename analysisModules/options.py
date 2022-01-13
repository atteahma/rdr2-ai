from os.path import join

import cv2
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
# import pytesseract
# from pytesseract import Output
from PIL import Image
from tesserocr import PyTessBaseAPI, PSM
from spellchecker.spellchecker import SpellChecker

from rdr2_ai import config
from rdr2_ai.configWindow.configWindow import ConfigWindow
from rdr2_ai.module import Module
from rdr2_ai.utils.utils import applyBBox, dilate, segmentImage

matplotlib.use('TkAgg')

class OptionsGetter(Module):

    CRAFTING = 0b01
    COOKING = 0b10

    RES_SKIP = 1

    def __init__(self, configWindow: ConfigWindow, showInConfigWindow: bool = False, timeSkip: int = 1):
        self.optionsOffsetBR = config.optionsOffsetBR
        self.craftingScoreThreshold = config.craftingScoreThreshold
        self.textColorTolerance = config.textColorTolerance
        self.OCRScaleFactor = config.OCRScaleFactor
        self.minOptionTextGap = config.minOptionTextGap
        self.textPadding = config.textPadding
        self.OCRConfig = config.OCRConfig
        self.minOCRConfidence = config.minOCRConfidence
        self.minHorLineHeight = config.minHorLineHeight
        self.horLineCoverageThresh = config.horLineCoverageThresh
        self.spellcheckDistance = config.spellcheckDistance
        
        self.timeSkip = timeSkip
        self.currOptions = None
        self.frameIndex = 0

        self.winSize = None
        self.optionsBB = None

        self.configWindow = configWindow
        self.showInConfigWindow = showInConfigWindow

        self.spellcheck = SpellChecker(distance=self.spellcheckDistance)

        self.tesseractAPI = PyTessBaseAPI(path=join("C:\\Project\\tessdata\\"),
                                          psm=PSM.SINGLE_LINE)
    
    def cleanup(self):
        self.tesseractAPI.End()

    def updateBoundingBoxes(self, frame):
        self.winSize = (frame.shape[1], frame.shape[0])
        self.optionsBB = ( self.winSize[0] - self.optionsOffsetBR[0],
                           self.winSize[1] - self.optionsOffsetBR[1],
                           self.winSize[0],
                           self.winSize[1] )


    def getOptions(self, frame):
        if self.frameIndex % self.timeSkip == 0:
            self.currOptions = self.getOptionsFromFrame(frame)
        self.frameIndex += 1

        self.print(f'detected options {self.currOptions}')

        return self.currOptions

    """
    def getCraftingInfo(self,frame):

        craftingFrame = applyBBox(frame,self.craftingBB)

        matchScores = cv2.matchTemplate(craftingFrame,self.craftingTemplate,cv2.TM_SQDIFF_NORMED)
        minScore, _, minLoc, _ = cv2.minMaxLoc(matchScores, None)

        isCrafting = minScore < self.craftingScoreThreshold
        craftingChoices = []

        if isCrafting:
            itemsLeftBB = (
                minLoc[0],
                1200,
                minLoc[0] + self.craftingTemplate.shape[1],
                1400,
            )
            itemsLeftFrame = applyBBox(craftingFrame,itemsLeftBB)
            maxRedVal = np.max(itemsLeftFrame[:,:,2])

            # there is red text that indicates there are no items left
            # white text if there are items left
            itemsLeft = maxRedVal > 200

            if itemsLeft:
                itemsBB = (
                    minLoc[0],
                    320,
                    minLoc[0] + self.craftingTemplate.shape[1],
                    900,
                )

                itemsFrame = applyBBox(craftingFrame,itemsBB)

                # four items stacked vertically, some are greyed out (unavailable)
                itemFrames = np.split(itemsFrame,4,axis=0)
                itemFramesCropped = list(map(
                    lambda itemFrame: cropCenter(itemFrame,scale=0.7),
                    itemFrames,
                ))
                craftingChoices = np.array(list(map(
                    lambda itemFrame: np.max(itemFrame),
                    itemFramesCropped,
                ))) > 200
        
        return isCrafting,craftingChoices
        """

    def getOptionsFromFrame(self, frame):
        
        if self.optionsBB is None or self.winSize is None:
            self.updateBoundingBoxes(frame)

        # crop to only options area
        optionsFrame = applyBBox(frame,self.optionsBB)
        if self.showInConfigWindow and self.configWindow:
            self.configWindow.addDrawEvent('optionsFrameRaw', optionsFrame)

        # clean options frame for ocr
        optionsFramePreProc = self.preprocessOptionsFrame(optionsFrame)
        if self.showInConfigWindow and self.configWindow:
            self.configWindow.addDrawEvent('optionsFrameClean', optionsFramePreProc)

        # detect if there is a horizontal line. if there exists one, text below
        # it is simply the name of the item that you are crafting/cooking
        horLineExists = self.horizontalLinePresent(optionsFramePreProc)

        # segment image into each seperate option
        optionFramesList = self.segmentOptionsFrame(optionsFramePreProc)

        if len(optionFramesList) > 0 and horLineExists:
            optionFramesList = optionFramesList[:-1]

        # do ocr on each option frame
        optionWords = self.wordsFromFrames(optionFramesList)

        return optionWords
    
    def preprocessOptionsFrame(self, optionsFrame):

        # binarize image and cvt to grayscale
        optionsFrameMaskInv = np.all(optionsFrame < (255-self.textColorTolerance),axis=2)
        optionsFrameBin = np.zeros(optionsFrame.shape[:2],dtype=np.uint8)
        optionsFrameBin[~optionsFrameMaskInv] = 255

        # crop as tight as possible and scale up for OCR
        textPad = int(self.textPadding)
        x,y,w,h = cv2.boundingRect(optionsFrameBin)
        x1 = max(0,x-textPad)
        y1 = max(0,y-textPad)
        x2 = min(optionsFrameBin.shape[1],x+w+textPad)
        y2 = min(optionsFrameBin.shape[0],y+h+textPad)

        optionsFrameCropped = optionsFrameBin[y1:y2,x1:x2]
        optionsFrameScaled = cv2.resize(
            optionsFrameCropped,
            (0,0),
            fx=self.OCRScaleFactor,
            fy=self.OCRScaleFactor,
            interpolation=cv2.INTER_CUBIC,
        )

        # fill in holes
        optionsFrameDilated = dilate(optionsFrameScaled)

        return optionsFrameDilated

    def horizontalLinePresent(self, optionsFrame):
        minLineHeight = int(self.minHorLineHeight * self.OCRScaleFactor / 3)
        minTextGap = int(self.minOptionTextGap * self.OCRScaleFactor / 3)

        optionFramesList = segmentImage(
            optionsFrame,
            minGap=minLineHeight,
            pad=0,
            bgColor=0,
            axis=0
        )

        for frame in optionFramesList:

            if (frame.shape[0] < minTextGap) and (np.mean(frame) > self.horLineCoverageThresh):
                # found a line
                return True
        
        return False

    def segmentOptionsFrame(self, optionsFrame):
        minGap = int(self.minOptionTextGap * self.OCRScaleFactor / 3)
        textPad = int(self.textPadding * self.OCRScaleFactor / 3)
        
        optionFramesList = segmentImage(
            optionsFrame,
            minGap=minGap,
            pad=textPad,
            bgColor=0,
            axis=0
        )

        return optionFramesList
    
    def wordsFromFrames(self, optionFramesList):
        optionWords = []
        for optionFrame in optionFramesList:
            optionFrame = optionFrame[::OptionsGetter.RES_SKIP , ::OptionsGetter.RES_SKIP]
            
            #newOptionsWords = self.getWords_PyTesseract(optionFrame)
            newOptionsWords = self.getWords_TesserOCR(optionFrame)
            optionWords.extend(newOptionsWords)
        
        optionWordsClean = []
        if len(optionWords) > 0:
            optionWordsClean = list(map(self.cleanOCROutput,optionWords))

        optionWordsClean = list(filter(len,optionWordsClean))

        return optionWordsClean
    
    def getWords_TesserOCR(self, optionFrame):
        pilOptionFrame = Image.fromarray(optionFrame ^ 255)
        self.tesseractAPI.SetImage(pilOptionFrame)
        text = self.tesseractAPI.GetUTF8Text()
        return [text]

    # def getWords_PyTesseract(self, optionFrame):
    #     ocrData = pytesseract.image_to_data(
    #         optionFrame ^ 255, # switch black and white
    #         config=self.OCRConfig,
    #         output_type=Output.DICT
    #     )

    #     # filter out by minimum confidence set in config
    #     goodWords = []
    #     for word,conf in zip(ocrData['text'],ocrData['conf']):
    #         if float(conf) > self.minOCRConfidence:
    #             goodWords.append(word)

    #     optionWords = []
    #     if len(goodWords) > 0:
    #         optionWords.append(' '.join(goodWords).lower())
        
    #     return optionWords

    def cleanOCROutput(self, s):
        
        #print(f'unclean: {s}')

        s = ''.join([c for c in s if (c.isalpha() or (c == ' '))])
        s = s.lower()
        s = s.strip(' ')

        # spell check and remove single letter words
        words = s.split(' ')
        goodWords = []
        for i,w in enumerate(words):
            if len(w) == 1:
                continue

            # if w not in self.spellcheck:
            #     w = self.spellcheck.correction(w)
            
            goodWords.append(w)
            
        s = ' '.join(goodWords)

        s = s.lower()
        s = s.strip(' ')

        #print(f'clean: {s}')

        return s
