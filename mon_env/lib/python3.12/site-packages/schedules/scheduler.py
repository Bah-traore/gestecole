import time
import threading
import re
from .Errors import Errors
from datetime import datetime
import inspect
import asyncio
class timer():
    def start(self, *, target, args=(), asynchronous=False, repeat=False):
        """
        Start a scheduled task
        """
        if not inspect.iscoroutinefunction(target) and asynchronous:
            raise Errors.AsyncError(f"\"{target.__name__}\" is not an asynchronous function!")
        elif inspect.iscoroutinefunction(target) and not asynchronous:
            raise Errors.AsyncError(f"\"{target.__name__}\" is an asynchronous function!")
        if not isinstance(args, tuple):
            raise TypeError("The args must be a tuple!")
        Seconds = sum([self.__dict__[Variable] * {"s": 1, "m": 60, "h": 3600, "d": 86400}[re.sub(f"_{self.__class__.__name__}__", "", Variable)[0]] for Variable in self.__dict__.keys()])
        threading.Thread(target=self.__task, args=(Seconds, target, args, repeat, asynchronous)).start()
    def __task(self, Sleep, Target, Args, Repeat, Asynchronous):
        time.sleep(Sleep)
        if Asynchronous:
            Loop = asyncio.new_event_loop()
            Loop.run_until_complete(Target(*Args))
        else:
            Target(*Args)
        if Repeat:
            threading.Thread(target=self.__task, args=(Sleep, Target, Args, Repeat, Asynchronous)).start()
    def second(self, Seconds : int):
        """
        Set the seconds
        """
        if not isinstance(Seconds, int):
            raise TypeError("the seconds must be an integer!")
        self.__seconds = Seconds
        return self
    def minute(self, Minutes):
        """
        Set the minutes
        """
        if not isinstance(Minutes, int):
            raise TypeError("the minutes must be an integer!")
        self.__minutes = Minutes
        return self
    def hour(self, Hours):
        """
        Set the hours
        """
        if not isinstance(Hours, int):
            raise TypeError("the hours must be an integer!")
        self.__hours = Hours
        return self
    def day(self, Days):
        """
        Set the days
        """
        if not isinstance(Days, int):
            raise TypeError("the days must be an integer!")
        self.__days = Days
        return self
class every():
    def start(self, *, target, args=(), asynchronous=False, repeat=False):
        if not inspect.iscoroutinefunction(target) and asynchronous:
            raise Errors.AsyncError(f"\"{target.__name__}\" is not an asynchronous function!")
        elif inspect.iscoroutinefunction(target) and not asynchronous:
            raise Errors.AsyncError(f"\"{target.__name__}\" is an asynchronous function!")
        if not isinstance(args, tuple):
            raise TypeError("The args must be a tuple!")
        self.__dict__ = {re.sub(f"_{self.__class__.__name__}__", "", Key) : Value for Key, Value in self.__dict__.items()}
        threading.Thread(target=self.__task, args=(target, args, self.__dict__, repeat, asynchronous)).start()
    def __task(self, Target, Args, Times, Repeat, Asynchronous):
        Now = datetime.now()
        Hours = Times["hours"] if "hours" in Times else 0
        if not "hours" in Times and (not "minutes" in Times or ("minutes" in Times and Times["minutes"] >= Now.minute)):
            Hours = Now.hour
        elif not "hours" in Times:
            Hours = Now.hour + 1
        Minutes = Times["minutes"] if "minutes" in Times else 0
        if not "minutes" in Times and (not "seconds" in Times or ("seconds" in Times and Times["seconds"] >= Now.second)):
            Minutes = Now.minute
        elif not "minutes" in Times:
            Minutes = Now.minute + 1 if "seconds" in Times else 0
        time.sleep((Now.replace(hour=Hours, minute=Minutes, second=Times["seconds"] if "seconds" in Times else 0) - datetime.now()).seconds)
        if Asynchronous:
            Loop = asyncio.new_event_loop()
            Loop.run_until_complete(Target(*Args))
        else:
            Target(*Args)
        if Repeat:
            time.sleep(sorted([{"s": 1, "m": 60, "h": 3600}[Key[0]] for Key in Times.keys()], reverse=True)[0])
            threading.Thread(target=self.__task, args=(Target, Args, Times, Repeat, Asynchronous)).start()
    def second(self, Seconds : int):
        """
        Set what second the target will run.

        The seconds must be between 0-60.
        """
        if not isinstance(Seconds, int):
            raise TypeError("the seconds must be an integer!")
        if Seconds < 0 or Seconds > 60:
            raise Errors.RangeError("The seconds range must be between 0-60!")
        self.__seconds = Seconds
        return self
    def minute(self, Minutes):
        """
        Set what minutes the target will run.

        The minutes must be a number between 0-60.
        """
        if not isinstance(Minutes, int):
            raise TypeError("the minutes must be an integer!")
        if Minutes < 0 or Minutes > 60:
            raise Errors.RangeError("The minutes range must be between 0-60!")
        self.__minutes = Minutes
        return self
    def hour(self, Hours):
        """
        Set what hour the target will run.

        The hours must be a number between 0-24.
        """
        if not isinstance(Hours, int):
            raise TypeError("the hours must be an integer!")
        if Hours < 0 or Hours > 24:
            raise Errors.RangeError("The hours range must be between 0-24!")
        self.__hours = Hours
        return self