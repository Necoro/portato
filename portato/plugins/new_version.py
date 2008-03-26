try:
	from bzrlib import plugin, branch
except ImportError:
	plugin = branch =  None

from threading import Thread

import gobject

from portato.helper import debug, warning
from portato import get_listener
from portato.constants import VERSION, APP_ICON, APP

def find_thread (rev):
	try:
		b = branch.Branch.open("lp:portato")
	except Exception, e:
		warning("NEW_VERSION :: Exception occured while accessing the remote branch: %s", str(e))
		return

	debug("NEW_VERSION :: Installed rev: %s - Current rev: %s", rev, b.revno())
	if int(rev) < int(b.revno()):
		def callback():
			get_listener().send_notify(base = "New Portato Live Version Found", descr = "You have rev. %s, but the most recent revision is %s." % (rev, b.revno()), icon = APP_ICON)
			return False
		
		gobject.idle_add(callback)

def find_version (*args, **kwargs):
	if not all((plugin, branch)):
		return

	v = VERSION.split()
	if len(v) != 3 or v[0] != "9999":
		return

	rev = v[-1]

	plugin.load_plugins() # to have lp: addresses parsed
	t = Thread(target = find_thread, args=(rev,))
	t.setDaemon(True)
	t.start()
