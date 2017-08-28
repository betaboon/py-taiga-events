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
    async def wrapped(*args):
        self = args[0]
        if not self.isAuthenticated():
            raise UnauthenticatedError()
        return await func(*args)
    return wrapped


def requires_arguments(*paths):
    def wrapper(func):
        @wraps(func)
        async def wrapped(*args):
            for path in paths:
                try:
                    val = dictGetByKeyPath(args[1], path)
                except KeyError:
                    raise MissingArgumentsError()
            return await func(*args)
        return wrapped
    return wrapper


def dictGetByKeyPath(dict, keyPath):
    keyPath = keyPath if isinstance(keyPath, list) else [keyPath]
    val = None
    for key in keyPath:
        val = val[key] if val else dict[key]
    return val


class UnknownCommandError(KeyError):
    pass


class UnauthenticatedError(Exception):
    pass


class MissingArgumentsError(Exception):
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
