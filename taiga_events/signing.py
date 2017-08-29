import base64
import hashlib
import hmac

from .meta import Singleton


class TokenInvalidError(ValueError):
    pass


class SigningConfig(metaclass=Singleton):
    def __init__(self):
        self.salt = None
        self.secret = None

    def setSalt(self, salt):
        self.salt = salt

    def setSecret(self, secret):
        self.secret = secret


def setConfig(salt, secret):
    config = SigningConfig()
    config.setSalt(salt)
    config.setSecret(secret)


def generateSignature(value):
    config = SigningConfig()
    key = "{}signer{}".format(config.salt, config.secret)
    shaKey = hashlib.sha1(bytes(key, 'UTF-8')).digest()
    hmacKey = hmac.new(
        shaKey, msg=value, digestmod=hashlib.sha1
    ).digest()
    return base64.urlsafe_b64encode(hmacKey).replace(b'=',b'')


def verifyToken(token):
    try:
        split = token.split(":")
        value = bytes(":".join(split[0:-1]), 'UTF-8')
        sig = bytes(split[-1], 'UTF-8')
        if sig == generateSignature(value):
            return
    except:
        pass
    raise TokenInvalidError()
