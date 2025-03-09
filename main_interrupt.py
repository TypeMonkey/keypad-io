# import required libraries
import RPi.GPIO as GPIO
import time
import signal

# these GPIO pins are connected to the keypad
# change these according to your connections!
L1 = 17
L2 = 27
L3 = 22
L4 = 10

C1 = 26
C2 = 19
C3 = 13

cMap = [
    ['*', '0', '#'], 
    ['7', '8', '9'], 
    ['4', '5', '6'], 
    ['1', '2', '3']]

rowMap = {L1:1, L2:2, L3:3, L4:4}
colMap = {C1:1, C2:2, C3:3}

def callback(in_pin: int):
  #print("interrupt at ", in_pin, " | ", time.time_ns())
  if not GPIO.input(in_pin):
    #print("Button pressed!")

    for r in rowMap.keys():
      GPIO.output(r, GPIO.HIGH)
      if GPIO.input(in_pin) == GPIO.HIGH:
        print(f" ==> Row {r} is pressed: ({r},{in_pin})")
        GPIO.output(r, GPIO.LOW)
        break
      GPIO.output(r, GPIO.LOW)
      
  else:
    #print("Button released! IGNORED")
    pass

# Initialize the GPIO pins

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(L1, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(L2, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(L3, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(L4, GPIO.OUT, initial=GPIO.LOW)

# Make sure to configure the input pins to use the internal pull-down resistors

GPIO.setup(C1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(C1, GPIO.FALLING, callback=callback, bouncetime=50)

GPIO.setup(C2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(C2, GPIO.FALLING, callback=callback, bouncetime=50)

GPIO.setup(C3, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(C3, GPIO.FALLING, callback=callback, bouncetime=50)

try:
  print("start")
  signal.pause()
except KeyboardInterrupt:
  print("cleanedup")
  GPIO.cleanup()