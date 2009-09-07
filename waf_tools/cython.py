#!/usr/bin/env python
# encoding: utf-8

import TaskGen

TaskGen.declare_chain(
        name = 'cython',
        rule = '${CYTHON} -o ${TGT[0].bld_dir(env)} ${CYTHONFLAGS} ${SRC}',
        ext_in = '.pyx',
        ext_out = '.c'
)

def detect(conf):
        gob2 = conf.find_program('cython', var='CYTHON', mandatory=True)
        conf.env['CYTHONFLAGS'] = ''
