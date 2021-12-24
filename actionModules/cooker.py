from rdr2_ai.controls.actionHandler import ActionType
from rdr2_ai.configWindow.configWindowTemplate import ConfigWindowTemplate, ContentType
from rdr2_ai.module import Module
from rdr2_ai.utils.utils import allAnyCloseEnough, anyCloseEnough, closeEnough
from rdr2_ai.analysisModules.options import OptionsGetter


cookerConfigWindowTemplate = ConfigWindowTemplate() \
    .setSize(height=600, width=1200) \
    .addStaticText('Raw Options Frame',(10,100),(40,400)) \
    .addContentBox('optionsFrameRaw',ContentType.Image,(60,100),(400,400)) \
    .addStaticText('Cleaned Options Frame',(10,600),(40,400)) \
    .addContentBox('optionsFrameClean',ContentType.Image,(60,600),(400,400))

class Cooker(Module):

    def __init__(self, configWindow=None):
        self.configWindow = configWindow
        self.optionsGetter = OptionsGetter(configWindow=configWindow, showInConfigWindow=True)

    def getActions(self, frame):
        
        # get options
        options,success = self.optionsGetter.getOptions(frame)
        if not success:
            # not fatal, could be fixed next frame
            pass

        actions,success = [],False
        
        if len(options) == 1:
            option = options[0]

            if closeEnough(option,'cook'):
                # we are actively cooking
                actions,success = [(ActionType.HOLD,'SPACEBAR')],True
            
            elif closeEnough(option,'back'):
                # we are out of this ingredient, go back to crafting
                actions,success = [(ActionType.TAP,'f')],True
        
        elif len(options) == 2:
            optionA,optionB = options

            if closeEnough(optionA,'cook another'):
                # we already took care of the case when we run out of
                # ingredients in the 'back' case, so cook another
                actions,success = [(ActionType.TAP,'SPACEBAR')],True
            
            elif closeEnough(optionA,'eat') and closeEnough(optionB,'stow'):
                # release holding spacebar, then always stow
                actions,success = [
                    (ActionType.RELEASE,'SPACEBAR'),
                    (ActionType.TAP,'r'),
                ],True
            
            elif anyCloseEnough(optionA,['craft/cook','craftcook','craft cook']):
                actions,success = [(ActionType.TAP,'r')],True

        elif len(options) == 3:
            if allAnyCloseEnough(options,['show craftable','effects','leave']):
                return [(ActionType.DONE,'')],True

            if allAnyCloseEnough(options,['craftable','effects','leave']): # hack
                return [(ActionType.DONE,'')],True

        elif len(options) in [4,5]:

            if allAnyCloseEnough(options,['recipe','show all','ingredients','effects','cook','brew','leave']):
                if anyCloseEnough('cook', options):
                    actions,success = [(ActionType.TAP,'ENTER')],True
                else:
                    actions,success = [(ActionType.DONE, '')],True

        else:
            pass
            #self.print(f'error in getActions [len(options)={len(options)}]')

        return actions,success
