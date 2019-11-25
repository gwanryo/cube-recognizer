import cv2, math, time
import numpy as np
import json

'''
This program is rubix cube color recognizer using OpenCV
2019. 11. 08
'''

# Sets of camera, Sets of camera view
cameras, screens = [], []

# Read from config, else use default value
CONFIG_FILE = 'cube.json'

# Quantity of camera
# Don't recommend change this value
CAMERA_OFFSET = 0; CAMERA_QUANTITY = 2

# Total camera delay
# If you reads 3 times, 1s of delay are given to each cameras
CAMERA_DELAY = 2

# Number of camera shots
CAMERA_TIMES = 3

# Width, Height of camera
CAMERA_WIDTH, CAMERA_HEIGHT = 320, 240

# Starting points of camera view windows
RENDER_BASE_X, RENDER_BASE_Y = 0, 0

# Window Titlebar
# Change it depends on your environment
RENDER_TITLEBAR_HEIGHT = 33

# Get average of color pixels in offset * offset square pixels, 
# Distance offset of grouping same colors
COLOR_AVERAGE_OFFSET, COLOR_DISTANCE_OFFSET = 3, 100

# Cube Object
# It defines 6 cube faces, including their position in camera, etc
CUBE = None

# Read settings from json
def readConfig(file):
    with open(file, 'r') as f:
        config = json.load(f)
    
    global CAMERA_OFFSET, CAMERA_QUANTITY
    CAMERA_OFFSET, CAMERA_QUANTITY = config['CAMERA_OFFSET'], config['CAMERA_QUANTITY']
    
    global CAMERA_DELAY, CAMERA_TIMES
    CAMERA_DELAY, CAMERA_TIMES = config['CAMERA_DELAY'], config['CAMERA_TIMES']

    global CAMERA_WIDTH, CAMERA_HEIGHT
    CAMERA_WIDTH, CAMERA_HEIGHT = config['CAMERA_WIDTH'], config['CAMERA_HEIGHT']

    global RENDER_BASE_X, RENDER_BASE_Y
    RENDER_BASE_X, RENDER_BASE_Y = config['RENDER_BASE_X'], config['RENDER_BASE_Y']

    global RENDER_TITLEBAR_HEIGHT
    RENDER_TITLEBAR_HEIGHT = config['RENDER_TITLEBAR_HEIGHT']

    global COLOR_AVERAGE_OFFSET, COLOR_DISTANCE_OFFSET
    COLOR_AVERAGE_OFFSET, COLOR_DISTANCE_OFFSET = \
        config['COLOR_AVERAGE_OFFSET'], config['COLOR_DISTANCE_OFFSET']

    global CUBE
    CUBE = config['CUBE']

# Render camera screen to window
def renderWindow(title, screen, x, y):
    cv2.imshow(title, screen)
    cv2.moveWindow(title, x, y)

