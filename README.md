# keypad-io

 An event-based Python keypad library for the Raspberry Pi

## Features
- Allows for **_secondary_** characters for _telephone styled_ keypads
- **Event-based** architecture via **callback**/**listener** functions
- Allows for key detection via **interruptions** or **polling**
- Can support arbitrarily sized keypads
- Allows for custom GPIO numbering choice
- Dependent only on `RPi.GPIO`
- Project is fully typed to reduce ambiguity and confusion during use
- Can be used with context managers for consistent clean-up

## Installation

`keypad-io` is available on `PyPi` and can be installed using:

```
pip install keypad-io
```

## Requirements
`keypad-io` only has the following dependencies:
- `>= Python 3.11`
- `RPi.GPIO`

## Usage
```Python

# Not needed, but convenient to keep example application alive
import signal

try:
  """
  keypad-io can work with your existing RPi.GPIO setup
  given input and output pins don't conflict with other uses

  It will also follow your existing GPIO numbering
  """
  GPIO.setwarnings(False)
  GPIO.setmode(GPIO.BCM)
  
  input_pins = #specify your input pins (these usually are called "Column" pins)
  output_pins = #specify your output pins (these usually are called "Row" pins)

  """
  Callback function to be invoked when a key press is detected
  """
  def key_l(c: str, out: int, inp: int):
    print(" ==> received: ", c, f" ({out}, {inp})")
  
  """
  Character mapping between input and output pin positions with their expected
  characters. 

  Note: See that there are multiple choices for the second row, second column key.
  This means if that key is pressed multiple times sequentially (within a set amount of miliseconds)
  it will return the next key of choice.

  (ex: '8' at the first key press, 'T' at the second, etc.. and wrapping back to '8')
  """
  char_map = [
    ['*', '0', '#'], 
    ['7', ('8', "T", "U", "V"), '9'], 
    ['4', '5', '6'], 
    ['1', '2', '3']
  ]

  """
  Creates a Keypad with out set input_pins and output_pins, as well as character mapping.
  By giving poll=True, this Keypad will rely on continually polling the provided pins
  for key presses.

  We set key_l as an initial listener, and we want characters to be detected via polling
  rather than interrupts (which is the default)
  """
  with Keypad(input_pins, output_pins, char_map, poll=True) as k:
    k.add_listener(key_l)
    signal.pause()
  
  """
  keypad will invoke RPi.GPIO.cleanup() on the given input and output pins, as well as
  removing interrupt listening if it's chosen as the detection method
  """
except KeyboardInterrupt:
  print("Application stopped!")
```