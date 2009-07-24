cdef extern from *:
    ctypedef int size_t

cdef extern from "errno.h":
    int errno

cdef extern from "string.h":
    char* strerror (int errno)
    size_t strlen (char* s)
    char* strcpy (char* dest, char* src)

cdef extern from "stdio.h":

    ctypedef struct FILE:
        pass

    FILE* c_fopen "fopen" (char* path, char* mode)
    int c_fclose "fclose" (FILE* f)
    int c_feof "feof" (FILE* f)
    int fread (void* buf, size_t size, size_t n, FILE* f)

    enum WHENCE:
        SEEK_SET
        SEEK_CUR
        SEEK_END
    
    int fseek (FILE* stream, long offset, WHENCE whence)

cdef extern from "Python.h":
    ctypedef struct PyObject:
        pass

    void* PyMem_Malloc (size_t n)
    void PyMem_Free (void* p)

cdef:
    struct File:
        FILE* file
        char* name

    File* fopen (char* path, char* mode) except NULL
    void fclose (File* f)

    void ffree (void* p)
    char* fget (File* f, size_t n) except NULL

    char* strdup (char* other) except NULL