def showWindow(i, cam, bgr, nY, nCr, nCb):
    # Define various camera view
    # Edit it if you want
    screens = [
        [
            'Camera{} - nY'.format(i), 
            nY, 
            RENDER_BASE_X + 0 * CAMERA_WIDTH, 
            RENDER_BASE_Y + i * (CAMERA_HEIGHT + RENDER_TITLEBAR_HEIGHT)
        ],
        [
            'Camera{} - nCr'.format(i), 
            nCr, 
            RENDER_BASE_X + 1 * CAMERA_WIDTH, 
            RENDER_BASE_Y + i * (CAMERA_HEIGHT + RENDER_TITLEBAR_HEIGHT)
        ],
        [
            'Camera{} - nCb'.format(i), 
            nCb, 
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
    for screen in screens:
        renderWindow(screen[0], screen[1], screen[2], screen[3])

    # If you want to save some images, use this function
    #cv.imwrite('test{}-gray.png'.format(i), gray)
    #cv.imwrite('test{}-ycrcb.png'.format(i), YCrCb)

    # Note. 0x1B (ESC)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        cam.release()

# Draw green circle on selected points
def drawPos(cubeObj, screen):
    for obj in cubeObj:
        for i, pixel in enumerate(obj['pixel']):
            x = pixel[0]; y = pixel[1]
            cv2.circle(screen, (x, y), 2, (0, 255, 0), -1)
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
            avgA += a[y, x]
            avgB += b[y, x]
            avgC += c[y, x]

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
            obj['color'][i] = (avgA, avgB, avgC)
            if i == 4: obj['center'] = (avgA, avgB, avgC)

# Calculate distance in color
def calDist(fromX, fromY, fromZ, toX, toY, toZ):
    return math.sqrt(
        abs(fromX * fromX - toX * toX)
        + abs(fromY * fromY - toY * toY)
        + abs(fromZ * fromZ - toZ * toZ))

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

# Clear cube faceString for renew calculation
def clearCube():
    global CUBE
    for obj in CUBE:
        obj['faceString'] = [str(i) for i in range(0, 9)]

def validate():
    # TODO: Validate if there is 9 tiles of each 6 colors,
    #       if not, recognize cube one more again or modify(not recommend) it.
    #       To modify cube info, you can remove farthest distance color.
    #       You can adjust led lights to clear camera's sight.
    global CUBE
    faceColor = [], faceQuantity = 0

    for obj in CUBE:
        # Calculating face color quantity
        if not faceQuantity:
            faceQuantity = len(obj['faceString'])

        for color in obj['faceString']:
            # Return false if faceString member has numerical value (initial value)
            try:
                int(obj['faceString'])
                return False
            except ValueError:
                pass

            if faceColor[color]:
                faceColor[color] += 1
            else:
                faceColor[color] = 0

    for count in faceColor:
        if count != faceQuantity:
            return False
    
    return True

def recognize():
    if len(cameras) == 0:
        readConfig(CONFIG_FILE)

    for i in range(CAMERA_OFFSET, CAMERA_OFFSET + CAMERA_QUANTITY + 1):
        cameras.append(cv2.VideoCapture(i))

    for cam in cameras:
        cam.set(3, CAMERA_WIDTH)  # cv2.CAP_PROP_FRAME_HEIGHT
        cam.set(4, CAMERA_HEIGHT)  # cv2.CAP_PROP_FRAME_WIDTH
    
    for i in range(0, CAMERA_TIMES + 1):
        for cam in cameras:
            ret, frame = cam.read()

            # Calculate YCrCb color range
            YCrCb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCR_CB)
            Y, Cr, Cb = cv2.split(YCrCb)
            nY = cv2.normalize(Y, None, 0, 255, cv2.NORM_MINMAX)
            nCr = cv2.normalize(Cr, None, 0, 255, cv2.NORM_MINMAX)
            nCb = cv2.normalize(Cb, None, 0, 255, cv2.NORM_MINMAX)

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
            else:
                cubeObj.append(CUBE[3])
                cubeObj.append(CUBE[4])
                cubeObj.append(CUBE[5])
            # ... Add something if you have more cameras

            # Write face info, and x, y value in camera view
            drawPos(cubeObj, frame)

            # Save center color, and 9 face colors
            saveColor(cubeObj, nY, nCr, nCb)

            if __name__ == "__main__":
                showWindow(i, cam, frame, nY, nCr, nCb)

        # Grouping same color
        groupColor()
        
        # Delay time for slow speed CPU
        time.sleep(CAMERA_DELAY / CAMERA_TIMES / len(cameras))

        # Print grouping color of each cube face
        for obj in CUBE:
            print(obj['face'] + '-' + ''.join(obj['faceString']))


def completeRecognize():
    faceValidate = False

    while faceValidate != True:
        recognize()
        faceValidate = validate()
        if not faceValidate:
            print("Recognition Failed")

'''
This is main code for executing this library directly
'''
def main():
    readConfig(CONFIG_FILE)

    for i in range(CAMERA_OFFSET, CAMERA_OFFSET + CAMERA_QUANTITY + 1):
        cameras.append(cv2.VideoCapture(i))

    for cam in cameras:
        cam.set(3, CAMERA_WIDTH)  # cv2.CAP_PROP_FRAME_HEIGHT
        cam.set(4, CAMERA_HEIGHT)  # cv2.CAP_PROP_FRAME_WIDTH

    while True:
        #clearCube()

        for i, cam in enumerate(cameras):
            ret, frame = cam.read()

            # Calculate YCrCb color range
            YCrCb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCR_CB)
            Y, Cr, Cb = cv2.split(YCrCb)
            nY = cv2.normalize(Y, None, 0, 255, cv2.NORM_MINMAX)
            nCr = cv2.normalize(Cr, None, 0, 255, cv2.NORM_MINMAX)
            nCb = cv2.normalize(Cb, None, 0, 255, cv2.NORM_MINMAX)

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
            else:
                cubeObj.append(CUBE[3])
                cubeObj.append(CUBE[4])
                cubeObj.append(CUBE[5])
            # ... Add something if you have more cameras

            # Write face info, and x, y value in camera view
            drawPos(cubeObj, frame)

            # Save center color, and 9 face colors
            saveColor(cubeObj, nY, nCr, nCb)
        
        # Grouping same color
        groupColor()

        # Print grouping color of each cube face
        for obj in CUBE:
            print(obj['face'] + '-' + ''.join(obj['faceString']))

        # Delay time for slow speed CPU
        time.sleep(CAMERA_DELAY / CAMERA_TIMES / len(cameras))

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
else:
    recognize()