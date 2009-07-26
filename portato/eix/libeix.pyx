class EixError (Exception):
    message = "Unknown error."

    def __str__ (self):
        return self.message

class EndOfFileException (EixError):

    def __init__ (self, filename):
        self.message = "End of file reached though it was not expected: '%s'" % filename

class EixReaderClosed (EixError):
    message = "EixReader is already closed."

class UnsupportedVersionError (EixError):

    def __init__ (self, version):
        self.message = "Version '%s' is not supported." % version

cdef class EixReader (object):
    cdef object file
    cdef char closed
    
    cdef readonly object filename
    cdef readonly object version

    supported_versions = (28, )

    def __init__ (self, filename):
        self.filename = filename
        self.file = open(filename, "r")
        self.closed = 0
        
        self.version = self._get_number()

        if self.version not in self.supported_versions:
            raise UnsupportedVersionError(self.version)

    cdef unsigned long _get_number (self) except *:
        cdef unsigned char n
        cdef short count, i
        cdef unsigned long value
        cdef char* rest
        cdef object orest

        n = self._get_one_byte()

        if n < 0xFF:
            value = n
        else:
            count = 0

            while (n == 0xFF):
                count += 1
                n = self._get_one_byte()

            if n == 0:
                n = 0xFF # 0xFF is encoded as 0xFF 0x00
                count -= 1
            
            value = n << (count*8)

            if count > 0:
                orest = self.get_string(count)
                rest = orest # cast to char*

                for 0 <= i < count:
                    value += (<unsigned char>rest[i]) << ((count - i - 1)*8)

        return value

    cdef unsigned char _get_one_byte (self) except? 0:
        s = self.file.read(1)

        if len(s) != 1:
            raise EndOfFileException, self.filename
        
        return ord(s)

    cdef object _get_string (self, length):
        if self.closed:
            raise EixReaderClosed

        s = self.file.read(length)

        if len(s) != length:
            raise EndOfFileException, self.filename

        return s

    def get_number (self):
        if self.closed:
            raise EixReaderClosed
        
        return self._get_number()

    def close (self):
        if self.closed:
            raise EixReaderClosed
        
        self.file.close()
        self.closed = 1
