from types import FunctionType
from typing import Dict
from enum import IntEnum

class StateMachine:
    def __init__(self):
        self.actionStateFunctions: Dict[IntEnum, FunctionType] = {}
        self.state = -1
        self.invalidQueries = []
    
    def setState(self, state):
        if state is not self.state:
            self.state = state
            self.currentActionStateFunction = self.actionStateFunctions[self.state]
    
    def getActionsAndUpdateState(self, **data):
        if len(data) == 1:
            data = data[0]

        res = self.currentActionStateFunction(data)
        if res is None:
            self.invalidQueries.append((self.state, data))
            return []
        actions, nextState = res
        self.setState(nextState)
        return actions
