try:
	from dbus.mainloop.glib import threads_init
except ImportError:
	threads_init = None

from portato.constants import USE_CATAPULT

def dbus_init (*args):
	if USE_CATAPULT and threads_init is not None:
		threads_init()
