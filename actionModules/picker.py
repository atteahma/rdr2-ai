from enum import Enum, auto
from typing import Callable

import numpy as np
import cv2

from rdr2_ai.analysisModules.options import OptionsGetter
from rdr2_ai.module import Module
from rdr2_ai.utils.state import StateMachine
from rdr2_ai.configWindow.configWindow import ConfigWindow

class PickerState(Enum):
    SEARCHING = auto()
    FOUND = auto()
    APPROACHING = auto()
    PICKING = auto()

class PickerStateMachine(StateMachine):

    def __init__(self, printFunc: Callable,
                       configWindow: ConfigWindow = None):
        super().__init__()

        self.print = printFunc

        # boiler plate
        self.actionStateFunctions[PickerState.SEARCHING  ] = self.searching
        self.actionStateFunctions[PickerState.FOUND      ] = self.found
        self.actionStateFunctions[PickerState.APPROACHING] = self.approaching
        self.actionStateFunctions[PickerState.PICKING    ] = self.picking
        self.setState(PickerState.SEARCHING)

        # specifics [trying out slightly different design to fisher: giving a lot more
        # analysis power to the state machine rather than precompute everything in main
        # action module and then use those to compute state.]
        self.optionsGetter = OptionsGetter(configWindow=configWindow,
                                           showInConfigWindow=True)
    
    def searching(self, frame):
        return [], PickerState.SEARCHING
    
    def found(self, frame):
        return [], PickerState.FOUND
    
    def approaching(self, frame):
        return [], PickerState.APPROACHING
    
    def picking(self, frame):
        return [], PickerState.PICKING

class Picker(Module):

    def __init__(self, configWindow: ConfigWindow):
        self.configWindow = configWindow
        self.stateMachine = PickerStateMachine(self.print, configWindow=configWindow)

    def getActions(self, frame: np.ndarray):

        actions = self.stateMachine.getActionsAndUpdateState(frame)

        return actions
    