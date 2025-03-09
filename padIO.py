import RPi.GPIO as GPIO
import time
import signal
from typing import Callable
from threading import Thread, Event, Self, Sequence

class Keypad:
  in_pins: list[int]
  out_pins: list[int]
  char_matrix: list[list[tuple[str]]]
  poll_thread: Thread
  poll_sleeper: Event
  key_delay: int
  secondary_max_gap: int
  __listeners__: list[Callable[[str], any]]

  """
  tuple[list[str], int, int]
  -> tuple[str] - list of key choices (first is primary, the others are secondary)
  -> int - nanoseconds the key was captured
  -> int - index on list[str] that was the capture key
  """
  __key_map__: list[list[tuple[tuple[str], int, int]]]

  __is_closed__: bool
  
  def __init__(
    self, 
    ins: list[int], 
    outs: list[int], 
    char_matrix: list[list[str | tuple[str]]], 
    poll: bool = False,
    key_delay: int = 100,
    secondary_max_gap: int = 200,
    stop_immediate: bool = True,
    initial_listeners: list[Callable[[str, int, int], any]] = []):
    """
    Creates a Keypad

    Parameters:
    ins (list[int]) - list of GPIO pin numbers to be considered as the input pins
    outs (list[int]) - list of GPIO pin numbers to be considered as the output pins
    char_matrix (list[list[str | tuple[str, list[str], float]]]) - a len(outs) by len(ins) matrix determining the 
                                                                   characters per output-input pin press
    poll (bool) - whether to determine key presses via continual polling of keypad, or interupts. (default: True)
    key_delay (int) - the amount of miliseconds to wait before re-scanning the keypad for key presses (default: 0.1 seconds)
    secondary_max_gap (int) - the max amount of miliseconds to wait between pressing the same key to cycle to the
                                          next secondary character choice (default: 0.075)
    stop_immediate (bool) - whether to return the most immediate pressed character (default: True)
    initial_listeners (list[Callable[[str, int, int], any]]) - initial list of callback/listener functions (default: [])

    Note: "ins" and "outs" pin numbering follows whatever RPi.GPIO.setmode() is set. It's not loyal to any pin numbering.

    Raises a ValueError if char_matrix isn't of the dimension: len(outs) by len(ins)
    """

    if len(char_matrix) != len(outs):
      raise ValueError("Number of rows in char_map must match size of ins")
    if any([x for x in char_matrix if len(x) != len(ins)]):
      raise ValueError("Number of columns in char_map must match size of outs")

    self.in_pins = ins
    self.out_pins = outs
    self.char_matrix = [[(x) if isinstance(x, str) else x for x in h] for h in char_matrix]

    if poll:
      self.poll_thread = Thread(target=self.__poll_target_func__) if poll else None
      self.poll_sleeper = Event()

    self.key_delay = key_delay * 1000000
    self.secondary_max_gap = secondary_max_gap * 1000000
    self.stop_immediate = stop_immediate
    self.__listeners__ = list(initial_listeners)

    self.__is_closed__ = False
    self.__key_map__ = [[( (x) if isinstance(x, str) else x, -1, 0) for x in h] for h in self.char_matrix]
      
    
    GPIO.setup(self.out_pins, GPIO.OUT, initial=GPIO.LOW)

    if not poll:
      for in_pin in self.in_pins:
        GPIO.setup(in_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(in_pin, GPIO.FALLING, callback=self.__key_press_callback__, bouncetime=key_delay)
    else:
      GPIO.setup(self.in_pins, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    print("ins: ", ins)
    print("outs: ", outs)

  def add_listener(self, listener: Callable[[str, int, int], any]):
    """
    Adds a listener (callback) function to invoke when a keypress is detected

    Parameters:
    listener: Callable[[str, int, int] - the listener/callback function to add

    Raises a ValueError if this keypad has been closed
    """

    if self.__is_closed__:
      raise ValueError("Keypad is closed")
    self.__listeners__.append(listener)

  def remove_listener(self, listener: Callable[[str, int, int], any]):
    """
    Removes a listener (callback) function

    Parameters:
    listener: Callable[[str, int, int] - the listener/callback function to remove (must be the same instance as the one added)

    Raises a ValueError if this keypad has been closed
    """

    if self.__is_closed__:
      raise ValueError("Keypad is closed")
    self.__listeners__.remove(listener)

  def __poll_target_func__(self):
    print(" ==> polling function started!")

    poll_delay = self.key_delay / 1000000000

    while not self.__is_closed__:
      result: tuple[int, int, str] = None
      for out_c_index, out_pin in enumerate(self.out_pins):
        GPIO.output(out_pin, GPIO.HIGH)

        for in_c_index, in_pin in enumerate(self.in_pins):
          #print(" => checking: ", f"{out_pin},{in_pin} | {poll_delay}")
          if GPIO.input(in_pin) == GPIO.HIGH:
            #print(" ===> poll: input detected: ", f"{out_pin},{in_pin}")
            current_time = time.time_ns()
            result = self.__determine_key__(in_c_index, out_c_index, current_time)

            if self.stop_immediate:
              #print(" ===> propagating ", result)
              self.__propagate_to_listeners__(result[2], result[0], result[1])
              break
        GPIO.output(out_pin, GPIO.LOW)

      self.poll_sleeper.wait(poll_delay)

    print(" ==> polling function done!")

  def __key_press_callback__(self, in_pin: int):
    if self.__is_closed__:
      return

    #print("===> input detected at ", in_pin)

    if not GPIO.input(in_pin):
      in_c_index = self.in_pins.index(in_pin)

      result = None
      for out_c_index, out_pin in enumerate(self.out_pins):
        GPIO.output(out_pin, GPIO.HIGH)
        if GPIO.input(in_pin) == GPIO.HIGH:
          current_time = time.time_ns()
          result = self.__determine_key__(in_c_index, out_c_index, current_time)
        GPIO.output(out_pin, GPIO.LOW)

        if result and self.stop_immediate:
          #print(" ! stopped!")
          break
      
      if result:
        self.__propagate_to_listeners__(result[2], result[0], result[1])

  def __determine_key__(self, in_c_index: int, out_c_index: int, capture_time: int) -> tuple[int, int, str]:
    result: tuple[int, int, str] = None
    #print("=>",self.char_matrix[out_c_index][in_c_index], " | ", result)

    latest_key_detail = self.__key_map__[out_c_index][in_c_index]
    current_key_detail = (latest_key_detail[0], capture_time, (latest_key_detail[2] + 1) % len(latest_key_detail[0]))
    difference = capture_time - latest_key_detail[1]

    if latest_key_detail[1] >= 0:
      #print(" ==> key was pressed before ", difference, "|", self.second_choice_delay, difference < self.second_choice_delay)
      if difference > self.secondary_max_gap:
        #print(" => outside window. Resetting")
        current_key_detail = (current_key_detail[0], current_key_detail[1], 0)
      #print(" ==> cur: ", current_key_detail)
      result = (out_c_index, in_c_index, current_key_detail[0][current_key_detail[2]])
    else:
      current_key_detail = (current_key_detail[0], current_key_detail[1], 0)
      result = (out_c_index, in_c_index, latest_key_detail[0][0])

    """
    print(" ==> ", \
      self.char_matrix[out_c_index][in_c_index], \
      " | diff: ", f"{capture_time} - {latest_key_detail[1]} = {difference} \n", \
      " | window: ", f"{self.secondary_max_gap} => in window? {difference <= (self.secondary_max_gap)} \n", \
      " | KEY window: ", f"{self.key_delay} => in KEY window? {difference <= (self.key_delay)} | {difference - (self.key_delay)} \n", \
      " | result: ", result, "\n")
    """

    if isinstance(result[2], str) == False:
      print("error!!! ", current_key_detail)

    self.__key_map__[out_c_index][in_c_index] = current_key_detail
    return result
    
  def __propagate_to_listeners__(self, character: str, out_pin: int, in_pin: int):
    for listener in self.__listeners__:
      listener(character, out_pin, in_pin)

  def correct_char_map(self, input_seq: list[str | tuple[str]]) -> list[list[str | tuple[str]]]:
    """
    Corrects the char_matrix of this keypad by tracking keypad presses against a sequence of 
    expected inputs.

    Note: This method corrects the primary character per key and will preserve existing secondary choices
          and their time window. If you're looking to also change secondary choices, consider directly changing
          char_matrix

    Parameters:
    input_seq list[str | tuple[str]]) - sequence of characters to match unique keypad presses against

    Returns:
    (int, int, str) - The first two ints indicate the index of the 
                      output and input pin in out_pins and in_pins repectively.
                      The str is the pressed character, as dictated by char_matrix

    Raises a ValueError keypad has been closed, or len(input_seq) != the sum of all primary choices in char_matrix
    """
    if self.__is_closed__:
      raise ValueError("keypad has been closed")

    if len(input_seq) != sum([len(x) for x in self.char_matrix]):
      raise ValueError("Character input sequence must be equal to all characters in char_matrix")
    
    corrected_mat: list[list[str | tuple[str]]] = [[None for _ in j] for j in self.char_matrix]
    corrected_chars = 0

    finished_input = Event()

    def key_listener(character: str, out_index: int, in_index: int):
      nonlocal corrected_mat, corrected_chars
      if not corrected_mat[out_index][in_index]:
        correct_char = input_seq[corrected_chars]
        oldValue = self.char_matrix[out_index][in_index]

        if isinstance(oldValue, tuple):
          self.char_matrix[out_index][in_index] = (correct_char, *oldValue[-(len(oldValue) - 1)::])
          corrected_mat[out_index][in_index] = (correct_char, *oldValue[-(len(oldValue) - 1)::])
        else:
          self.char_matrix[out_index][in_index] = correct_char
          corrected_mat[out_index][in_index] = correct_char

        #print(f" ==> old char at ({out_index}, {in_index}) => {character} IS NOW {self.char_matrix[out_index][in_index]} | {corrected_chars} | {len(input_seq)} | {type(oldValue)}")
        corrected_chars += 1

      if corrected_chars == len(input_seq):
        finished_input.set()

    self.add_listener(key_listener)
    finished_input.wait()
    self.remove_listener(key_listener)

    # Re-do self.__key_map__ so character pin pointing in callback is correct
    self.__key_map__ = [[( (x) if isinstance(x, str) else x, -1, 0) for x in h] for h in self.char_matrix]

    #print(" => done ", self.char_matrix, "\n", corrected_mat)

    return corrected_mat

  def __enter__(self):
    return self.start()
  
  def __exit__(self, exc_type, exc_val, exc_tb):
    self.close()

  def start(self) -> Self:
    if self.__is_closed__:
      raise ValueError("keypad object has been closed")

    if hasattr(self, "poll_thread"):
      self.poll_thread.start()
    return self

  def close(self):
    if not self.__is_closed__:
      self.__is_closed__ = True

      if hasattr(self, "poll_thread"):
        self.poll_sleeper.set()
        self.poll_thread.join()
      else:
        for in_pin in self.in_pins:
          GPIO.remove_event_detect(in_pin)
      
      GPIO.cleanup(self.in_pins + self.out_pins)

try:
  GPIO.setwarnings(False)
  GPIO.setmode(GPIO.BCM)

  cMap_old = [
    ["1","2","3"],
    ["4","5","6"],
    ["7","8","9"],
    ["*","0","#"]
  ]
  

  def key_l(c: str, out: int, inp: int):
    print(" ==> received: ", c, f" ({out}, {inp})")

  cMap = [
    ['*', '0', '#'], 
    ['7', ('8', "T", "U", "V"), '9'], 
    ['4', '5', '6'], 
    ['1', '2', '3']]
  with Keypad([26,19,13], [17,27,22,10], cMap, initial_listeners=[], poll=False) as k:
    #print(k.correct_char_map("123456789*0#"))
    #print("==> done!!!")
    k.add_listener(key_l)
    signal.pause()
except KeyboardInterrupt:
  print("\nApplication stopped!")