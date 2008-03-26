try:
	from bzrlib import plugin, branch
except ImportError:
	plugin = branch =  None

from threading import Thread

from portato.helper import debug, _
from portato import get_listener
from portato.constants import VERSION, APP_ICON, APP

def find_thread (rev):
	b = branch.Branch.open("lp:portato")

	if int(rev) < int(b.revno()):
		get_listener().send_notify(base = "New Portato Live Version Found", descr = "You have rev. %s, but the most recent revision is %s." % (rev, b.revno()), icon = APP_ICON)

def find_version (*args, **kwargs):
	if not all((plugin, branch)):
		return

	v = VERSION.split()
	if len(v) != 3 and v[0] != "9999":
		return

	rev = v[-1]

	plugin.load_plugins() # to have lp: addresses parsed
	Thread(target = find_thread, args=(rev,)).start()
