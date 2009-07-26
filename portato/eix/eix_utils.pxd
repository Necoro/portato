cdef extern from *:
    ctypedef int size_t

cdef extern from "errno.h":
    int errno

cdef extern from "string.h":
    char* strerror (int errno)
    size_t strlen (char* s)
    char* strcpy (char* dest, char* src)

cdef extern from "Python.h":
    void* PyMem_Malloc (size_t n)
    void PyMem_Free (void* p)

cdef:
    char* strdup (char* other) except NULL
