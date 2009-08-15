# -*- coding: utf-8 -*-
#
# File: portato/mq.pxd
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

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
