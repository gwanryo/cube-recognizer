import cv2, math, time
import numpy as np
import json

if __name__ == "__main__":
    import sys
    from os import path
    print(path.dirname(path.dirname(path.abspath(__file__))))
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
    import cube_light as cl
else:
    from . import cube_light as cl

'''
This program is rubix cube color recognizer using OpenCV
2019. 11. 08
'''

CAMERAS                 = []            # Sets of camera
SCREENS                 = []            # Sets of camera view

CONFIG_FILE             = 'cube.json'   # Read from config, else use default value

CAMERA_URL              = [             # Set camera streaming url
    'http://localhost:8080/?action=stream',
    'http://localhost:8081/?action=stream'
]

CAMERA_DELAY            = 0.5           # Total camera delay
CAMERA_OFFSET           = 1             # Camera offset when using directly connected camera
CAMERA_WIDTH            = 320           # Width of camera
CAMERA_HEIGHT           = 240           # Height of camera

RENDER_BASE_X           = 0             # Starting x points of camera view windows
RENDER_BASE_Y           = 0             # Starting y points of camera view windows
RENDER_TITLEBAR_HEIGHT  = 33            # Window Titlebar                               # Change it depends on your environment

COLOR_AVERAGE_OFFSET    = 5             # Get average of color pixels in offset * offset square pixels
COLOR_DISTANCE_OFFSET   = 70            # Distance offset of grouping same colors
COLOR_CHROMATIC         = {             # To classify colors in specific range
    "C": ["Y", "G", "B"],
    "H": [14, 50, 92, 140],
    "S": 110,
    "V": 0
}

CUBE = None                             # Cube Object                                   # It defines 6 cube faces, including their position in camera, etc

# Read settings from json
def readConfig(file):
    with open(file, 'r') as f:
        config = json.load(f)

    global CAMERA_URL, CAMERA_DELAY, CAMERA_OFFSET
    CAMERA_URL, CAMERA_DELAY, CAMERA_OFFSET = config['CAMERA_URL'], config['CAMERA_DELAY'], config['CAMERA_OFFSET']

    global CAMERA_WIDTH, CAMERA_HEIGHT
    CAMERA_WIDTH, CAMERA_HEIGHT = config['CAMERA_WIDTH'], config['CAMERA_HEIGHT']

    global RENDER_BASE_X, RENDER_BASE_Y
    RENDER_BASE_X, RENDER_BASE_Y = config['RENDER_BASE_X'], config['RENDER_BASE_Y']

    global RENDER_TITLEBAR_HEIGHT
    RENDER_TITLEBAR_HEIGHT = config['RENDER_TITLEBAR_HEIGHT']

    global COLOR_AVERAGE_OFFSET
    COLOR_AVERAGE_OFFSET = config['COLOR_AVERAGE_OFFSET']

    global COLOR_DISTANCE_OFFSET
    COLOR_DISTANCE_OFFSET = config['COLOR_DISTANCE_OFFSET']

    global COLOR_CHROMATIC
    COLOR_CHROMATIC = config['COLOR_CHROMATIC']

    global CUBE
    CUBE = config['CUBE']

