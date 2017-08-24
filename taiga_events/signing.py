import base64
import hashlib
import hmac


class Signer(object):
    def __init__(self, salt, secret):
        self.salt = salt
        self.secret = secret

    def generateSignature(self, value):
        key = "{}signer{}".format(self.salt, self.secret)
        shaKey = hashlib.sha1(bytes(key, 'UTF-8')).digest()
        hmacKey = hmac.new(
            shaKey, msg=value, digestmod=hashlib.sha1
        ).digest()
        return base64.urlsafe_b64encode(hmacKey).replace(b'=',b'')

    def verifyToken(self, token):
        split = token.split(":")
        value = bytes(":".join(split[0:-1]), 'UTF-8')
        sig = bytes(split[-1], 'UTF-8')
        return sig == self.generateSignature(value)
