# -*- coding: utf-8 -*-
#
# File: portato/gui/qt/terminal.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from PyQt4 import Qt

from Queue import Queue
from threading import Thread
from os import read

try:
	from curses.ascii import ctrl
except ImportError: # emulate ctrl-behavior for known values
	def ctrl (val):
		if val == "H": return '\x08'
		elif val == "W": return '\x17'
		else: debug("unknown error passed to emulated ctrl:",val)

from portato.gui.wrapper import Console
from portato.helper import debug

class WriteEvent (Qt.QEvent):
	TYPE = Qt.QEvent.Type(1001)

	def __init__ (self, string):
		Qt.QEvent.__init__(self, self.TYPE)
		self.string = string

	def get_string(self):
		return self.string

class DeleteEvent (Qt.QEvent):
	TYPE = Qt.QEvent.Type(1002)
	(DEL_CHAR, DEL_WORD, DEL_LINE, DEL_LINE_REVERT) = range(4)

	def __init__ (self, type = DEL_CHAR):
		Qt.QEvent.__init__(self, self.TYPE)
		self.del_type = type

class BoldFormat (Qt.QTextCharFormat):

	def __init__(self):
		Qt.QTextCharFormat.__init__(self)
		self.setFontWeight(Qt.QFont.Bold)

class UnderlineFormat (Qt.QTextCharFormat):

	def __init__(self):
		Qt.QTextCharFormat.__init__(self)
		self.setFontUnderline(True)

class ColorFormat (Qt.QTextCharFormat):

	def __init__(self, color):
		Qt.QTextCharFormat.__init__(self)

		self.setForeground(Qt.QBrush(Qt.QColor(color)))

# we only support a subset of the commands
esc_seq = ("\x1b", "[")
reset_seq = "39;49;00"
seq_end = "m"
seq_sep = ";"
backspace = ctrl("H")
backword = ctrl("W")
cr = "\r"

title_seq = ("\x1b", "]")
title_end = "\x07"

# the attributes
attr = {}
attr[0]			=  	None 				# normal
attr[1]			=  	BoldFormat()	 	# bold
attr[4]    		=  	UnderlineFormat()	# underline
attr[30]        =  	ColorFormat("white") # should be black - but is inverted
attr[31]        =	ColorFormat("red")
attr[32]        = 	ColorFormat("lime") # lime looks better on black than normal green
attr[33]       	= 	ColorFormat("yellow")
attr[34]        = 	ColorFormat("blue")
attr[35]      	= 	ColorFormat("magenta")
attr[36]        = 	ColorFormat("cyan")
attr[37]        = 	ColorFormat("white")
attr[39]      	= 	None				# default - use white too

