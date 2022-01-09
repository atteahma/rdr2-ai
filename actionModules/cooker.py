from rdr2_ai.controls.actionHandler import ActionType
from rdr2_ai.configWindow.configWindowTemplate import ConfigWindowTemplate, ContentType
from rdr2_ai.module import Module
from rdr2_ai.utils.utils import allAnyCloseEnough, anyCloseEnough, closeEnough
from rdr2_ai.analysisModules.options import OptionsGetter


cookerConfigWindowTemplate = ConfigWindowTemplate() \
    .setSize(height=800, width=1200) \
    .addStaticText('Raw Options Frame',(10,100),(40,400)) \
    .addContentBox('optionsFrameRaw',ContentType.Image,(60,100),(400,400)) \
    .addStaticText('Cleaned Options Frame',(10,600),(40,400)) \
    .addContentBox('optionsFrameClean',ContentType.Image,(60,600),(400,400)) \
    .addStaticText('Frames/s:', (600,100), (30,100)) \
    .addContentBox('fps', ContentType.Text, (600,300), (30,100))

class Cooker(Module):

    def __init__(self, configWindow=None):
        self.configWindow = configWindow
        self.optionsGetter = OptionsGetter(configWindow=configWindow, showInConfigWindow=True)

    def cleanup(self):
        pass

    def getActions(self, frame):
        
        # get options
        options = self.optionsGetter.getOptions(frame)

        actions = []
        if len(options) == 1:
            option = options[0]

            if closeEnough(option,'cook'):
                # we are actively cooking
                actions = [(ActionType.HOLD,'SPACEBAR')]
            
            elif closeEnough(option,'back'):
                # we are out of this ingredient, go back to crafting
                actions = [(ActionType.TAP,'f')]
        
        elif len(options) == 2:
            optionA,optionB = options

            if closeEnough(optionA,'cook another'):
                # we already took care of the case when we run out of
                # ingredients in the 'back' case, so cook another
                actions = [(ActionType.TAP,'SPACEBAR')]
            
            elif closeEnough(optionA,'eat') and closeEnough(optionB,'stow'):
                # release holding spacebar, then always stow
                actions = [
                    (ActionType.RELEASE,'SPACEBAR'),
                    (ActionType.TAP,'r'),
                ]
            
            elif anyCloseEnough(optionA,['craft/cook','craftcook','craft cook']):
                actions = [(ActionType.TAP,'r')]

        # this makes it run forever, but makes it robust against missing word 'cook' one frame
        # elif len(options) == 3:
        #     if allAnyCloseEnough(options,['show craftable','effects','leave']):
        #         actions = [(ActionType.DONE,'')]

        #     elif allAnyCloseEnough(options,['craftable','effects','leave']): # hack
        #         actions = [(ActionType.DONE,'')]

        elif len(options) in [4,5]:

            if allAnyCloseEnough(options,['recipe','all','show all','ingredients','effects','cook','brew','leave']):
                if anyCloseEnough('cook', options):
                    actions = [(ActionType.TAP,'ENTER')]
                # else:
                #     actions = [(ActionType.DONE, '')]

        else:
            pass
            #self.print(f'error in getActions [len(options)={len(options)}]')

        return actions
