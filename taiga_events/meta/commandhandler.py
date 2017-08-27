from abc import ABCMeta, abstractmethod


def handles_command(command):
    def decorate(func):
        func.handles_command = command
        return func
    return decorate


def requires_authentication(func):
    async def decorate(*args):
        self = args[0]
        if not self.isAuthenticated():
            raise UnauthenticatedError()
        return await func(*args)
            
    return decorate


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
