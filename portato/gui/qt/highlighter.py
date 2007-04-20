# -*- coding: utf-8 -*-
#
# File: portato/gui/qt/highlighter.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

# The syntax is inspired by the gtksourceview syntax by
# Leonardo Ferreira Fontenelle <leo.fontenelle@gmail.com>

from PyQt4 import Qt
from portato.helper import debug

import re # prefer Python-Module over Qt-one

class EbuildHighlighter (Qt.QSyntaxHighlighter):
	"""A QSyntaxHighlighter implementation for the use with ebuild-syntax."""

	NORMAL_STATE = 0
	STRING_STATE = 1

	def __init__ (self, edit):
		"""Constructor.

		@param edit: the EditWidget to use the highlighter with
		@type edit: Qt.QTextEdit"""

		Qt.QSyntaxHighlighter.__init__(self, edit)
		
		#
		# the regular expressions ... *muahahaha*
		#
		
		# comments
		self.comment = self.__create(r'#.*', color = "steelblue", italic = True)
		
		# bash variables
		self.bashVar = self.__create(r'(\$\{.+?\})|(\$\w+)', color = "green")
		
		# a string
		self.string = self.__create(r'(?<!\\)"', color = "fuchsia")
		
		# the syntax elements, which are checked in a loop
		self.syntax = {}

		# bash syntax
		self.syntax["bashSyn"] = self.__create(r'\b(case|do|done|elif|else|esac|exit|fi|for|function|if|in|local|read|return|select|shift|then|time|until|while)\b', color = "navy", underline = True)

		# special bash commands
		self.syntax["bashCmd"] = self.__create(r'\b(make|awk|cat|cd|chmod|chown|cp|echo|env|export|grep|head|let|ln|mkdir|mv|rm|sed|set|tail|tar|touch|unset)\b', color = "navy", bold = True)
		
		# portage variables
		self.syntax["portVar"] = self.__create(r'\b((ARCH|HOMEPAGE|DESCRIPTION|IUSE|SRC_URI|LICENSE|SLOT|KEYWORDS|FILESDIR|WORKDIR|(P|R)?DEPEND|PROVIDE|DISTDIR|RESTRICT|USERLAND)|(S|D|T|PV|PF|P|PN|A)|C(XX)?FLAGS|LDFLAGS|C(HOST|TARGET|BUILD))\b', color = "saddlebrown", bold = True)
		
		# portage commands
		self.syntax["portCmd"] = self.__create(r'\b(e(begin|end|conf|install|make|warn|infon?|error|patch)|die|built_with_use|use(_(with|enable))?|inherit|hasq?|(has|best)_version|unpack|(do|new)(ins|s?bin|doc|lib(|\.so|\.a)|man|info|exe|initd|confd|envd|pam|menu|icon)|do(python|sed|dir|hard|sym|html|jar|mo)|keepdir|prepall(|docs|info|man|strip)|prep(info|lib|lib\.(so|a)|man|strip)|(|doc|ins|exe)into|f(owners|perms)|(exe|ins|dir)opts)\b', color = "saddlebrown", bold = True)
		
		# portage functions, i.e. the functions implemented by the ebuild
		self.syntax["portFunc"] = self.__create(r'^(src_(unpack|compile|install|test)|pkg_(config|nofetch|setup|(pre|post)(inst|rm)))', color = "green")
		
	def do_reg_exp (self, syntaxTuple, string):
		"""Tries to match a regular expression and if this succeeds, 
		sets the text format.

		@param syntaxTuple: tuple holding regexp and format
		@type sytaxTuple: (RE-object, Qt.QTextCharFormat)
		@param string: the string to look in
		@type string: string"""

		regexp, format = syntaxTuple

		match = regexp.search(string)
			
		while match is not None:
			span = match.span()
			length = span[1]-span[0]
			
			self.setFormat(span[0], length, format)
			match = regexp.search(string, span[1])

	def highlightBlock (self, string):
		"""This function is called, whenever the edit want to have some text checked.
		
		@param string: the text to check
		@type string: Qt.QString"""

		string = str(string) # we got a QString here

		# check the normal syntax elements
		for t in self.syntax.values():
			self.do_reg_exp(t, string)

		# reset to normal state :)
		self.setCurrentBlockState(self.NORMAL_STATE)

		# look for strings
		prevStart = 0
		foundEnd = False
		stringMatch = self.string[0].search(string)
		
		if self.previousBlockState() == self.STRING_STATE: # we were in a string last time
			if stringMatch is None: # and there is no end of string in this line
				self.setFormat(0, len(string), self.string[1])
				self.setCurrentBlockState(self.STRING_STATE)
			else:
				foundEnd = True

		while stringMatch is not None:

			if foundEnd: # we know that the string will end in this block
				self.setCurrentBlockState(self.NORMAL_STATE)
				self.setFormat(prevStart, stringMatch.end() - prevStart, self.string[1])
				
				# look for a possible start of another string
				stringMatch = self.string[0].search(string, stringMatch.end())
				foundEnd = False
			
			else: # we have entered a new string
				
				prevStart = stringMatch.start()
				stringMatch = self.string[0].search(string, stringMatch.end()) # the end of string
				
				if stringMatch is not None:
					foundEnd = True
				else: # no string end: mark the rest of the line as string
					self.setCurrentBlockState(self.STRING_STATE)
					self.setFormat(prevStart, len(string) - prevStart, self.string[1])

		self.do_reg_exp(self.bashVar, string) # replace bashVars in strings
		self.do_reg_exp(self.comment, string) # do comments last

	def __create (self, regexp, color = None, italic = False, bold = False, underline = False):
		"""This creates a syntax tuple.
		
		@param regexp: the regular expression
		@type regexp: string
		@param color: the color to take; if None, take standard color
		@type color: string
		@param italic: italic-flag
		@type italic: bool
		@param bold: bold-flag
		@type bold: bool
		@param underline: underline-flag
		@type underline: bool
		
		@returns: the created syntax-tuple
		@rtype: (RE-object, Qt.QTextCharFormat)
		"""

		compRe = re.compile(regexp)
		format = Qt.QTextCharFormat()

		font = Qt.QFont()
		font.setItalic(italic)
		font.setBold(bold)
		font.setUnderline(underline)
		format.setFont(font)

		if color is not None:
			brush = Qt.QBrush(Qt.QColor(color))
			format.setForeground(brush)

		return (compRe, format)
