from dbus.mainloop.glib import threads_init

def dbus_init (*args):
	threads_init()