class QtConsole (Console, Qt.QTextEdit):
	"""Self implemented emulation of a terminal emulation.
	This only supports a subset of instructions known to normal terminals."""

	def __init__ (self, parent):
		"""Constructor.
		
		@param parent: parent widget
		@type parent: Qt.QWidget"""

		Qt.QTextEdit.__init__(self, parent)

		self.pty = None
		self.running = False
		self.formatQueue = Queue()
		self.title = None
		self.writeQueue = ""
		self.isOk = False

		self.setCurrentFont(Qt.QFont("Monospace",11))

		# set black bg
		self.palette().setColor(Qt.QPalette.Base, Qt.QColor("black"))
		self.setBackgroundRole(Qt.QPalette.Base)
		self.setAutoFillBackground(True)
				
		# set standard char format to "white"
		self.stdFormat = self.currentCharFormat()
		self.stdFormat.merge(ColorFormat("white"))
		self.setCurrentCharFormat(self.stdFormat)

		self.setReadOnly(True)

	def _deletePrev (self, type):
		"""Deletes the previous character/word."""
		if type == DeleteEvent.DEL_CHAR: # just the prev char
			self.textCursor().deletePreviousChar()
		
		elif type == DeleteEvent.DEL_WORD:
			self.textCursor().select(Qt.QTextCursor.WordUnderCursor)
			self.textCursor().removeSelectedText()
		
		elif type == DeleteEvent.DEL_LINE:
			self.moveCursor(Qt.QTextCursor.StartOfLine, Qt.QTextCursor.KeepAnchor)
			self.textCursor().removeSelectedText()
			self.setLineWrapMode(Qt.QTextEdit.NoWrap)
			self.isOk = True
		
		elif type == DeleteEvent.DEL_LINE_REVERT:
			self.setLineWrapMode(Qt.QTextEdit.WidgetWidth)
			self.isOk = False
	
	def event (self, event):
		if event.type() == WriteEvent.TYPE:
			self._write(event.get_string())
			event.accept()
			return True

		elif event.type() == DeleteEvent.TYPE:
			self._deletePrev(event.del_type)
			event.accept()
			return True
		
		event.ignore()
		return False

	def _write (self, text):
		"""Writes some text. A text of "\\x1b" signals _write() to reload
		the current char format.
		
		@param text: the text to print
		@type text: string"""

		if text == esc_seq[0]: # \x1b -> reload format
			self.setCurrentCharFormat(self.get_format())
		else:
			if not self.textCursor().atEnd() and not self.isOk: # move cursor and re-set format
				f = self.currentCharFormat()
				self.moveCursor(Qt.QTextCursor.End)
				self.setCurrentCharFormat(f)
			
			# insert the text
			self.insertPlainText(text)
			
			# scroll down if needed
			if not self.isOk: self.ensureCursorVisible()

	def write(self, text):
		"""Convenience function for emitting the writing signal."""
		
		def send (text):
			Qt.QCoreApplication.postEvent(self, WriteEvent(text))
		
		if text is None:
			send(self.writeQueue)
			self.writeQueue = ""

		elif text == esc_seq[0]:
			send(self.writeQueue)
			send(text)
			self.writeQueue = ""
		
		elif len(self.writeQueue) == 4:
			send(self.writeQueue+text)
			self.writeQueue = ""
		
		else:
			self.writeQueue = self.writeQueue + text

	def start_new_thread (self):
		"""Starts a new thread, which will listen for some input.
		@see: QtTerminal.__run()"""
		self.run = True
		self.current = Thread(target=self.__run, name="QtTerminal Listener")
		self.current.setDaemon(True) # close application even if this thread is running
		self.current.start()

	def set_pty (self, pty):
		if not self.running:
			self.pty = pty
			self.start_new_thread()
			self.running = True
		
		else: # quit current thread
			self.run = False
			self.clear()

			self.pty = pty # set this after clearing to lose no chars :)
			self.start_new_thread()

	def __run (self):
		"""This function is mainly a loop, which looks for some new input at the terminal,
		and parses it for text attributes."""

		got_cr = False
		
		while self.run:
			s = read(self.pty, 1)
			if s == "": break # nothing read -> finish

			if self.isOk and s == "\n":
				self.write(None)
				Qt.QCoreApplication.postEvent(self, DeleteEvent(DeleteEvent.DEL_LINE_REVERT))

			if got_cr:
				got_cr = False
				if s == "\n": # got \r\n, which is ok
					self.write(s)
					continue
				else:
					self.write(None)
					Qt.QCoreApplication.postEvent(self, DeleteEvent(DeleteEvent.DEL_LINE))

			if s == backspace: # BS
				self.write(None)
				Qt.QCoreApplication.postEvent(self, DeleteEvent())
			
			elif s == backword:
				self.write(None)
				Qt.QCoreApplication.postEvent(self, DeleteEvent(DeleteEvent.DEL_WORD))

			elif s == cr: # CR -> make the line being deleted
				got_cr = True

			elif s == esc_seq[0]: # -> 0x27
				s = read(self.pty, 1)
				if s == esc_seq[1]: # -> [
					while True:
						_s = read(self.pty, 1)
						s += _s
						if _s == seq_end: break
					self.parse_seq(s[1:-1])

				elif s == title_seq[1]: # -> ]
					while True:
						_s = read(self.pty, 1)
						s += _s
						if _s == title_end: break
					
					self.parse_title(s[1:-1])
				else:
					self.write(esc_seq[0]+s)
			
			elif not got_cr:
				self.write(s)
			
		self.write(None)

	def parse_seq (self, seq):
		"""Parses a sequence of bytes.
		If a new attribute has been encountered, a new format is created and added
		to the internal format queue.
		
		@param seq: sequence to parse
		@type seq: string"""
		
		global attr # the dict of attributes

		format = self.virgin_format() 

		if seq != reset_seq: # resettet -> done
			seq = seq.split(seq_sep)
			for s in seq:
				try:
					s = int(s)
				except ValueError:
					format = self.virgin_format()
					break

				try:
					if attr[s] is not None:
						format.merge(attr[s])
					else:
						format = self.virgin_format()
						break
				except KeyError: # no such attribute
					format = self.virgin_format()
					break

		self.add_format(format)
		self.write(esc_seq[0]) # write \x1b to signal the occurence of a new format

	def parse_title (self, seq):
		if not seq.startswith("0;"):
			return

		self.title = seq[2:]

	def get_window_title (self):
		return self.title

	def add_format (self, format):
		"""Adds a format to the queue.
		We have to take a queue, because the write-signals might occur asynchronus,
		so we set a format for the wrong characters.
		
		@param format: the format to add
		@type format: Qt.QTextCharFormat"""

		self.formatQueue.put(format)

	def get_format (self):
		"""Returns a format from the queue.
		We have to take a queue, because the write-signals might occur asynchronus,
		so we set a format for the wrong characters.
		
		@returns: the popped format
		@rtype: Qt.QTextCharFormat"""

		return self.formatQueue.get()

	def virgin_format (self):
		"""The normal standard format. It is necessary to create it as a new one for some
		dubious reasons ... only Qt.QGod knows why."""
		return Qt.QTextCharFormat(self.stdFormat)
