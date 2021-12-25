from enum import Enum
from time import sleep, time
from dataclasses import dataclass
import argparse
import sys

from timerUtility.profiler import Profiler

from rdr2_ai import config
from rdr2_ai.controls.actionHandler import ActionHandler
from rdr2_ai.module import Module
from rdr2_ai.configWindow.configWindow import ConfigWindow
from rdr2_ai.actionModules.cooker import Cooker,cookerConfigWindowTemplate
from rdr2_ai.actionModules.fisher import Fisher,fisherConfigWindowTemplate
from rdr2_ai.actionModules.chorer import Chorer,chorerConfigWindowTemplate
from rdr2_ai.actionModules.recorder import Recorder
from rdr2_ai.utils.capture import Capture


class AIMode(Enum):
    COOK = 'cook'
    FISH = 'fish'
    CHORES = 'chores'
    RECORD = 'record'

@dataclass
class AIArguments:
    mode: str
    showConfigWindow: bool
    initTime: int
    recordDir: str
    doProfile: bool

class Main(Module):

    def __init__(self, args: AIArguments):
        
        # get config settings
        self.initTime = args.initTime
        captureWindowKeyword = config.captureWindowKeyword
        outputWindowName = config.configWindowName
        outputWindowLocation = config.configWindowLocation

        # init modules
        self.capture = Capture(captureWindowKeyword, updateWindow=False)
        if args.showConfigWindow:
            self.configWindow = ConfigWindow(outputWindowName,outputWindowLocation)
        else:
            self.configWindow = None
        if args.doProfile:
            self.profiler = Profiler(profilerLoop=['capture','getActions','doActions','internalInfo'])
        else:
            self.profiler = None
        self.actionHandler = ActionHandler(configWindow=self.configWindow)

        # init mode module(s)
        mode = AIMode(args.mode)
        if mode is AIMode.COOK:
            self.actionModule = Cooker(configWindow=self.configWindow)
            if self.configWindow:
                self.configWindow.useTemplate(cookerConfigWindowTemplate)
        elif mode is AIMode.FISH:
            self.actionModule = Fisher(configWindow=self.configWindow)
            if self.configWindow:
                self.configWindow.useTemplate(fisherConfigWindowTemplate)
        elif mode is AIMode.CHORES:
            self.actionModule = Chorer(configWindow=self.configWindow)
            if self.configWindow:
                self.configWindow.useTemplate(chorerConfigWindowTemplate)
        elif mode is AIMode.RECORD:
            self.actionModule = Recorder(args.recordDir)

    def runMainLoop(self):
        self.initCountdown()

        frameNum = 0
        run = True
        while run:
            
            frameStartTime = time()

            self.print(f'frame {frameNum}')

            if self.profiler:
                self.profiler.profilerBreak()

            # capture window
            frame = self.capture.captureWindow()

            if self.profiler:
                self.profiler.profilerBreak()

            # get actions
            actions = self.actionModule.getActions(frame)

            if self.profiler:
                self.profiler.profilerBreak()

            # do actions
            if len(actions) > 0:
                for action in actions:
                    if self.actionHandler.isDoneAction(action):
                        self.print(f'finished!')
                        run = False
                        break

                    success = self.actionHandler.doAction(action)
                    if not success:
                        self.print(f'error in doAction [action={action}]')

            if self.profiler:
                self.profiler.profilerBreak()

            if run:
                self.actionHandler.printHeldKeys()

            frameNum += 1

            # temp, make into fps module later
            currFPS = round(1/(time() - frameStartTime))
            if self.configWindow:
                self.configWindow.drawToTemplate('fps', str(currFPS))
            else:
                self.print(f'Frames/s = {currFPS}')

            if self.configWindow:
                continueLoop = self.configWindow.render()
                if not continueLoop:
                    run = False

        # release all held keys
        self.actionHandler.releaseAll()

        if self.configWindow:
            self.configWindow.cleanup()
        
        if self.profiler:
            self.profiler.printStats()

    def initCountdown(self):
        seconds = self.initTime
        print(f'starting in', end='')
        while seconds > 0:
            print(f' {seconds}', end='', flush=True)
            seconds -= 1
            sleep(1)
        print()

if __name__ == '__main__':

    argParser = argparse.ArgumentParser(description='Start the AI Engine.')
    argParser.add_argument('--mode', '-m',
                           required=True, type=str, choices=[m.value for m in AIMode],
                           help='Select Action Module to use.')
    argParser.add_argument('--showConfigWindow', '-c',
                           default=False, action='store_true',
                           help='Show visualizations of the inner workings.')
    argParser.add_argument('--recordDir', '-d',
                           default='', required=' record' in sys.argv,
                           help='The directory to store recorded frames in.')
    argParser.add_argument('--initTime', '-t',
                           default=3, type=int,
                           help='The length (sec) of the initial countdown.')
    argParser.add_argument('--doProfile', '-p',
                           default=False, action='store_true',
                           help='Show profiling information on exit.')

    parsedArgsObj = argParser.parse_args()
    aiArgs = AIArguments(**vars(parsedArgsObj))
    
    main = Main(aiArgs)
    main.runMainLoop()
