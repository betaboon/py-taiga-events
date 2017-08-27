from abc import ABCMeta, abstractmethod
from functools import wraps


def handles_command(*args):
    func = None
    func_name = None
    if len(args) == 1 and callable(args[0]):
        # @handles_command
        func = args[0]
        func_name = func.__name__
    elif len(args) == 1 and isinstance(args[0], str):
        # @handles_command('name')
        func_name = args[0]
    def decorate(func):
        func.handles_command = func_name
        return func
    return decorate(func) if func else decorate


def requires_authentication(func):
    @wraps(func)
    async def wrap(*args):
        self = args[0]
        if not self.isAuthenticated():
            raise UnauthenticatedError()
        return await func(*args)
    return wrap


class UnknownCommandError(KeyError):
    pass


class UnauthenticatedError(Exception):
    pass


class CommandHandlerMeta(metaclass=ABCMeta):
    @property
    def handlers(self):
        for attr in dir(self):
            obj = getattr(self, attr)
            if callable(obj) and hasattr(obj, "handles_command"):
                yield obj

    async def handleCommand(self, command, data):
        for handler in self.handlers:
            if handler.handles_command == command:
                result = await handler(data)
                return result
        raise UnknownCommandError()

    @abstractmethod
    def isAuthenticated(self):
        pass