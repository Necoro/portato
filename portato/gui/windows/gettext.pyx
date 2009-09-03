cdef extern from "langinfo.h":
    char* nl_langinfo (int item)
    cdef enum:
        CODESET

cdef extern from "libintl.h":
    char * textdomain (char* domain)
    char * bindtextdomain (char* domain, char* dir)
    char * bind_textdomain_codeset (char* domain, char* codeset)

def set_gtk_gettext (char* domain, char* dir):
    textdomain(domain)
    bindtextdomain(domain, dir)

    old_charset = nl_langinfo(CODESET)
    bind_textdomain_codeset(domain, "UTF-8")

    return old_charset
