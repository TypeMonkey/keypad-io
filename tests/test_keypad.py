import unittest
import types
import sys
import time
import threading
from typing import Any

def createRPIGPIOMock():
  """
  Creates a mock of the RPi.GPIO module 
  so that these tests don't have to run on a Raspberry Pi
  """
  module_name = 'RPi.GPIO'
  bogus_module = types.ModuleType(module_name)

  def setup_mock(i: int, s: int, initial=0, pull_up_down=1):
    pass

  def add_event_detect_mock(i: int, s: int, callback=None, bouncetime: int = 0):
    pass

  def remove_event_detect_mock(i: int):
    pass

  def cleanup_mock(i: list[int]):
    pass

  bogus_module.IN = 1
  bogus_module.PUD_UP = 22
  bogus_module.OUT = 0
  bogus_module.LOW = 0
  bogus_module.FALLING = 32
  bogus_module.setup = setup_mock
  bogus_module.add_event_detect = add_event_detect_mock
  bogus_module.remove_event_detect = remove_event_detect_mock
  bogus_module.cleanup = cleanup_mock

  return bogus_module

sys.modules['RPi.GPIO'] = createRPIGPIOMock()

from keypad import Keypad

class KeypadCases(unittest.TestCase):
  def test_constructor(self):
    # Test if constructor throws ValueError at char_map with wrong dimensions

    # Correct case
    in_pins = [1,2,3,4,5]
    out_pins = [7,8,9]
    cMap_correct = [
      ["a", "b", "c", "e", "f"],
      ["g", "h", "i", "j", "k"],
      ["l", "m", "n", "n", "o"]
    ]
    with Keypad(in_pins, out_pins, cMap_correct) as k:
      pass

    # Incorrect case 1
    in_pins = [1,2,3,4,5]
    out_pins = [7,8,9]
    cMap_wrong = [
      ["a", "b", "c", "e", "f"],
      ["g", "h", "j", "k"],
      ["l", "m", "n", "o"]
    ]
    try:
      with Keypad(in_pins, out_pins, cMap_wrong) as k:
        self.fail("Keypad initiated correctly despite jagged char_matrix")
    except ValueError as e:
      pass

    # Incorrect case 2
    cMap = [
      ["a", "b", "c", "e", "f"],
      ["g", "h", "i", "j", "k"],
      ["l", "m", "n", "n", "o"]
    ]
    cMap = [[cMap[j][i] for j in range(len(cMap))] for i in range(len(cMap[0]))]
    try:
      with Keypad(in_pins, out_pins, cMap) as k:
        self.fail("Keypad initiated correctly despite wrong dimensions")
    except ValueError as e:
      pass

    # Test if constructor correctly initializes __key_map__
    cMap = [
      ["a", "b", "c", "e", "f"],
      [("g", "^", "*", "("), "h", "i", "j", "k"],
      ["l", "m", ("n", '1', '2', '3'), "n", "o"]
    ]
    with Keypad(in_pins, out_pins, cMap) as k:
      # Check __key_map__
      l = [True if isinstance(c, tuple) and \
                   len(c) == 3 and \
                   isinstance(c[0], tuple) and \
                   isinstance(c[1], int) and c[1] == -1 and \
                   isinstance(c[2], int) and c[2] == 0 \
                   else False 
           for r in k.__key_map__ 
           for c in r]
      if not all(l):
        self.fail("not all elements are 3 element tuples (str, int, int)")

  def test_determine_key(self):
    # Test if the correct keys are being determined

    # Simple keypad
    in_pins = [1,2,3,4,5]
    out_pins = [7,8,9]
    cMap = [
      ["a", "b", "c", "e", "f"],
      ["g", "h", "i", "j", "k"],
      ["l", "m", "n", "n", "o"]
    ]
    with Keypad(in_pins, out_pins, cMap) as k:
      """
      using the default values of:
      key_delay = 100 miliseconds (100000000 ns)
      secondary_max_gap = 200 miliseconds (200000000 ns)

      __determine_key__() shouldn't take key_delay into consideration
      as that's determined by the polling/interrupt functions via
      sleep/bounce times.

      __determine_key__() is essentially in keys with secondary choices.
      """
      current_ns = time.time_ns()

      r = k.__determine_key__(0,0, current_ns)
      self.assertEqual(r, (0,0, "a"))

      r = k.__determine_key__(0,0, current_ns + 5)
      self.assertEqual(r, (0,0, "a"))

    # Keypad with multiple options for the "8" key
    in_pins = [1,2,3]
    out_pins = [4,5,6,7]
    cMap = [
      ['*', '0', '#'], 
      ['7', ('8', "T", "U", "V"), '9'], 
      ['4', '5', '6'], 
      ['1', '2', '3']
    ]
    with Keypad(in_pins, out_pins, cMap) as k:
      """
      using the default values of:
      key_delay = 100 miliseconds (100000000 ns)
      secondary_max_gap = 200 miliseconds (200000000 ns)
      """
      current_ns = time.time_ns()

      r = k.__determine_key__(0,0, current_ns)
      self.assertEqual(r, (0,0, "*"))

      r = k.__determine_key__(0,0, current_ns + 5)
      self.assertEqual(r, (0,0, "*"))

      current_ns = time.time_ns()
      r = k.__determine_key__(1,1, current_ns)
      self.assertEqual(r, (1,1, "8"))

      r = k.__determine_key__(1,1, k.__key_map__[1][1][1] + 5)
      self.assertEqual(r, (1,1, "T"))

      r = k.__determine_key__(1,1, k.__key_map__[1][1][1] + 200000001)
      self.assertNotEqual(r, (1,1, "U"))
      r = k.__determine_key__(1,1, k.__key_map__[1][1][1] + 200000001)
      self.assertEqual(r, (1,1, "8"))

  def test_correct_char_map(self):
    # Test correct_char_map()

    # Keypad with multiple options for the "8" key
    in_pins = [1,2,3]
    out_pins = [4,5,6,7]
    correct_Map = [
      ['1', '2', '3'],
      ['4', '5', '6'], 
      ['7', ('8', "T", "U", "V"), '9'],
      ['*', '0', '#']
    ]
    cMap = [
      ['*', '0', '#'], 
      ['7', ('8', "T", "U", "V"), '9'], 
      ['4', '5', '6'], 
      ['1', '2', '3']
    ]
    with Keypad(in_pins, out_pins, cMap) as k:
      s = list("1234567")+[('8', "T", "U", "V")]+list("9*0#")
      r = None

      def corrector():
        nonlocal r
        r = k.correct_char_map(s)

      def feeder():
        s_index = 0
        for r_index in range(len(out_pins)):
          for c_index in range(len(in_pins)):
            k.__propagate_to_listeners__(s[s_index], r_index, c_index)
            s_index += 1

      corrector_thread = threading.Thread(target=corrector)
      corrector_thread.start()

      feeder_thread = threading.Thread(target=feeder)
      feeder_thread.start()

      feeder_thread.join()
      corrector_thread.join()

      self.assertEqual(r, correct_Map)



    
def main():
  unittest.main()

if __name__ == "__main__":
  main()