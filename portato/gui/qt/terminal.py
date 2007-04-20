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

from threading import Thread, Lock
from os import read

from portato.gui.wrapper import Console
from portato.helper import debug

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
backspace = 8
title_seq = ("\x1b", "]")
title_end = "\x07"

# the attributes
attr = {}
attr[0]			=  	None 				# normal
attr[1]			=  	BoldFormat()	 	# bold
attr[4]    		=  	UnderlineFormat()	# underline
attr[30]        =  	ColorFormat("black")
attr[31]        =	ColorFormat("red")
attr[32]        = 	ColorFormat("green")
attr[33]       	= 	ColorFormat("yellow")
attr[34]        = 	ColorFormat("blue")
attr[35]      	= 	ColorFormat("magenta")
attr[36]        = 	ColorFormat("cyan")
attr[37]        = 	ColorFormat("white")
attr[39]      	= 	None				# default

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
		self.stdFormat = self.currentCharFormat()
		self.formatQueue = []
		self.formatLock = Lock()
		self.title = None

		self.setReadOnly(True)

		# we need these two signals, as threads are not allowed to access the GUI
		# solution: thread sends signal, which is handled by the main loop
		Qt.QObject.connect(self, Qt.SIGNAL("doSomeWriting"), self._write)
		Qt.QObject.connect(self, Qt.SIGNAL("deletePrevChar()"), self._deletePrev)

	def _deletePrev (self):
		"""Deletes the previous character."""
		self.textCursor().deletePreviousChar()

	def _write (self, text):
		"""Writes some text. A text of "\\x1b" signals _write() to reload
		the current char format.
		
		@param text: the text to print
		@type text: string"""

		if text == esc_seq[0]: # \x1b -> reload format
			self.setCurrentCharFormat(self.get_format())
		else:
			
			if not self.textCursor().atEnd(): # move cursor and re-set format
				f = self.currentCharFormat()
				self.moveCursor(Qt.QTextCursor.End)
				self.setCurrentCharFormat(f)
			
			# insert the text
			self.textCursor().insertText(text)
			
			# scroll down if needed
			self.ensureCursorVisible()

	def write(self, text):
		"""Convenience function for emitting the writing signal."""
		self.emit(Qt.SIGNAL("doSomeWriting"), text)

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
		
		while self.run:
			s = read(self.pty, 1)
			if s == "": break # nothing read -> finish

			if ord(s) == backspace: # BS
				self.emit(Qt.SIGNAL("deletePrevChar()"))
				continue

			if s == esc_seq[0]: # -> 0x27
				s = read(self.pty, 1)
				if s == esc_seq[1]: # -> [
					while True:
						_s = read(self.pty, 1)
						s += _s
						if _s == seq_end: break
					self.parse_seq(s[1:-1])
					continue

				elif s == title_seq[1]: # -> ]
					while True:
						_s = read(self.pty, 1)
						s += _s
						if _s == title_end: break
					
					self.parse_title(s[1:-1])
					continue
				else:
					self.write(esc_seq[0]+s)
			
			if s == "\r": continue
			self.write(s)

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

		self.formatLock.acquire()
		self.formatQueue.append(format)
		self.formatLock.release()

	def get_format (self):
		"""Returns a format from the queue.
		We have to take a queue, because the write-signals might occur asynchronus,
		so we set a format for the wrong characters.
		
		@returns: the popped format
		@rtype: Qt.QTextCharFormat"""

		self.formatLock.acquire()
		f = self.formatQueue.pop(0)
		self.formatLock.release()
		return f

	def virgin_format (self):
		"""The normal standard format. It is necessary to create it as a new one for some
		dubious reasons ... only Qt.QGod knows why."""
		return Qt.QTextCharFormat(self.stdFormat)
