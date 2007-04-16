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

	def __init__ (self, parent):
		Qt.QTextEdit.__init__(self, parent)

		self.pty = None
		self.running = False
		self.stdFormat = self.currentCharFormat()
		self.formatQueue = []
		self.formatLock = Lock()
		self.title = None

		self.setReadOnly(True)

		Qt.QObject.connect(self, Qt.SIGNAL("doSomeWriting"), self._write)
		Qt.QObject.connect(self, Qt.SIGNAL("deletePrevChar()"), self._deletePrev)

	def _deletePrev (self):
		self.textCursor().deletePreviousChar()

	def _write (self, text):
		if text == esc_seq[0]:
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
		self.emit(Qt.SIGNAL("doSomeWriting"), text)

	def start_new_thread (self):
			self.run = True
			self.current = Thread(target=self.__run)
			self.current.setDaemon(True) # close application even if this thread is running
			self.current.start()

	def set_pty (self, pty):
		if not self.running:
			self.pty = pty
			self.start_new_thread()
			self.running = True
		
		else:
			# quit current thread
			self.run = False
	#		self.current.join()
			self.clear()

			self.pty = pty # set this after clearing to lose no chars :)
			self.start_new_thread()

	def __run (self):
		while self.run:
			s = read(self.pty, 1)
			if s == "": break

			if ord(s) == backspace:
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
		global attr

		format = self.virgin_format()

		if seq != reset_seq: # resettet -> done
			seq = seq.split(seq_sep)
			for s in seq:
				try:
					s = int(s)
				except ValueError:
					format = self.virgin_format()
					break

				if attr[s] is not None:
					format.merge(attr[s])
				else:
					format = self.virgin_format()
					break

		self.add_format(format)
		self.write(esc_seq[0])

	def parse_title (self, seq):

		if not seq.startswith("0;"):
			return

		self.title = seq[2:]

	def get_window_title (self):
		return self.title

	def add_format (self, format):
		self.formatLock.acquire()
		self.formatQueue.append(format)
		self.formatLock.release()

	def get_format (self):
		self.formatLock.acquire()
		f = self.formatQueue.pop(0)
		self.formatLock.release()
		return f

	def virgin_format (self):
		return Qt.QTextCharFormat(self.stdFormat)
