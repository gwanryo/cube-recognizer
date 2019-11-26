from neopixel import *
import time, json

'''
This program is for light adjustment in rubix cube recognizer
2019. 11. 25
'''

LIGHT_CONFIG    = 'light.json'
LED_COUNT       = 16        # Number of LED pixels.
LED_PIN         = 18        # GPIO pin connected to the pixels (18 uses PWM!).
LED_FREQ_HZ     = 800000    # LED signal frequency in hertz (usually 800khz)
LED_DMA         = 10        # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS  = 30        # Set to 0 for darkest and 255 for brightest
LED_INVERT      = False     # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL     = 0         # set to '1' for GPIOs 13, 19, 41, 45 or 53
STRIP           = None      

# Read settings from json
def readConfig(file):
    with open(file, 'r') as f:
        config = json.load(f)

    global LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_BRIGHTNESS, LED_INVERT, LED_CHANNEL, STRIP
    LED_COUNT = config['LED_COUNT']
    LED_PIN = config['LED_PIN']
    LED_FREQ_HZ = config['LED_FREQ_HZ']
    LED_DMA = config['LED_DMA']
    LED_BRIGHTNESS = config['LED_BRIGHTNESS']
    LED_INVERT = True if config['LED_INVERT'] == 1 else False
    LED_CHANNEL = config['LED_CHANNEL']

    # Create NeoPixel object with appropriate configuration.
    STRIP = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)

# Read config
def reloadConfig(file):
    data = {}
    data['LED_COUNT'] = LED_COUNT
    data['LED_PIN'] = LED_PIN
    data['LED_FREQ_HZ'] = LED_FREQ_HZ
    data['LED_DMA'] = LED_DMA
    data['LED_BRIGHTNESS'] = LED_BRIGHTNESS
    data['LED_INVERT']= 1 if LED_INVERT else 0
    data['LED_CHANNEL'] = LED_CHANNEL

    with open(file, 'w') as f:
        json.dump(data, f)

    readConfig(LIGHT_CONFIG)

# Wipe color across display a pixel at a time.
def colorWipe(color, wait_ms=50):
    for i in range(STRIP.numPixels()):
        STRIP.setPixelColor(i, color)
        STRIP.show()
        time.sleep(wait_ms/1000.0)

# Clear whole led lights
def clearWipe(wait_ms=50):
    colorWipe(Color(0, 0, 0), 10)

# Set LED Brightness
def setBrightness(num):
    if num > 255 or num < 0:
        return False
    
    global LED_BRIGHTNESS
    LED_BRIGHTNESS = num

    try:
        clearWipe()
        reloadConfig(LIGHT_CONFIG)
        return True
    except:
        return False

# Whipe whole led in specific brightness
def whiteWipe(brightness = LED_BRIGHTNESS):
    if not STRIP:
        readConfig(LIGHT_CONFIG)
        
    if brightness != LED_BRIGHTNESS:
        setBrightness(brightness)

    colorWipe(Color(255, 255, 255), 10)
