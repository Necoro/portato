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
