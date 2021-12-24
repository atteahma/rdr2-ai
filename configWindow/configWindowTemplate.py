from dataclasses import dataclass
from enum import Enum

from rdr2_ai.module import Module

class ContentType(Enum):
    Image = 1
    Text = 2
    Plot = 3

@dataclass
class ContentBoxInfo:
    name: str
    contentType: ContentType
    location: tuple[int,int]
    size: tuple[int,int]

@dataclass
class StaticText:
    text: str
    location: tuple[int,int]
    size: tuple[int,int]

class ConfigWindowTemplate(Module):

    def __init__(self):
        self.contentBoxes = {}
        self.staticTexts = []
        self.size = None
        self.bgColor = (0,0,0)

    # BUILD METHODS

    def addContentBox(self, name, contentType, location, size):
        if name in self.contentBoxes:
            self.print('name already exists in template')
            return self
        
        self.contentBoxes[name] = ContentBoxInfo(name,contentType,location,size)
        return self

    def addStaticText(self, text, location, size):
        staticTextObj = StaticText(text,location,size)
        self.staticTexts.append(staticTextObj)
        return self

    def setSize(self, height, width):
        self.size = (height, width)
        return self

    def setBGColor(self, color):
        self.bgColor = color
        return self


    # RUNTIME METHODS

    def getContentBox(self, name):
        if name not in self.contentBoxes:
            return None
        
        return self.contentBoxes[name]
    
    def getStaticTexts(self):
        return self.staticTexts
    