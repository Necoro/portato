try:
	from bzrlib import plugin, branch
except ImportError:
	plugin = branch =  None
import gobject

from portato.helper import debug, warning
from portato import get_listener
from portato.constants import VERSION, APP_ICON, APP
from portato.gui.utils import GtkThread

def find_version (rev):
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

def start_thread(rev):
	t = GtkThread(target = find_version, name = "Version Updater Thread", args = (rev,))
	t.setDaemon(True)
	t.start()
	return True

def run_menu (*args, **kwargs):
	"""
	Run the thread once.
	"""
	if not all((plugin, branch)):
		return None

	v = VERSION.split()
	if len(v) != 3 or v[0] != "9999":
		return None

	rev = v[-1]

	plugin.load_plugins() # to have lp: addresses parsed
	
	start_thread(rev)
	return rev

def run (*args, **kwargs):
	"""
	Run the thread once and add a 30 minutes timer.
	"""
	rev = run_menu()

	if rev is not None:
		gobject.timeout_add(30*60*1000, start_thread, rev) # call it every 30 minutes
