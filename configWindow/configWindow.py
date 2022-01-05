import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvas
import cv2

from rdr2_ai.module import Module
from rdr2_ai.configWindow.configWindowTemplate import ContentBoxInfo,ContentType

class ConfigWindow(Module):

    def __init__(self,winName,winLoc,template=None,winSize=None,bgColor=(0,0,0),font=cv2.FONT_HERSHEY_DUPLEX):
        self.winName = winName
        self.winLoc = winLoc
        self.font = font
        self.bgColor = bgColor

        # create window
        cv2.namedWindow(self.winName,
                        cv2.WINDOW_AUTOSIZE    | \
                        cv2.WINDOW_KEEPRATIO   | \
                        cv2.WINDOW_GUI_EXPANDED)
        cv2.moveWindow(self.winName,*self.winLoc)

        if template is not None:
            self.useTemplate(template)

        elif winSize is not None:
            self.winSize = winSize
            canvasShape = (winSize[0],winSize[1],3)
            self.canvas = np.zeros(canvasShape,dtype=np.float32)
            self.flush()

    def useTemplate(self, template):
        self.template = template

        canvasShape = (template.size[0],template.size[1],3)
        self.canvas = np.zeros(canvasShape,dtype=np.float32)

        self.staticTexts = template.getStaticTexts()
        self.bgColor = template.bgColor
        self.flush()
    
    def flush(self):
        self.canvas = self.canvas * 0
        for c in range(3):
            self.canvas[:,:,c] = self.bgColor[2-c] # 2-c because opencv uses BGR
        
        for st in self.staticTexts:
            self.drawText(st.text,st.location,st.size)

    def drawToTemplate(self, name, data):
        if self.template is None:
            self.print('no template used')
            return
        
        cbInfo: ContentBoxInfo = self.template.getContentBox(name)

        if cbInfo.contentType is ContentType.Image:
            self.drawImage(data,cbInfo.location,cbInfo.size)

        elif cbInfo.contentType is ContentType.Plot:
            self.drawFig(data, cbInfo.location, cbInfo.size)

        elif cbInfo.contentType is ContentType.Text:
            if type(data) is tuple and len(data) == 2:
                txt, color = data
                self.drawText(txt, cbInfo.location, cbInfo.size, color=color)
            else:
                self.drawText(data, cbInfo.location, cbInfo.size)

    def drawImage(self, im, loc, size, interp=None):
        
        loc = np.array(loc,dtype=np.uint)
        size = np.array(size,dtype=np.uint)

        # fix type
        if (im.astype(np.uint8) == im).all() and np.amax(im) > 1:
            # use as float im
            im = (im / 255).astype(np.float32)

        # grayscale in 3 channels
        if len(im.shape) == 2:
            im = np.stack((im,im,im),axis=2)
        
        # fix size
        cv2Size = (int(size[1]),int(size[0]))
        if interp is None:
            interp = cv2.INTER_LINEAR
        im = cv2.resize(im,cv2Size,interpolation=interp)
        
        # add im
        self.canvas[ loc[0] : (loc+size)[0] , loc[1] : (loc+size)[1]] = im
    
    def drawFig(self, data, loc, size):

        fig = plt.figure()
        for d in data:
            plt.plot(d)

        loc = np.array(loc,dtype=np.uint)
        size = np.array(size,dtype=np.uint)

        sizePLT = (size[1] // 25,size[0] // 25)

        fig.set_size_inches(*sizePLT)
        figCanvas = FigureCanvas(fig)
        figCanvas.draw()

        plotIm = cv2.cvtColor(
            np.array(fig.canvas.get_renderer()._renderer,dtype=np.float32) / 255,
            cv2.COLOR_RGB2GRAY
        )

        plt.close(fig)

        self.drawImage(plotIm, loc, size)
    
    def drawText(self, text, loc, size, color=(255,255,255)):

        text = str(text)
        loc = np.array(loc,dtype=np.uint)
        size = np.array(size,dtype=np.uint)

        cv2Origin = (int(loc[1]),int(loc[0] + size[0]))

        scale = 2
        (w, h), base = cv2.getTextSize(text, self.font, scale, 2)
        scale = scale * min(size[1]/w , size[0]/h)

        color = tuple(map(lambda p: p/255, color))

        # flush old text
        self.canvas[loc[0] : loc[0] + size[0] + 5, loc[1] : loc[1] + size[1]] = (0.0,0.0,0.0)
        
        # put new text
        cv2.putText(self.canvas, text, cv2Origin, self.font, scale, color=color, thickness=2, lineType=cv2.FILLED)
    
    def render(self):
        cv2.imshow(self.winName,self.canvas)
        key = cv2.waitKey(1)
        if key == 27:
            return False
        return True

    def cleanup(self):
        cv2.destroyWindow(self.winName)