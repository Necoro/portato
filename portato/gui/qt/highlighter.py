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

	NORMAL_STATE = 0
	STRING_STATE = 1

	def __init__ (self, edit):
		Qt.QSyntaxHighlighter.__init__(self, edit)
		
		self.comment = self.__create(r'#.*', color = "steelblue", italic = True)
		self.bashVar = self.__create(r'(\$\{.+?\})|(\$\w+)', color = "green")
		
		self.syntax = {}
		self.syntax["bashSyn"] = self.__create(r'\b(case|do|done|elif|else|esac|exit|fi|for|function|if|in|local|read|return|select|shift|then|time|until|while)\b', color = "navy", underline = True)

		self.syntax["bashCmd"] = self.__create(r'\b(make|awk|cat|cd|chmod|chown|cp|echo|env|export|grep|head|let|ln|mkdir|mv|rm|sed|set|tail|tar|touch|unset)\b', color = "navy", bold = True)
		
		self.syntax["portVar"] = self.__create(r'\b((ARCH|HOMEPAGE|DESCRIPTION|IUSE|SRC_URI|LICENSE|SLOT|KEYWORDS|FILESDIR|WORKDIR|(P|R)?DEPEND|PROVIDE|DISTDIR|RESTRICT|USERLAND)|(S|D|T|PV|PF|P|PN|A)|C(XX)?FLAGS|LDFLAGS|C(HOST|TARGET|BUILD))\b', color = "saddlebrown", bold = True)
		
		self.syntax["portCmd"] = self.__create(r'\b(e(begin|end|conf|install|make|warn|infon?|error|patch)|die|built_with_use|use(_(with|enable))?|inherit|hasq?|(has|best)_version|unpack|(do|new)(ins|s?bin|doc|lib(|\.so|\.a)|man|info|exe|initd|confd|envd|pam|menu|icon)|do(python|sed|dir|hard|sym|html|jar|mo)|keepdir|prepall(|docs|info|man|strip)|prep(info|lib|lib\.(so|a)|man|strip)|(|doc|ins|exe)into|f(owners|perms)|(exe|ins|dir)opts)\b', color = "saddlebrown", bold = True)
		
		self.syntax["portFunc"] = self.__create(r'^(src_(unpack|compile|install|test)|pkg_(config|nofetch|setup|(pre|post)(inst|rm)))', color = "green")
		
		self.string = self.__create(r'(?<!\\)"', color = "fuchsia")

	def do_reg_exp (self, syntaxTuple, string):
		regexp, format = syntaxTuple

		match = regexp.search(string)
			
		while match is not None:
			span = match.span()
			length = span[1]-span[0]
			
			self.setFormat(span[0], length, format)
			match = regexp.search(string, span[1])

	def highlightBlock (self, string):
		string = str(string) # we got a QString here

		for t in self.syntax.values():
			self.do_reg_exp(t, string)

		self.setCurrentBlockState(self.NORMAL_STATE)

		# look for strings
		prevStart = 0
		foundEnd = False
		stringMatch = self.string[0].search(string)
		if self.previousBlockState() == self.STRING_STATE:
			if stringMatch is None:
				self.setFormat(0, len(string), self.string[1])
				self.setCurrentBlockState(self.STRING_STATE)
			else:
				foundEnd = True

		while stringMatch is not None:

			if foundEnd:
				self.setCurrentBlockState(self.NORMAL_STATE)
				self.setFormat(prevStart, stringMatch.end() - prevStart, self.string[1])
				stringMatch = self.string[0].search(string, stringMatch.end())
				foundEnd = False
			else:
				prevStart = stringMatch.start()
				stringMatch = self.string[0].search(string, stringMatch.end())
				if stringMatch is not None:
					foundEnd = True
				else:
					self.setCurrentBlockState(self.STRING_STATE)
					self.setFormat(prevStart, len(string) - prevStart, self.string[1])

		self.do_reg_exp(self.bashVar, string) # replace bashVars in strings
		self.do_reg_exp(self.comment, string) # do comments last

	def __create (self, regexp, color = None, italic = False, bold = False, underline = False):

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
