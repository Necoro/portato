#!/usr/bin/env python
# encoding: utf-8

import TaskGen

TaskGen.declare_chain(
        name = 'cython',
        rule = '${CYTHON} -o ${TGT} ${CYTHONFLAGS} ${SRC}',
        ext_in = '.pyx',
        ext_out = '.c'
)

def detect(conf):
        conf.find_program('cython', var='CYTHON', mandatory=True)
        conf.env['CYTHONFLAGS'] = ''
