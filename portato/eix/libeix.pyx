from portato.eix.eix_utils cimport File, fopen, fclose, ffree, fget

def test (f):
    cdef File* cf
    cdef char* buf

    print "Trying to open: ", f
    cf = fopen(f, "r")
    try:
        buf = fget(cf, 20)
        print "The first two chars:", buf[0], buf[1]
        ffree(buf)
    finally:
        fclose(cf)