# Draw green circle on selected points
def drawPos(cubeObj, screen):
    for obj in cubeObj:
        for i, pixel in enumerate(obj['pixel']):
            x = pixel[0]; y = pixel[1]
            cv2.circle(screen, (x, y), COLOR_AVERAGE_OFFSET, (0, 255, 0), -1)
            cv2.putText(screen, '{}{}'.format(obj['face'], i), #[{}, {}]'.format(obj['face'], i, x, y),
                (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (0, 0, 0))

# Calculate average color in range of -offset/2 ~ offset/2
def calAvgColor(a, b, c, x, y, offset):
    fromX = math.ceil(x - offset / 2); toX = math.ceil(x + offset / 2)
    fromY = math.ceil(y - offset / 2); toY = math.ceil(y + offset / 2)

    if fromX < 0: fromX = 0
    if toX >= CAMERA_WIDTH: toX = CAMERA_WIDTH - 1
    if fromY < 0: fromY = 0
    if toY >= CAMERA_HEIGHT: toY = CAMERA_HEIGHT - 1

    avgA = 0; avgB = 0; avgC = 0
    for aY in range(fromY, toY):
        for aX in range(fromX, toX):
            avgA += a[aY, aX]
            avgB += b[aY, aX]
            avgC += c[aY, aX]

    powOffset = offset * offset
    avgA = math.floor(avgA / powOffset)
    avgB = math.floor(avgB / powOffset)
    avgC = math.floor(avgC / powOffset)

    return avgA, avgB, avgC

# Save average color, and set center color
def saveColor(cubeObj, a, b, c):
    for obj in cubeObj:
        for i, pixel in enumerate(obj['pixel']):
            x = pixel[0]; y = pixel[1]
            avgA, avgB, avgC = calAvgColor(a, b, c, x, y, COLOR_AVERAGE_OFFSET)

            if len(obj['color'][i]) == 3:
                obj['color'][i] = ((obj['color'][i][0] + avgA) / 2,
                                    (obj['color'][i][1] + avgB) / 2,
                                    (obj['color'][i][2] + avgC) / 2)
            else:
                obj['color'][i] = (avgA, avgB, avgC)

            if i == 4: obj['center'] = obj['color'][i]

# Calculate distance in color
def calDist(fromX, fromY, fromZ, toX, toY, toZ):
    return math.sqrt(
        (fromX - toX) * (fromX - toX)
        + (fromY - toY) * (fromY - toY)
        + (fromZ - toZ) * (fromZ - toZ))

# Grouping similar colors detected in camera
def groupColor():
    global CUBE
    for fromObj in CUBE:
        for toObj in CUBE:
            # Get center pixel color of cube face
            i = 0; fromX, fromY, fromZ = fromObj['center']
            for toX, toY, toZ in toObj['color']:
                distance = calDist(fromX, fromY, fromZ, toX, toY, toZ)

                # If color distance is smaller than distance offset,
                # put them in same color group
                if distance < COLOR_DISTANCE_OFFSET:
                    toObj['faceString'][i] = fromObj['face']

                i += 1

# Find face string using color string
def findFaceUsingColor(c):
    global CUBE

    for obj in CUBE:
        if obj['centerColor'] == c:
            return obj['face']

    return None

# Set center color using specific range
def setCenterColor():
    global CUBE, COLOR_CHROMATIC
    cC = COLOR_CHROMATIC['C']; cH = COLOR_CHROMATIC['H']; cS = COLOR_CHROMATIC['S']
    redOrange = (-1, 0)

    for n, obj in enumerate(CUBE):
        h, s, v = obj['center']
        if s <= cS:
            obj['centerColor'] = "W"
        else:
            if h < cH[0] or h >= cH[-1]:
                if h < cH[0]: h += 181

                if redOrange[0] != -1:
                    if h < redOrange[0]:
                        obj['centerColor'] = "R"
                        CUBE[redOrange[1]]['centerColor'] = "O"
                    else:
                        obj['centerColor'] = "O"
                        CUBE[redOrange[1]]['centerColor'] = "R"
                else:
                    redOrange = (h, n)
            else:
                for colorStr, lower, upper in list(zip(cC, cH[:-1], cH[1:])):
                    if lower <= h < upper:
                        obj['centerColor'] = colorStr

# Classify Red and Orange
def classifyRedOrange(roList):
    global CUBE

    if len(roList) != 9 * 2:
        print("classify Red & Orange failed! length of roList is {}".format(len(roList)))
    
    roList = sorted(roList, key=lambda x: x[-1])

    for k, (n, i, c) in enumerate(roList):
        print("Face {} - {} : {}".format(CUBE[n]['face'], i, c))
        if k < 9:
            faceColor = findFaceUsingColor("R")
            if faceColor: CUBE[n]['faceString'][i] = faceColor
        else:
            faceColor = findFaceUsingColor("O")
            if faceColor: CUBE[n]['faceString'][i] = faceColor

# Classify colors in specific range
# W, Y, G, B, RO
def classifyColor():
    global CUBE, COLOR_CHROMATIC
    cC = COLOR_CHROMATIC['C']; cH = COLOR_CHROMATIC['H']; cS = COLOR_CHROMATIC['S']
    roList = []
    
    setCenterColor()

    for n, obj in enumerate(CUBE):
        for i, (h, s, v) in enumerate(obj['color']):
            if s <= cS:
                faceColor = findFaceUsingColor("W")
                if faceColor: obj['faceString'][i] = faceColor
            else:
                if h < cH[0]:
                    roList.append((n, i, h + 181))
                elif h >= cH[-1]:
                    roList.append((n, i, h))
                else:
                    for colorStr, lower, upper in list(zip(cC, cH[:-1], cH[1:])):
                        if lower <= h < upper:
                            faceColor = findFaceUsingColor(colorStr)
                            if faceColor: obj['faceString'][i] = faceColor
    
    if len(roList):
        classifyRedOrange(roList)

# Clear cube faceString for renew calculation
def clearCube():
    global CUBE
    for obj in CUBE:
        obj['faceString'] = [str(i) for i in range(9)]
        obj['color'] = ['' for i in range(9)]

def validate():
    # TODO: Validate if there is 9 tiles of each 6 colors,
    #       if not, recognize cube one more again or modify(not recommend) it.
    #       To modify cube info, you can remove farthest distance color.
    #       You can adjust led lights to clear camera's sight.
    global CUBE
    faceColor = {}

    for obj in CUBE:
        # Calculating face color quantity
        faceQuantity = len(obj['faceString'])

        for color in obj['faceString']:
            # Return false if faceString member has numerical value (initial value)
            try:
                color.replace('.', '', 1).isdigit()
            except:
                print("Validation Fail - Numerical value")
                return False

            try:
                faceColor[color] += 1
            except:
                faceColor[color] = 1

    for key, count in faceColor.items():
        print("Face {}'s color quantity - {}".format(key, count))

    for key, count in faceColor.items():
        if count != faceQuantity:
            return False

    print("Validation OK")
    return True

def cubeRecognize():
    global CAMERAS, CAMERA_OFFSET

    if len(CAMERAS) == 0:
        readConfig(CONFIG_FILE)

        CAMERAS = []
        for i, u in enumerate(CAMERA_URL):
            cap = cv2.VideoCapture(u)
            if cap is None or not cap.isOpened():
                print("Warning: Not valid streaming url, so try to use directly connected camera.")
                CAMERAS.append(cv2.VideoCapture(i + CAMERA_OFFSET))
            else:
                CAMERAS.append(cv2.VideoCapture(u))

        for cam in CAMERAS:
            cam.set(3, CAMERA_WIDTH)    # cv2.CAP_PROP_FRAME_HEIGHT
            cam.set(4, CAMERA_HEIGHT)   # cv2.CAP_PROP_FRAME_WIDTH

    for i, cam in enumerate(CAMERAS):
        _, frame = cam.read()

        # Calculate YCrCb color range
        #YCrCb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCR_CB)
        #Y, Cr, Cb = cv2.split(YCrCb)
        #nY = cv2.normalize(Y, None, 0, 255, cv2.NORM_MINMAX)
        #nCr = cv2.normalize(Cr, None, 0, 255, cv2.NORM_MINMAX)
        #nCb = cv2.normalize(Cb, None, 0, 255, cv2.NORM_MINMAX)

        # Calculate HSV color range
        HSV = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        H, S, V = cv2.split(HSV)
        nH = cv2.normalize(H, None, 0, 255, cv2.NORM_MINMAX)
        nS = cv2.normalize(S, None, 0, 255, cv2.NORM_MINMAX)
        nV = cv2.normalize(V, None, 0, 255, cv2.NORM_MINMAX)

        # Camera 1 = B, R, D
        # Camera 2 = U, L, F
        cubeObj = []
        if i == 0:
            cubeObj.append(CUBE[0])
            cubeObj.append(CUBE[1])
            cubeObj.append(CUBE[2])
        elif i == 1:
            cubeObj.append(CUBE[3])
            cubeObj.append(CUBE[4])
            cubeObj.append(CUBE[5])
        # ... Add something if you have more CAMERAS

        # Write face info, and x, y value in camera view
        drawPos(cubeObj, frame)

        # Save center color, and 9 face colors
        saveColor(cubeObj, H, S, V)

        if __name__ == "__main__":
            showWindow(i, cam, frame, H, S, V)
        else:
            # Delay time for slow speed CPU
            time.sleep(CAMERA_DELAY / len(CAMERAS))

    # Grouping same color
    groupColor()

    # Classify specific range of color
    classifyColor()

    for obj in CUBE:
        print("Face {} - {}, {}".format(obj['face'], obj['center'], obj['centerColor']))
        for i, (h, s, v) in enumerate(obj['color']):
            print("{} - ({}, {}, {})".format(i, h, s, v))

    # Print grouping color of each cube face
    for obj in CUBE:
        print(obj['face'] + '-' + ''.join(obj['faceString']))

# Try recognition as given number
def recognize(num = 5, brightness = cl.LED_BRIGHTNESS):
    faceValidate = False

    if brightness != cl.LED_BRIGHTNESS:
        cl.whiteWipe(brightness)

    for _ in range(0, num):
        if CUBE:
            clearCube()
        cubeRecognize()
        faceValidate = validate()
        if faceValidate:
            return {
                "success": 1,
                "cube": CUBE
            }

    return {
        "success": 0,
        "cube": CUBE
    }

#############################################
#   Functions below are for main function   #
#############################################

# Render camera screen to window
def renderWindow(title, screen, x, y):
    cv2.imshow(title, screen)
    cv2.moveWindow(title, x, y)

def showWindow(i, cam, bgr, a, b, c):
    # Define various camera view
    # Edit it if you want
    SCREENS = [
        [
            'Camera{} - Alpha'.format(i), 
            a, 
            RENDER_BASE_X + 0 * CAMERA_WIDTH, 
            RENDER_BASE_Y + i * (CAMERA_HEIGHT + RENDER_TITLEBAR_HEIGHT)
        ],
        [
            'Camera{} - Beta'.format(i), 
            b, 
            RENDER_BASE_X + 1 * CAMERA_WIDTH, 
            RENDER_BASE_Y + i * (CAMERA_HEIGHT + RENDER_TITLEBAR_HEIGHT)
        ],
        [
            'Camera{} - Gamma'.format(i), 
            c, 
            RENDER_BASE_X + 2 * CAMERA_WIDTH, 
            RENDER_BASE_Y + i * (CAMERA_HEIGHT + RENDER_TITLEBAR_HEIGHT)
        ],
        [
            'Camera{} - Pixel'.format(i), 
            bgr, 
            RENDER_BASE_X + 3 * CAMERA_WIDTH, 
            RENDER_BASE_Y + i * (CAMERA_HEIGHT + RENDER_TITLEBAR_HEIGHT)
        ],
    ]

    # Rendering windows for each pre-defined camera view
    for screen in SCREENS:
        renderWindow(screen[0], screen[1], screen[2], screen[3])

    # If you want to save some images, use this function
    #cv.imwrite('test{}-gray.png'.format(i), gray)
    #cv.imwrite('test{}-ycrcb.png'.format(i), YCrCb)

    # Note. 0x1B (ESC)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        cam.release()

'''
This is main code for executing this library directly
'''
def main():
    while True:
        cubeRecognize()
        time.sleep(1)

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
