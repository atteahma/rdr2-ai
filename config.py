# red dead 2 window name
captureWindowKeyword = 'Red Dead Redemption 2'

# output window
configWindowName = 'RDR2 AI'
configWindowLocation = (-3400,40)

# (x,y) offset from the bottom right that covers all options
optionsOffsetBR = (450,400)

keyPressLength = 0.2
mousePressLength = 0.2

# template matching and ocr params
craftingScoreThreshold = 10 ** -2
textColorTolerance = 25
OCRScaleFactor = 3
textPadding = 5
minOptionTextGap = 50
minHorLineHeight = 5
horLineCoverageThresh = 0.4 # [0,1]
OCRConfig = r'-l eng --psm 7 --oem 1'
minOCRConfidence = 30
saveDebugIms = False

spellcheckDistance = 2

# replace index 0 with index 1
freqMistakes = [('u','o'),('r','f'),('r','t'),('i','/'),('x','k'),('l','k'),('n','h')]
