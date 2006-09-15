/*
 * This is a python module implementing real threads.
 */
#include <Python.h>
#include <pthread.h>

/**
 * Callback for the thread. Just calls the argument's python function.
 */
static void * thread_cb (void * arg)
{
	PyObject * arglist;

	arglist = Py_BuildValue("()",NULL);
	PyEval_CallObject((PyObject*)arg, arglist);
    Py_DECREF(arglist);
	Py_DECREF((PyObject*)arg);

	return NULL;
}

/**
 * Function called from the python application.
 */
static PyObject * thread_start (PyObject * self, PyObject *args)
{
	PyObject *temp;
	pthread_t ID;

    if (PyArg_ParseTuple(args, "O:thread_start", &temp))  // get argument
	{
        if (!PyCallable_Check(temp)) // not callable
		{
            PyErr_SetString(PyExc_TypeError, "parameter must be callable");
            return NULL;
        }
        Py_INCREF(temp);         /* Add a reference to new callback */
		int status = pthread_create(&ID, NULL, thread_cb, (void*) temp);
		if (status)
		{
			PyErr_SetString(PyExc_SystemError, "error during thread start");
			return NULL;
		}
    }
	
	Py_RETURN_NONE;
}

static PyMethodDef ThreadMethods[] = {
    {"thread_start",  thread_start, METH_VARARGS,
     "Start a new thread."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

/**
 * Init function.
 */
PyMODINIT_FUNC
initgeneticthread(void)
{
    (void) Py_InitModule("geneticthread", ThreadMethods);
}
