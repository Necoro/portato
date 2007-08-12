from gettext import lgettext as _
import pynotify

from portato import listener

from portato.helper import warning, error, debug
from portato.constants import APP_ICON, APP

def notify (retcode, **kwargs):
	if retcode is None:
		warning(_("Notify called while process is still running!"))
	else:
		icon = APP_ICON
		if retcode == 0:
			text = "Emerge finished!"
			descr = ""
			urgency = pynotify.URGENCY_NORMAL
		else:
			text = "Emerge failed!"
			descr = "Error Code: %d" % retcode
			urgency = pynotify.URGENCY_CRITICAL

		listener.send_notify(base = text, descr = descr, icon = icon, urgency = urgency)
