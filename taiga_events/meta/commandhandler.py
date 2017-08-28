from abc import ABCMeta, abstractmethod
from functools import wraps


def command(*args):
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


def require_authentication(func):
    @wraps(func)
    async def wrapped(*args, **kwargs):
        self = args[0]
        if not self.isAuthenticated():
            raise UnauthenticatedError()
        return await func(*args, **kwargs)
    return wrapped


def validate_spec(spec, value, name=None):
    def childName(parent, child):
        return child if not parent else "{}.{}".format(name, child)
    if not isinstance(value, dict):
        raise InvalidArgumentError(name)
    elif isinstance(spec, str):
        if spec not in value:
            raise MissingArgumentError(childName(name, spec))
    elif isinstance(spec, list):
        for subspec in spec:
            validate_spec(subspec, value, name)
    elif isinstance(spec, dict):
        for subname, subspec in spec.items():
            validate_spec(subname, value, name)
            validate_spec(
                subspec, value.get(subname), childName(name, subname)
            )
    else:
        raise InvalidSpecError(spec)


def validate_arguments(*spec):
    def wrapper(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            arguments = kwargs.get('arguments', {})
            validate_spec(list(spec), arguments)
            return await func(*args, **kwargs)
        return wrapped
    return wrapper




class SpecError(Exception):
    pass

class InvalidSpecError(SpecError):
    pass

class InvalidArgumentError(SpecError):
    pass

class MissingArgumentError(SpecError):
    pass

class InvalidCommandError(KeyError):
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

    async def handleCommand(self, command, arguments):
        for handler in self.handlers:
            if handler.handles_command == command:
                result = await handler(arguments=arguments)
                return result
        raise InvalidCommandError(command)

    @abstractmethod
    def isAuthenticated(self):
        pass
