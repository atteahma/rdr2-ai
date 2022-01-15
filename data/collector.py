import os

import numpy as np
import pandas as pd
import cv2

from rdr2_ai.module import Module

class FishData(Module):

    def __init__(self, labels: list[str]):
        self.writeDir = os.path.join('./data/fishing')
        if not os.path.exists(self.writeDir):
            os.makedirs(self.writeDir)

        # pick up where we left off
        currFiles = os.listdir(self.writeDir)
        isRelevant = lambda f: f.endswith('.csv') and f.startswith('run_')
        relFiles = filter(isRelevant, currFiles)
        getNumeric = lambda s: int(''.join([c for c in s if c.isnumeric()]))
        currIds = map(getNumeric, relFiles)
        lastId = max(currIds, default=0)
        self.currRunId = lastId + 1

        self.labels = labels
        self.createNewRunDict()

        self.print(f'starting with index {self.currRunId}')
        
    def log(self, label, data):
        if label not in self.runData:
            self.print(f'label {label} not found.')
            return
        
        runList = self.runData[label]
        runList.append(data)
    
    def write(self):
        self.print('writing to log file.')

        isValid = self.validateRuns()
        if not isValid:
            return
        
        self.writeImages()
        self.writeData()

        self.createNewRunDict()
        self.currRunId += 1
    
    def createNewRunDict(self):
        self.runData = {label: [] for label in self.labels}

    def validateRuns(self):
        runLens = {label: len(self.runData[label]) for label in self.labels}
        if len(set(runLens.values())) != 1:
            self.print(f'invalid run lengths {runLens}.')
            return False
        if not all(runLens.values()):
            # we have an empty pt
            self.print('no data to log.')
            return False
        return True

    def writeImages(self):
        imLabels = self.getImageLabels()

        for label in imLabels:
            imDir = os.path.join(self.writeDir, f'run_{self.currRunId}_{label}')
            os.mkdir(imDir)
            ims = self.runData[label]
            numberWidth = len(str(len(ims)))
            for i, im in enumerate(ims):
                imPath = os.path.join(imDir, str(i).zfill(numberWidth) + '.tiff') # for windows sorting
                cv2.imwrite(imPath, im)
            self.print(f'wrote {len(ims)} images with label {label}.')
    
    def getImageLabels(self):
        imLabels = []
        for label, data in self.runData.items():
            if data and type(data[0]) is np.ndarray:
                imLabels.append(label)
        return imLabels
    
    def writeData(self):
        runDataPath = os.path.join(self.writeDir, f'run_{self.currRunId}.csv')
        relevantRunData = {label: self.runData[label] for label in self.getDataLabels()}
        if len(relevantRunData) > 0:
            df = pd.DataFrame.from_dict(relevantRunData)
            df.to_csv(runDataPath, index=False)
            self.print(f'wrote {np.prod(df.shape)} data points.')
        
    def getDataLabels(self):
        return list(set(self.labels) - set(self.getImageLabels()))

    def cleanup(self):
        pass
