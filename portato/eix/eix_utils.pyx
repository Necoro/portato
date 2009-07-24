class EndOfFileError (IOError):
    
    def __init__ (self, filename = None):
        self.message = "End of file reached while not expecting it"
        self.filename = filename

    def __str__ (self):
        if self.filename is not None:
            return "%s: %s" % (self.message, self.filename)
        else:
            return self.message

cdef char* strdup (char * other) except NULL:
    cdef size_t len
    cdef char* new

    if other is NULL:
        return NULL

    len = strlen(other)
    new = <char*>PyMem_Malloc(len+1)

    if new is NULL:
        raise MemoryError, "Malloc of new string copy"
        return NULL

    return strcpy(new, other)


cdef File* fopen (char* path, char* mode) except NULL:
    cdef File* f
    
    f = <File*> PyMem_Malloc(sizeof(File))
    
    if f is NULL:
        raise MemoryError, "Malloc of File"
        return NULL

    f.file = c_fopen(path, mode)

    if f.file is NULL:
        raise IOError, (errno, strerror(errno), path)
        return NULL

    f.name = strdup(path)

    if f.name is NULL:
        return NULL

    return f

cdef void fclose (File* f):
    c_fclose(f.file)
    ffree(f.name)
    PyMem_Free(f)

cdef void ffree (void* p):
    PyMem_Free(p)

cdef char* fget (File* f, size_t n) except NULL:
    cdef char* buf
    buf = <char*> PyMem_Malloc(n)

    if buf is NULL:
        raise MemoryError, "Malloc"
        return NULL

    if (fread(buf, 1, n, f.file) != n):
        PyMem_Free(buf)
        raise EndOfFileError, f.name

    return buf
