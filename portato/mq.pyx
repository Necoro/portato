from stdlib cimport *

cdef extern from "errno.h":
    int errno
    cdef enum:
        EACCES, EEXIST, ENOENT, ENOMEM, ENOSPC,
        EINVAL, EPERM, EIDRM, EINTR

cdef extern from *:
    int INT_MAX
    int RAND_MAX
    ctypedef size_t int
    int rand()

cdef extern from "string.h":
    char* strerror(int errno)
    void* memcpy (void* dst, void* src, size_t len)

cdef extern from "sys/msg.h" nogil:
    cdef enum:
        IPC_CREAT, IPC_EXCL, IPC_NOWAIT,
        IPC_RMID

    ctypedef int key_t

    struct msqid_ds:
        pass

    int msgget(key_t key, int msgflg)
    int msgctl(int msqid, int cmd, msqid_ds* buf)
    int msgsnd(int msgid, void* msgp, size_t msgsz, int msgflg)
    int msgrcv(int msgid, void* msgp, size_t msgsz, long msgtype, int msgflg)

cdef struct msg_data:
    long mtype
    char mtext[1]

cdef enum:
    MAX_MESSAGE_SIZE = 2048

class MessageQueueError(Exception):
    pass

class MessageQueueRemovedError (MessageQueueError):
    pass

cdef class MessageQueue (object):

    CREAT = IPC_CREAT
    EXCL = IPC_EXCL
    
    cdef int msgid
    cdef readonly key_t key

    def __init__ (self, key = None, int flags = 0):

        if (flags & IPC_EXCL) and not (flags & IPC_CREAT):
            raise MessageQueueError("EXCL must be combined with CREAT.")

        if key is None and not (flags & IPC_EXCL):
            raise MessageQueueError("The key can only be None if EXCL is set.")

        # make sure there is nothing ... obscure
        flags &= (IPC_CREAT | IPC_EXCL)

        flags |= 0600 # mode

        if key is None:
            check = True
            while check:
                self.key = self.random_key()
                self.msgid = msgget(self.key, flags)
                check = (self.msgid == -1 and errno == EEXIST)
        else:
            self.key = key
            self.msgid = msgget(key, flags)

        if self.msgid == -1:
            if errno == EACCES:
                raise MessageQueueError("Permission denied.")
            elif errno == EEXIST:
                raise MessageQueueError("Queue already exists.")
            elif errno == ENOENT:
                raise MessageQueueError("Queue does not exist and CREAT is not set.")
            elif errno == ENOMEM or errno == ENOSPC:
                raise MessageQueueError("Insufficient ressources.")
            else:
                raise OSError(errno, strerror(errno))

    def remove (self):
        cdef msqid_ds info
        cdef int ret

        ret = msgctl(self.msgid, IPC_RMID, &info)

        if ret == -1:
            if errno == EIDRM or errno == EINVAL:
                raise MessageQueueRemovedError("Queue already removed.")
            elif errno == EPERM:
                raise MessageQueueError("Permission denied.")
            else:
                raise OSError(errno, strerror(errno))

    def send (self, message, int type = 1):
        cdef msg_data * msg
        cdef int ret
        cdef long size = len(message)

        if type <= 0:
            raise ValueError("type must be > 0")

        if size >= MAX_MESSAGE_SIZE:
            raise ValueError("Message must be smaller than %d", MAX_MESSAGE_SIZE)

        msg = <msg_data*>malloc(sizeof(msg_data) + size)

        if msg is NULL:
            raise MemoryError("Out of memory")

        memcpy(msg.mtext, <char*>message, size)
        msg.mtype = type

        with nogil:
            ret = msgsnd(self.msgid, &msg, size, 0)

        try:
            if ret == -1:
                if errno == EIDRM or errno == EINVAL:
                    raise MessageQueueRemovedError("Queue was removed.")
                elif errno == EINTR:
                    raise MessageQueueError("Signaled while waiting.")
                elif errno == EACCES:
                    raise MessageQueueError("Permission denied.")
                else:
                    raise OSError(errno, strerror(errno))
        finally:
            free(msg)

    def receive (self):
        cdef msg_data * msg
        cdef int ret
        cdef object retTuple

        msg = <msg_data*>malloc(sizeof(msg_data) + MAX_MESSAGE_SIZE)

        if msg is NULL:
            raise MemoryError("Out of memory")

        msg.mtype = 0

        with nogil:
            ret = msgrcv(self.msgid, msg, <size_t>MAX_MESSAGE_SIZE, 0, 0)
        
        try:
            if ret == -1:
                if errno == EIDRM or errno == EINVAL:
                    raise MessageQueueRemovedError("Queue was removed.")
                elif errno == EINTR:
                    raise MessageQueueError("Signaled while waiting.")
                elif errno == EACCES:
                    raise MessageQueueError("Permission denied.")
                else:
                    raise OSError(errno, strerror(errno))

            retTuple = (msg.mtext, msg.mtype)
        finally:
            free(msg)

        return retTuple

    cdef key_t random_key (self):
        return <int>(<double>rand() / (<double>RAND_MAX + 1) * INT_MAX)
