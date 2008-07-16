#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import re
import keyword
import code
import inspect
import compiler
import wx
import wx.stc as stc
import dabo

if __name__ == "__main__":
	dabo.ui.loadUI("wx")

import dabo.dEvents as dEvents
import dabo.dColors as dColors
from dabo.dLocalize import _
import dDataControlMixin as dcm
import dTimer

LexerDic = {
		"ada": stc.STC_LEX_ADA,
		"ave": stc.STC_LEX_AVE,
		"baan": stc.STC_LEX_BAAN,
		"batch": stc.STC_LEX_BATCH,
		"bullant": stc.STC_LEX_BULLANT,
		"config": stc.STC_LEX_CONF,
		"container": stc.STC_LEX_CONTAINER,
		"c++": stc.STC_LEX_CPP,
		"diff": stc.STC_LEX_DIFF,
		"eiffel": stc.STC_LEX_EIFFEL,
		"eiffelKw": stc.STC_LEX_EIFFELKW,
		"errorlist": stc.STC_LEX_ERRORLIST,
		"html": stc.STC_LEX_HTML,
		"latex": stc.STC_LEX_LATEX,
		"lisp": stc.STC_LEX_LISP,
		"lua": stc.STC_LEX_LUA,
		"makefile": stc.STC_LEX_MAKEFILE,
		"matlab": stc.STC_LEX_MATLAB,
		"nncrontab": stc.STC_LEX_NNCRONTAB,
		"plain text": stc.STC_LEX_NULL,
		"pascal": stc.STC_LEX_PASCAL,
		"perl": stc.STC_LEX_PERL,
		"php": stc.STC_LEX_PHPSCRIPT,
		"props": stc.STC_LEX_PROPERTIES,
		"python": stc.STC_LEX_PYTHON,
		"ruby": stc.STC_LEX_RUBY,
		"sql": stc.STC_LEX_SQL,
		"tcl": stc.STC_LEX_TCL,
		"vb": stc.STC_LEX_VB,
		"vbscript": stc.STC_LEX_VBSCRIPT,
		"xcode": stc.STC_LEX_XCODE,
		"xml": stc.STC_LEX_XML}

fileFormatsDic = {
		".ada": "ada",
		".bat": "batch",
		".cfg": "config",
		".config": "config",
		".c": "c++",
		".h": "c++",
		".cpp": "c++",
		".diff": "diff",
		".html": "html",
		".htm": "html",
		".css": "html",
		".tex": "latex",
		".cls": "latex",
		".lsp": "lisp",
		".pas": "pascal",
		".py": "python",
		".pyw": "python",
		".php": "php",
		".pl": "perl",
		".rb": "ruby",
		".ruby": "ruby",
		".sql": "sql",
		".txt": "plain text",
		".vbs": "vbscript",
		".cdxml": "xml",
		".cnxml": "xml",
		".mnxml": "xml",
		".rfxml": "xml",
		".xml": "xml"}


## testing load performance:
delay = False

#- fontMode = "proportional"	# 'mono' or 'proportional'
fontMode = "mono"  # 'mono' or 'proportional'

if wx.Platform == '__WXMSW__':
	monoFont = "Courier New"
	propFont = "Verdana"
	fontSize = 9
elif wx.Platform == '__WXMAC__':
	monoFont = "Monaco"
	propFont = "Verdana"
	fontSize = 12
else:
	monoFont = "Courier"
	propFont = "Helvetica"
	fontSize = 11

if fontMode == "mono":
	fontFace = monoFont
else:
	fontFace = propFont


class StyleTimer(dTimer.dTimer):
	def afterInit(self):
		# Default timer interval
		self.styleTimerInterval = 50
		self.super()
		self.bindEvent(dEvents.Hit, self.onHit)
		self.mode = "container"
		
	def onHit(self, evt):
		#self.Interval = 0
		self.stop()
		if self.mode in LexerDic.keys():
			if self.Parent:
				self.Parent.SetLexer(LexerDic[self.mode])
			self.mode = "container"
			self.Interval = self.styleTimerInterval
		else:
			if self.Parent:
				self.Parent.SetLexer(stc.STC_LEX_CONTAINER)


class STCPrintout(wx.Printout):
	"""Printout class for styled text controls. Taken from the following
	program by Riaan Booysen:
		-----------------------------------------------------------------------------
		 Name:		   STCPrinting.py
		 Purpose:
		
		 Author:	   Riaan Booysen
		
		 Created:	   2003/05/21
		 RCS-ID:	   $Id: STCPrinting.py,v 1.8 2006/10/12 12:19:17 riaan Exp $
		 Copyright:   (c) 2003 - 2006
		 Licence:	   wxWidgets
		-----------------------------------------------------------------------------
		Boa:Dialog:STCPrintDlg
	"""
	margin = 0.1
	linesPerPage = 80

	def __init__(self, stc, colourMode=0, filename='', doPageNums=1):
		wx.Printout.__init__(self)
		self.stc = stc
		self.colourMode = colourMode
		self.filename = filename
		self.doPageNums = doPageNums

		self.pageTotal, m = divmod(stc.GetLineCount(), self.linesPerPage)
		if m: self.pageTotal += 1


	def HasPage(self, page):
		return (page <= self.pageTotal)


	def GetPageInfo(self):
		return (1, self.pageTotal, 1, 32000)


	def OnPrintPage(self, page):
		stc = self.stc
		self.stcLineHeight = stc.TextHeight(0)

		# calculate sizes including margin and scale
		dc = self.GetDC()
		dw, dh = dc.GetSizeTuple()
		mw = self.margin*dw
		mh = self.margin*dh
		textAreaHeight = dh - mh*2
		textAreaWidth = dw - mw*2
		scale = float(textAreaHeight)/(self.stcLineHeight*self.linesPerPage)
		dc.SetUserScale(scale, scale)

		# render page titles and numbers
		f = dc.GetFont()
		f.SetFamily(wx.ROMAN)
		f.SetFaceName('Times New Roman')
		f.SetPointSize(f.GetPointSize()+3)
		dc.SetFont(f)

		if self.filename:
			tlw, tlh = dc.GetTextExtent(self.filename)
			dc.DrawText(self.filename,
				  int(dw/scale/2-tlw/2), int(mh/scale-tlh*3))

		if self.doPageNums:
			pageLabel = _('Page: %d') % page
			plw, plh = dc.GetTextExtent(pageLabel)
			dc.DrawText(pageLabel,
				  int(dw/scale/2-plw/2), int((textAreaHeight+mh)/scale+plh*2))

		# render stc into dc
		stcStartPos = stc.PositionFromLine((page-1)*self.linesPerPage)
		stcEndPos = stc.GetLineEndPosition(page*self.linesPerPage-1)

		maxWidth = 32000
		stc.SetPrintColourMode(self.colourMode)
		ep = stc.FormatRange(1, stcStartPos, stcEndPos, dc, dc,
						wx.Rect(int(mw/scale), int(mh/scale),
							   maxWidth, int(textAreaHeight/scale)),
						wx.Rect(0, (page-1)*self.linesPerPage*self.stcLineHeight,
							maxWidth, self.stcLineHeight*self.linesPerPage))
		# warn when fewer characters than expected are rendered by the stc when
		# printing
		if not self.IsPreview():
			if ep < stcEndPos:
				print _('warning: on page %s: not enough chars rendered, diff: %s')%(page, stcEndPos-ep)
		return True


class dEditor(dcm.dDataControlMixin, stc.StyledTextCtrl):
	# The Editor is copied from the wxPython demo, StyledTextCtrl_2.py, 
	# and modified. Thanks to Robin Dunn and everyone that contributed to 
	# that demo to get us going!
	fold_symbols = 3

	def __init__(self, parent, properties=None, attProperties=None, *args, **kwargs):
		self._baseClass = dEditor
		self._fileName = ""
		self._beforeInit(None)
		name, _explicitName = self._processName(kwargs, self.__class__.__name__)
		# Declare the attributes that underly properties.
		self._autoCompleteList = False
		self._autoIndent = True
		self._commentString = "#- "
		self._bufferedDrawing = True
		self._hiliteCharsBeyondLimit = False
		self._hiliteLimitColumn = 79
		self._encoding = self.Application.Encoding
		self._eolMode = ""
		self._useAntiAliasing = True
		self._codeFolding = True
		self._showLineNumbers = True
		self._showEOL = False
		self._showWhiteSpace = False
		self._useStyleTimer = False
		self._tabWidth = 4
		self._useTabs = True
		self._showCallTips = True
		self._codeCompletion = True
		self._syntaxColoring = True
		self._language = "plain text"
		self._keyWordsLanguage = ""
		self._defaultsSet = False
		self._fontFace = None
		self._fontSize = None
		self._useBookmarks = False
		self._selectionBackColor = None
		self._selectionForeColor = None
		self._title = ""
		self._importPat = re.compile(r"\bimport\b")
		self._classPat = re.compile(r"^\s*class ([^\(]+)\(([^\)]*?)\)")
		self._defPat = re.compile(r"^\s*def ")

		stc.StyledTextCtrl.__init__(self, parent, -1, 
				style = wx.NO_BORDER)
		dcm.dDataControlMixin.__init__(self, name, properties, attProperties, 
				_explicitName=_explicitName, *args, **kwargs)
		self._afterInit()
		
		self._printData = wx.PrintData()
		self._printout = STCPrintout(self)
		self._newFileName = _("< New File >")
		self._curdir = os.getcwd()
		self._registerFunc = None
		self._unRegisterFunc = None
		# Used for parsing class and method names
		self._pat = re.compile("^[ \t]*((?:(?:class)|(?:def)) [^\(]+)\(", re.M)

		self.modifiedEventMask = (stc.STC_MOD_INSERTTEXT | stc.STC_MOD_DELETETEXT |
				stc.STC_PERFORMED_USER | stc.STC_PERFORMED_UNDO | stc.STC_PERFORMED_REDO)
		self.SetModEventMask(self.modifiedEventMask)
		self.Bind(stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
		self.Bind(stc.EVT_STC_MARGINCLICK, self.OnMarginClick)
		self.Bind(stc.EVT_STC_MODIFIED, self.OnModified)
		self.Bind(stc.EVT_STC_STYLENEEDED, self.OnStyleNeeded)
		self.Bind(stc.EVT_STC_NEEDSHOWN, self.OnNeedShown)
		
		if delay:
			self.bindEvent(dEvents.Idle, self.onIdle)
		else:
			pass
# 			self.setDefaults()
# 			self._defaultsSet = True

		app = self.Application
		self._fontFace = app.getUserSetting("editor.fontface")
		self._fontSize = app.getUserSetting("editor.fontsize")
		if self._fontFace:
			dabo.ui.callAfter(self.changeFontFace, self._fontFace)
		else:
			self._fontFace = self.GetFont().GetFaceName()
		if self._fontSize:
			dabo.ui.callAfter(self.changeFontSize, self._fontSize)
		else:
			self._fontSize = self.GetFont().GetPointSize()

		self._syntaxColoring = True
		self._styleTimer = StyleTimer(self)
		self._styleTimer.stop()
		
		# Set the marker used for bookmarks
		self._bmkPos = 5
		self.MarkerDefine(self._bmkPos, 
				stc.STC_MARK_CIRCLE, "gray", "cyan")
		justFname = os.path.split(self._fileName)[1]
		svd = app.getUserSetting("bookmarks.%s" % justFname, "{}")
		if svd:
			self._bookmarks = eval(svd)
		else:
			self._bookmarks = {}
		# This holds the last saved bookmark status
		self._lastBookmarks = []
		# Create a timer to regularly flush the bookmarks
		self._bookmarkTimer = bmt = dTimer.dTimer(self)
		bmt.Interval = 20000		# 20 sec.
		bmt.bindEvent(dEvents.Hit, self._saveBookmarks)
		bmt.start()		

		if self.UseStyleTimer:
			self._styleTimer.mode = "container"
			self._styleTimer.start()
		self._clearDocument()
		self.setTitle()
	
	
	def setFormCallbacks(self, funcTuple):
		self._registerFunc, self._unRegisterFunc = funcTuple


	def __del__(self):
		self._saveBookmarks()
		self._unRegisterFunc(self)
		super(dEditor, self).__del__()
	
	
	def onPrintSetup(self):
		dlgData = wx.PageSetupDialogData(self._printData)
		printDlg = wx.PageSetupDialog(self, dlgData)
		printDlg.ShowModal()
		self._printData = wx.PrintData(dlgData.GetPrintData())
		printDlg.Destroy()
		
	
	def onPrintPreview(self):
		po1 = STCPrintout(self, stc.STC_PRINT_COLOURONWHITEDEFAULTBG,
				self._fileName, False)
		po2 = STCPrintout(self, stc.STC_PRINT_COLOURONWHITEDEFAULTBG,
				self._fileName, False)
		self._printPreview = wx.PrintPreview(po1, po2, self._printData)
		if not self._printPreview.Ok():
			dabo.errorLog.write(_("An error occured while preparing preview."))
			return
		frame = wx.PreviewFrame(self._printPreview, self.Form, _("Print Preview"))
		frame.Initialize()
		frame.SetSize(self.Form.Size)
		frame.CenterOnScreen()
		frame.Show(True)


	def onPrint(self, evt=None):
		pdd = wx.PrintDialogData()
		pdd.SetPrintData(self._printData)
		printer = wx.Printer(pdd)
		printout = STCPrintout(self, stc.STC_PRINT_COLOURONWHITEDEFAULTBG,
				self._fileName, False)

		if not printer.Print(self.Form, printout):
			dabo.errorLog.write(_("An error occured while printing."))
		else:
			self.printData = wx.PrintData(printer.GetPrintDialogData().GetPrintData())
		printout.Destroy()
		
	
	def setBookmark(self, nm, line=None):
		"""Creates a bookmark that can be referenced by the 
		identifying name that is passed. If a bookmark already
		exists for that name, the old one is deleted. The 
		bookmark is set on the current line unless a specific 
		line number is passed.
		"""
		if line is None:
			line = self._ZeroBasedLineNumber
		if nm in self._bookmarks.keys():
			self.clearBookmark(nm)
		hnd = self.MarkerAdd(line, self._bmkPos)
		self._bookmarks[nm] = hnd
		self._saveBookmarks()
	
	
	def findBookmark(self, nm):
		"""Moves to the line for the specified bookmark. If no such
		bookmark exists, does nothing.
		"""
		try:
			foundLine = self.MarkerLineFromHandle(self._bookmarks[nm])
		except KeyError:
			# No such bookmark
			foundLine = -1
		if foundLine > -1:
			self.moveToEnd()
			# Add some breathing room above
			self.LineNumber = foundLine-3
			self._ZeroBasedLineNumber = foundLine
	
	
	def clearBookmark(self, nm):
		"""Clears the specified bookmark. If no such bookmark 
		exists, does nothing.
		"""
		try:
			self.MarkerDeleteHandle(self._bookmarks[nm])
			del self._bookmarks[nm]
		except KeyError:
			pass
		self._saveBookmarks()


	def clearAllBookmarks(self):
		"""Removes all bookmarks."""
		self.MarkerDeleteAll(self._bmkPos)
		self._bookmarks.clear()
		self._saveBookmarks()
	
	
	def goNextBookMark(self, line=None):
		"""Moves to the next bookmark in the document. If the
		line to start searching from is not specified, searches from
		the current line. If there are no more bookmarks, nothing
		happens.
		"""
		### NOT WORKING! GOTTA FIGURE OUT THE MASK STUFF!  ###
		if line is None:
			line = self.LineNumber
		print "START LN", line
		nxtLine = self.MarkerNext(line, self._bmkPos)
		print "NEXT", nxtLine
		if nxtLine > -1:
			self.moveToEnd()
			self.LineNumber = nxtLine
		
		
	def goPrevBookMark(self, line=None):
		"""Moves to the previous bookmark in the document. If the
		line to start searching from is not specified, searches from
		the current line. If there are no more bookmarks, nothing
		happens.
		"""
		### NOT WORKING! GOTTA FIGURE OUT THE MASK STUFF!  ###
		if line is None:
			line = self.LineNumber
		print "START LN", line
		nxtLine = self.MarkerPrevious(line, self._bmkPos)
		print "PREV", nxtLine
		if nxtLine > -1:
			self.moveToEnd()
			self.LineNumber = nxtLine
		
	
	def getCurrentLineBookmark(self):
		"""Returns the name of the bookmark for the current
		line, or None if this line is not bookmarked.
		"""
		ret = None
		curr = self.LineNumber
		for nm, hnd in self._bookmarks.items():
			if self.MarkerLineFromHandle(hnd) == curr:
				ret = nm
				break
		return ret
		
		
	def getBookmarkList(self):
		"""Returns a list of all current bookmark names."""
		return self._bookmarks.keys()
		
		
	def getFunctionList(self):
		"""Returns a list of all 'class' and 'def' statements, along
		with their starting positions in the text.
		"""
		pat = re.compile(r"^([ \t]*(?:def )|(?:class ))([^\(]+)\(", re.M)
		ret = []
		mtch = 1
		pos = 0
		txt = self.GetText()
		while mtch:
			mtch = pat.search(txt)
			if mtch:
				key, nm = mtch.groups()
				pos += mtch.start(0)				
				ret.append((nm, pos, (key.strip() == "class")))
				keyOffset = len(key)
				txt = txt[mtch.start(0) + keyOffset:]
				pos += keyOffset
		return ret


	def getLineFromPosition(self, pos):
		"""Given a position within the text, returns the corresponding line 
		number. If the position is invalid, returns -1.
		"""
		return self.LineFromPosition(pos)


	def getPositionFromLine(self, linenum):
		"""Given a line number, returns the position of the start of that line.
		If the line number is invalid, returns -1."""
		return self.PositionFromLine(linenum)


	def getPositionFromXY(self, x, y=None):
		"""Given an x,y position, returns the position in the text if that point
		is close to any text; if not, returns -1.
		"""
		if y is None and isinstance(x, (list, tuple)):
			x, y = x
		return self.PositionFromPointClose(x, y)
		
		
	def getMarginWidth(self):
		"""Returns the width of the non-editing area along the left side."""
		ret = 0
		for ii in range(5):
			ret += self.GetMarginWidth(ii)
		return ret
		

	def showCurrentLine(self):
		"""Scrolls the editor so that the current position is visible."""
		self.EnsureCaretVisible()
		
		
	def OnNeedShown(self, evt):
		""" Called when the user deletes a hidden header line."""
		# We expand the previously folded text, but it may be better
		# to delete the text instead, since the user asked for it.
		# There are two bits of information in the event: the position
		# and the length. I think we could easily clear the text based
		# on this information, but for now I'll keep it just displaying
		# the previously hidden text. --pkm 2006-04-04.
		o = evt.GetEventObject()
		position = evt.GetPosition()
		length = evt.GetLength()
		headerLine = o.LineFromPosition(position)
		o.Expand(headerLine, True)


	def changeSelectedTextCase(self, newcase):
		newcase = newcase[0].lower()
		pos = self.SelectionPosition
		seltxt = self.SelectedText
		if newcase == "i":
			def invert(c):
				if c.islower():
					return c.upper()
				else:
					return c.lower()
			self.ReplaceSelection("".join(map(invert, self.SelectedText)))
		else:
			try:
				fnc = {"u": seltxt.upper, "l": seltxt.lower, "c": seltxt.title, 
						"t": seltxt.title}[newcase]
				self.ReplaceSelection(fnc())
			except KeyError:
				raise ValueError, "Case must be either upper, lower, capitalize, or invert."
		self.SelectionPosition = pos

	
	def selectLine(self):
		start =self.GetLineEndPosition(self.LineNumber-1)
		if self.Value[start] == "\r":
			start+=2
		else:
			start+=1
		end = self.GetLineEndPosition(self.LineNumber)
		self.SelectionPosition = (start, end)
	
	
	def selectWord(self):
		whiteSpace = " \t\r\n"
		syntaxDelimeters = """()[]{}"+-*/&%=\\;:"""
		curPos = self.GetCurrentPos()
		val = self.Value
		if val[curPos] in syntaxDelimeters:
			start=curPos
			end=start+1
		else:
			start=curPos
			while start-1 > 0:
				if val[start-1] not in (whiteSpace + syntaxDelimeters):
					start -= 1
				else:
					break
			
			end = curPos
			while end < len(val):
				if val[end] in (whiteSpace + syntaxDelimeters):
					break
				end += 1
		self.SelectionPosition = (start, end)
		self.SetCurrentPos(end)

	
	def OnSBScroll(self, evt):
		# redirect the scroll events from the dyn_sash's scrollbars to the STC
		self.GetEventHandler().ProcessEvent(evt)
		
	
	def OnSBFocus(self, evt):
		# when the scrollbar gets the focus move it back to the STC
		self.SetFocus()
	

	def OnStyleNeeded(self, evt):
		if not self._syntaxColoring:
			return
		self._styleTimer.mode = self.Language.lower()
		self._styleTimer.start()
		
		
	def onIdle(self, evt):
		if not self._defaultsSet and self.Language:
			self.setDefaults()
			self._defaultsSet = True
			

	def setDocumentDefaults(self):
		self.SetTabWidth(self.TabWidth)
		self.SetIndent(self.TabWidth)
		

	def setDefaults(self):
		self.UsePopUp(0)
		self.SetUseTabs(self.UseTabs)
		self.SetTabIndents(True)

		## Autocomplete settings:
		self.AutoCompSetIgnoreCase(True)
		self.AutoCompSetAutoHide(True)	 ## hide when the typed string no longer matches
		self.AutoCompStops(" ")  ## characters that will stop the autocomplete
		self.AutoCompSetFillUps(".(")
		# This lets you go all the way back to the '.' without losing the AutoComplete
		self.AutoCompSetCancelAtStart(False)

		## Note: "tab.timmy.whinge.level" is a setting that determines how to
		## indicate bad indentation.
		## It shows up as a blue underscore when the indentation is:
		##	   * 0 = ignore (default)
		##	   * 1 = inconsistent
		##	   * 2 = mixed spaces/tabs
		##	   * 3 = spaces are bad
		##	   * 4 = tabs are bad 
		self.SetProperty("tab.timmy.whinge.level", "1")
		self.setSyntaxColoring(self.SyntaxColoring)
		self.SetMargins(0,0)

		self.SetViewWhiteSpace(self.ShowWhiteSpace)
		self.SetBufferedDraw(self.BufferedDrawing)
		self.SetViewEOL(self.ShowEOL)
		self.SetUseAntiAliasing(self.UseAntiAliasing)

		## Seems that eolmode is CRLF on Mac by default... explicitly set it!
		if wx.Platform == "__WXMSW__":
			self.EOLMode = "CRLF"
		else:
			self.EOLMode = "LF"

		if self.HiliteCharsBeyondLimit:
			self.SetEdgeMode(stc.STC_EDGE_BACKGROUND)
			self.SetEdgeColumn(self.HiliteLimitColumn)

		self._setLineNumberMarginVisibility()
		self._setCodeFoldingMarginVisibility()

		# Make some styles,	 The lexer defines what each style is used for, we
		# just have to define what each style looks like.  This set is adapted from
		# Scintilla sample property files.
		self.setDefaultFont(fontFace, fontSize)
		# Python styles
		self.setPyFont(fontFace, fontSize)

		self.SetCaretForeground("BLUE")

		# Register some images for use in the AutoComplete box.
		self.RegisterImage(1, dabo.ui.strToBmp("daboIcon016"))
		self.RegisterImage(2, dabo.ui.strToBmp("property"))	#, setMask=False))
		self.RegisterImage(3, dabo.ui.strToBmp("event"))		#, setMask=False))
		self.RegisterImage(4, dabo.ui.strToBmp("method"))		#, setMask=False))
		self.RegisterImage(5, dabo.ui.strToBmp("class"))		#, setMask=False))

		self.CallTipSetBackground("yellow")
		self.SelectionBackColor = "yellow"
		self.SelectionForeColor = "black"
		

	def _setLineNumberMarginVisibility(self):
		"""Sets the visibility of the line number margin."""
		if self.ShowLineNumbers:
			self.SetMarginType(1, stc.STC_MARGIN_NUMBER)
			self.SetMarginSensitive(1, True)
			self.SetMarginWidth(1, 36)
		else:
			self.SetMarginSensitive(1, False)
			self.SetMarginWidth(1, 0)
			
		
	def _setCodeFoldingMarginVisibility(self):
		"""Sets the visibility of the code folding margin."""
		if not self.ShowCodeFolding:
			self.SetMarginSensitive(2, False)
			self.SetMarginWidth(2, 0)
		else:
			# Setup a margin to hold fold markers
			self.SetProperty("fold", "1")
			self.SetMarginType(2, stc.STC_MARGIN_SYMBOL)
			self.SetMarginMask(2, stc.STC_MASK_FOLDERS)
			self.SetMarginSensitive(2, True)
			self.SetMarginWidth(2, 12)

			if self.fold_symbols == 0:
				# Arrow pointing right for contracted folders,
				# arrow pointing down for expanded
				self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,
					stc.STC_MARK_ARROWDOWN, "black", "black");
				self.MarkerDefine(stc.STC_MARKNUM_FOLDER,
					stc.STC_MARK_ARROW, "black", "black");
				self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,
					stc.STC_MARK_EMPTY, "black", "black");
				self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,
					stc.STC_MARK_EMPTY, "black", "black");
				self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,
					stc.STC_MARK_EMPTY, "white", "black");
				self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID,
					stc.STC_MARK_EMPTY, "white", "black");
				self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL,
					stc.STC_MARK_EMPTY, "white", "black");

			elif self.fold_symbols == 1:
				# Plus for contracted folders, minus for expanded
				self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,
					stc.STC_MARK_MINUS, "white", "black");
				self.MarkerDefine(stc.STC_MARKNUM_FOLDER,
					stc.STC_MARK_PLUS,	"white", "black");
				self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,
					stc.STC_MARK_EMPTY, "white", "black");
				self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,
					stc.STC_MARK_EMPTY, "white", "black");
				self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,
					stc.STC_MARK_EMPTY, "white", "black");
				self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID,
					stc.STC_MARK_EMPTY, "white", "black");
				self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL,
					stc.STC_MARK_EMPTY, "white", "black");

			elif self.fold_symbols == 2:
				# Like a flattened tree control using circular headers and curved joins
				self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,
					stc.STC_MARK_CIRCLEMINUS, "white", "#404040");
				self.MarkerDefine(stc.STC_MARKNUM_FOLDER,
					stc.STC_MARK_CIRCLEPLUS, "white", "#404040");
				self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,
					stc.STC_MARK_VLINE, "white", "#404040");
				self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,
					stc.STC_MARK_LCORNERCURVE, "white", "#404040");
				self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,
					stc.STC_MARK_CIRCLEPLUSCONNECTED, "white", "#404040");
				self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID,
					stc.STC_MARK_CIRCLEMINUSCONNECTED, "white", "#404040");
				self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL,
					stc.STC_MARK_TCORNERCURVE, "white", "#404040");

			elif self.fold_symbols == 3:
				# Like a flattened tree control using square headers
				self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,
					stc.STC_MARK_BOXMINUS, "white", "#808080")
				self.MarkerDefine(stc.STC_MARKNUM_FOLDER,
					stc.STC_MARK_BOXPLUS, "white", "#808080")
				self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,
					stc.STC_MARK_VLINE, "white", "#808080")
				self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,
					stc.STC_MARK_LCORNER, "white", "#808080")
				self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,
					stc.STC_MARK_BOXPLUSCONNECTED, "white", "#808080")
				self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID,
					stc.STC_MARK_BOXMINUSCONNECTED, "white", "#808080")
				self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL,
					stc.STC_MARK_TCORNER, "white", "#808080")


	def changeFontFace(self, fontFace):
		if not self:
			return
		self.FontFace = fontFace
		
	
	def changeFontSize(self, fontSize):
		if not self:
			return
		if isinstance(fontSize, basestring):
			if fontSize.startswith("+"):
				newSize = self._fontSize + int(fontSize[1:])
			elif fontSize.startswith("-"):
				newSize = self._fontSize - int(fontSize[1:])
			else:
				# a raw string was passed
				try:
					newSize = int(fontSize)
				except ValueError:
					dabo.errorLog.write(_("Invalid value passed to changeFontSize: %s") % fontSize)
					return
		else:
			newSize = fontSize
		self.FontSize = newSize
		
		
	def setDefaultFont(self, fontFace, fontSize):
		# Global default styles for all languages
		self.StyleSetSpec(stc.STC_STYLE_DEFAULT, "face:%s,size:%d" % (fontFace, fontSize))
		self.StyleClearAll()  # Reset all to be like the default

		# Global default styles for all languages
		self.StyleSetSpec(stc.STC_STYLE_DEFAULT,
			"face:%s,size:%d" % (propFont, fontSize))
		self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,
			"back:#C0C0C0,face:%s,size:%d" % (propFont, 8))
		self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR,
			"face:%s" % fontFace)
		self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,
			"fore:#000000,back:#00FF00,bold")
		self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,
			"fore:#000000,back:#FF0000,bold")


	def setPyFont(self, fontFace, fontSize):
		# Python-specific styles
		self.StyleSetSpec(stc.STC_P_DEFAULT,
			"fore:#000000,face:%s,size:%d" % (fontFace, fontSize))
		# Comments
		self.StyleSetSpec(stc.STC_P_COMMENTLINE,
			"fore:#007F00,face:%s,size:%d,italic" % (fontFace, fontSize))
		# Number
		self.StyleSetSpec(stc.STC_P_NUMBER,
			"fore:#007F7F,size:%d" % fontSize)
		# String
		self.StyleSetSpec(stc.STC_P_STRING,
			"fore:#7F007F,face:%s,size:%d" % (fontFace, fontSize))
		# Single quoted string
		self.StyleSetSpec(stc.STC_P_CHARACTER,
			"fore:#7F007F,face:%s,size:%d" % (fontFace, fontSize))
		# Keyword
		self.StyleSetSpec(stc.STC_P_WORD,
			"fore:#00007F,bold,size:%d" % fontSize)
		# Triple quotes
		self.StyleSetSpec(stc.STC_P_TRIPLE,
			"fore:#7F0000,size:%d,italic" % fontSize)
		# Triple double quotes
		self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,
			"fore:#7F0000,size:%d,italic" % fontSize)
		# Class name definition
		self.StyleSetSpec(stc.STC_P_CLASSNAME,
			"fore:#0000FF,bold,underline,size:%d" % fontSize)
		# Function or method name definition
		self.StyleSetSpec(stc.STC_P_DEFNAME,
			"fore:#007F7F,bold,size:%d" % fontSize)
		# Operators
		self.StyleSetSpec(stc.STC_P_OPERATOR,
			"bold,size:%d" % fontSize)
		# Identifiers
		self.StyleSetSpec(stc.STC_P_IDENTIFIER,
			"fore:#000000,face:%s,size:%d" % (fontFace, fontSize))
		# Comment-blocks
		self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,
			"fore:#7F7F7F,size:%d,italic" % fontSize)
		# End of line where string is not closed
		self.StyleSetSpec(stc.STC_P_STRINGEOL,
			"fore:#000000,face:%s,back:#E0C0E0,eol,size:%d" % (fontFace, fontSize))





		
	def onCommentLine(self, evt):
		sel = self.GetSelection()
		begLine = self.LineFromPosition(sel[0])
		endLine = self.LineFromPosition(sel[1]-1)

		self.BeginUndoAction()
		for line in range(begLine, endLine+1):
			pos = self.PositionFromLine(line)
			self.InsertText(pos, self.CommentString)
		self.EndUndoAction()

		self.SetSelection(self.PositionFromLine(begLine), 
			self.PositionFromLine(endLine+1))
		

	def onUncommentLine(self, evt):
		sel = self.GetSelection()
		begLine = self.LineFromPosition(sel[0])
		endLine = self.LineFromPosition(sel[1]-1)

		self.BeginUndoAction()
		for line in range(begLine, endLine+1):
			pos = self.PositionFromLine(line)
			self.SetTargetStart(pos)
			self.SetTargetEnd(pos + len(self.CommentString))
			if self.SearchInTarget(self.CommentString) >= 0:
				self.ReplaceTarget("")
		self.EndUndoAction()

		self.SetSelection(self.PositionFromLine(begLine), 
			self.PositionFromLine(endLine+1))
	
	
	def onKeyDown(self, evt):
		keyCode = evt.EventData["keyCode"]
		if keyCode == wx.WXK_RETURN and self.AutoIndent and not self.AutoCompActive():
			## Insert auto indentation as necessary. This code was adapted from
			## PythonCard - Thanks Kevin for suggesting I take a look at it.
			evt.Continue = False
			self.CmdKeyExecute(stc.STC_CMD_NEWLINE)
			line = self.LineNumber - 1
			txt = self.GetLine(line).rstrip()
			
			currIndent = self.GetIndent()
			if currIndent == 0:
				indentLevel = 0
			else:
				indentLevel = self.GetLineIndentation(line) / self.GetIndent()
			
			# First, indent to the current level of indent:
			if self.UseTabs:
				padchar = "\t"
			else:
				padchar = " "
			padding = padchar * indentLevel
			pos = self.GetCurrentPos()
			
			self.InsertText(pos, padding)
			pos = pos + len(padding)
			
			# Next, indent another level if last line ended with ":"
			if len(txt) > 0 and txt[-1] == ':':
				padding = padchar
				self.InsertText(pos, padding)
				pos = pos + len(padding)
			self.SetCurrentPos(pos)
			self.SetSelection(pos, pos)


	def onKeyChar(self, evt):
		keyChar = evt.EventData["keyChar"]
		self._insertChar = ""
		
		if keyChar == "(" and self.AutoCompActive():
			self._insertChar = "("
		elif keyChar == "(" and self.ShowCallTips and not self.AutoCompActive():
			self.callTip()
		elif keyChar == "." and self.CodeCompletion:
			if self.AutoCompActive():
				# don't process the autocomplete, as it is 
				# already being processed. However, set the flag
				# so that onListSelection() knows to call 
				# autocomplete on the new item:
				self._insertChar = "."
				dabo.ui.callAfter(self._onPeriodActive)
			else:
				self._posBeforeCompList = self.GetCurrentPos() + 1
				dabo.ui.callAfter(self.codeComplete)
		elif self.AutoAutoComplete:
			if self.AutoCompActive():
				if keyChar in " ()[]{}.-":
					self.AutoCompCancel()
					return
			else:
				dabo.ui.callAfter(self.autoComplete, minWordLen=self.AutoAutoCompleteMinLen)


	def _onPeriodActive(self):
		self._posBeforeCompList = self.GetCurrentPos()
		dabo.ui.callAfter(self.codeComplete)


	def onListSelection(self, evt):
		txt = evt.GetText()
		if len(txt) > 0:
			insertChar = self._insertChar
			pos = self._posBeforeCompList
			self.SetTargetStart(pos)
			self.SetTargetEnd(self.GetCurrentPos())
			self.ReplaceTarget("")

			self.InsertText(pos, txt)
			self.GotoPos(pos + len(txt))

			if insertChar == "(":
				wx.CallAfter(self.callTip)
			elif insertChar == ".":
				self._posBeforeCompList = self.GetCurrentPos() + 1
				self.codeComplete()
			self._insertChar = ""
			
			
	def setInactive(self):
		"""Hides the auto-completion popup if one is open."""
		if self.AutoCompActive():
			self.AutoCompCancel()
			
	
	def getAvailableLanguages(cls):
		"""Returns an alphabetical list of all languages we have lexers for."""
		ret = LexerDic.keys()
		ret.sort()
		return ret
	getAvailableLanguages = classmethod(getAvailableLanguages)
		
		
	def setSyntaxColoring(self, color=None):
		"""Sets the appropriate lexer for syntax coloring."""
		lex = self.Language.lower()
		if color and lex:
			if lex in LexerDic.keys():
				self.SetLexer(LexerDic[lex])
				if lex == "python":
					if not self._keyWordsLanguage == lex:
						self.SetKeyWords(0, " ".join(keyword.kwlist))
						self._keyWordsLanguage = lex
				else:
					# Until we can get other keyword lists, we need to clear this out
					self.SetKeyWords(0, "")
					self._keyWordsLanguage = ""
				dabo.ui.callAfter(self.Colourise, 0, 1)
		else:
			self.ClearDocumentStyle()
			self.SetLexer(stc.STC_LEX_CONTAINER)		

		
	def OnModified(self, evt):
		if not self._syntaxColoring:
			return

		mt = evt.GetModificationType()
		if not mt & self.modifiedEventMask == mt:
			# For some reason the event masking doesn't always work
			return
		evt.Skip()
		self.setTitle()
		self.raiseEvent(dEvents.ContentChanged, evt)


	def OnUpdateUI(self, evt):
		if not self._syntaxColoring:
			return
		# check for matching braces
		braceAtCaret = -1
		braceOpposite = -1
		charBefore = None
		caretPos = self.GetCurrentPos()

		if caretPos > 0:
			charBefore = self.GetCharAt(caretPos - 1)
			styleBefore = self.GetStyleAt(caretPos - 1)

		# check before
		if charBefore and chr(charBefore) in "[]{}()" and styleBefore == stc.STC_P_OPERATOR:
			braceAtCaret = caretPos - 1

		# check after
		if braceAtCaret < 0:
			charAfter = self.GetCharAt(caretPos)
			styleAfter = self.GetStyleAt(caretPos)

			if charAfter and chr(charAfter) in "[]{}()" and styleAfter == stc.STC_P_OPERATOR:
				braceAtCaret = caretPos

		if braceAtCaret >= 0:
			braceOpposite = self.BraceMatch(braceAtCaret)

		if braceAtCaret != -1  and braceOpposite == -1:
			self.BraceBadLight(braceAtCaret)
		else:
			self.BraceHighlight(braceAtCaret, braceOpposite)
			#pt = self.PointFromPosition(braceOpposite)
			#self.Refresh(True, wxRect(pt.x, pt.y, 5,5))
			#print pt
			#self.Refresh(False)
			

	def OnMarginClick(self, evt):
		mg = evt.GetMargin()
		lineClicked = self.LineFromPosition(evt.GetPosition())
		if mg == 2:
			# Folding margin; fold and unfold as needed
			if evt.GetShift() and evt.GetControl():
				self.FoldAll()
			else:

				if self.GetFoldLevel(lineClicked) & stc.STC_FOLDLEVELHEADERFLAG:
					if evt.GetShift():
						self.SetFoldExpanded(lineClicked, True)
						self.Expand(lineClicked, True, True, 1)
					elif evt.GetControl():
						if self.GetFoldExpanded(lineClicked):
							self.SetFoldExpanded(lineClicked, False)
							self.Expand(lineClicked, False, True, 0)
						else:
							self.SetFoldExpanded(lineClicked, True)
							self.Expand(lineClicked, True, True, 100)
					else:
						self.ToggleFold(lineClicked)
		elif mg == 1:
			# Line number margin; hilite the line
			ln = self.LineFromPosition(evt.GetPosition())
			self.hiliteLine(ln, evt.GetShift())


	def hiliteLine(self, lineNum, extend=False):
		"""Selects the specified line. If the line number does not exist, 
		a ValueError is raised.
		"""
		start = self.PositionFromLine(lineNum)
		end = self.PositionFromLine(lineNum+1) -1
		if extend:
			# Need to extend from the current position
			currStart = self.GetSelectionStart()
			currEnd = self.GetSelectionEnd()
			start = min(start, currStart)
			end = max(end, currEnd)
		self.SetSelection(start, end)


	def callTip(self):
		"""Present the call tip for the current object, if any."""
		runtimeObjName = self._getRuntimeObjectName()
		obj = self._getRuntimeObject(runtimeObjName)
		pos = self.GetCurrentPos()

		if obj is not None:
			try:
				args = inspect.getargspec(obj)
				try:
					sarg = args[0][0]
				except IndexError:
					sarg = None
				if sarg is not None and sarg == "self":
					del args[0][0]
				args = inspect.formatargspec(args[0], args[1], args[2], args[3])
			except IndexError:
				args = ""

			if inspect.ismethod(obj):
				funcType = "Method"
			elif inspect.isfunction(obj):
				funcType = "Function"
			elif inspect.isclass(obj):
				funcType = "Class"
			elif inspect.ismodule(obj):
				funcType = "Module"
			elif inspect.isbuiltin():
				funcType = "Built-In"
			else:
				funcType = ""

			doc = ""
			docLines = obj.__doc__.splitlines()
			for line in docLines:
				doc += line.strip() + "\n"	 ## must be \n on all platforms
			doc = doc.strip()  ## Remove trailing blank line

			try:
				name = obj.__name__
			except AttributeError:
				name = ""
				
			shortDoc = "%s %s%s" % (funcType, name, args)
			longDoc = "%s\n\n%s" % (shortDoc, doc)
			
			self.CallTipShow(pos, shortDoc)
			# Highlight the object name:
			self.CallTipSetHighlight(len(funcType) + 1, 
				len(funcType) + len(name) + 1)

			# Let someone else display the complete documentation:
			self.raiseEvent(dEvents.DocumentationHint, 
				shortDoc=shortDoc, longDoc=longDoc, object=obj)
				

	def codeComplete(self):
		"""Display the code completion list for the current object, if any."""
		# Get the name of object the user is pressing "." after.
		# This could be 'self', 'dabo', or a reference to any object
		# previously defined.
		obj = self._getRuntimeObject(self._getRuntimeObjectName())
		if obj is not None:
			kw = []
			pos = self.GetCurrentPos()
			kw = [k for k in dir(obj)
				if not k.startswith("_")]
			
			# Sort upper case:
			kw.sort(lambda a,b: cmp(a.upper(), b.upper()))
			# Images are specified with a appended "?type"
			for i in range(len(kw)):
				try:
					obj_ = eval("obj.%s" % kw[i])
				except (AttributeError, TypeError):
					continue
				isEvent = False
				if inspect.isclass(obj_):
					try:
						isEvent = issubclass(obj_, dEvents.Event)
					except TypeError:
						pass				
				if type(obj_) == type(property()):
					kw[i] = kw[i] + "?2"
				elif inspect.isfunction(obj_) or inspect.ismethod(obj_):
					kw[i] = kw[i] + "?4"
				elif isEvent:
					kw[i] = kw[i] + "?3"
				elif inspect.isclass(obj_):
					kw[i] = kw[i] + "?5"
				else:
					# Punt with the Dabo icon:
					kw[i] = kw[i] + "?1"
					
			if self.AutoCompleteList:
				wx.CallAfter(self.AutoCompShow,0, " ".join(kw))
			else:
				self.Bind(stc.EVT_STC_USERLISTSELECTION, self.onListSelection)
				wx.CallAfter(self.UserListShow, 1, " ".join(kw))


	def FoldAll(self):
		lineCount = self.GetLineCount()
		expanding = True

		# find out if we are folding or unfolding
		for lineNum in range(lineCount):
			if self.GetFoldLevel(lineNum) & stc.STC_FOLDLEVELHEADERFLAG:
				expanding = not self.GetFoldExpanded(lineNum)
				break;

		lineNum = 0
		while lineNum < lineCount:
			level = self.GetFoldLevel(lineNum)
			if level & stc.STC_FOLDLEVELHEADERFLAG and \
			(level & stc.STC_FOLDLEVELNUMBERMASK) == stc.STC_FOLDLEVELBASE:
				if expanding:
					self.SetFoldExpanded(lineNum, True)
					lineNum = self.Expand(lineNum, True)
					lineNum = lineNum - 1
				else:
					lastChild = self.GetLastChild(lineNum, -1)
					self.SetFoldExpanded(lineNum, False)

					if lastChild > lineNum:
						self.HideLines(lineNum+1, lastChild)
			lineNum = lineNum + 1
	
	def FoldAllCode(self, expand):
		lineCount = self.GetLineCount()
		
		lineNum = 0
		while lineNum < lineCount:
			level = self.GetFoldLevel(lineNum)
			if level & stc.STC_FOLDLEVELHEADERFLAG:
				if expand:
					self.SetFoldExpanded(lineNum, True)
					self.ShowLines(lineNum, self.Expand(lineNum, True))
				else:
					lastChild = self.GetLastChild(lineNum, -1)
					self.SetFoldExpanded(lineNum, False)
					
					if lastChild > lineNum:
						self.HideLines(lineNum+1, lastChild)
			lineNum = lineNum + 1
	
	def Expand(self, line, doExpand, force=False, visLevels=0, level=-1):
		lastChild = self.GetLastChild(line, level)
		line = line + 1
		while line <= lastChild:
			if force:
				if visLevels > 0:
					self.Lines(line, line)
				else:
					self.HideLines(line, line)
			else:
				if doExpand:
					self.ShowLines(line, line)

			if level == -1:
				level = self.GetFoldLevel(line)

			if level & stc.STC_FOLDLEVELHEADERFLAG:
				if force:
					if visLevels > 1:
						self.SetFoldExpanded(line, True)
					else:
						self.SetFoldExpanded(line, False)

					line = self.Expand(line, doExpand, force, visLevels-1)
				else:
					if doExpand and self.GetFoldExpanded(line):
						line = self.Expand(line, True, force, visLevels-1)
					else:
						line = self.Expand(line, False, force, visLevels-1)
			else:
				line = line + 1;
		return line


	def promptToSave(self):
		try:
			fname = self._fileName
		except AttributeError:
			fname = None
		if fname is None or fname is "":
			s = "Do you want to save your changes?"
		else:
			s = "Do you want to save your changes to file '%s'?" % self._fileName
		return dabo.ui.areYouSure(s)

		
	def promptForFileName(self, prompt="Select a file", saveAs=False,
			path=None):
		"""Prompt the user for a file name."""
		if path is None:
			try:
				drct = self._curdir
			except AttributeError:
				drct = ""
		else:
			drct = path
		
		if saveAs:
			func = dabo.ui.getSaveAs
		else:
			func = dabo.ui.getFile
		fname = func("py", "cdxml", "cnxml", "mnxml", "rfxml", "*", message=prompt, defaultPath=drct)
		return fname
	
		
	def promptForSaveAs(self):
		"""Prompt user for the filename to save the file as.
		
		If the file exists, confirm with the user that they really want to
		overwrite.
		"""
		while True:
			fname = self.promptForFileName(prompt="Save As", saveAs=True)
			if fname is None:
				break
			if os.path.exists(fname):
				r = dabo.ui.areYouSure("File '%s' already exists. "
					"Do you want to overwrite it?" % fname, defaultNo=True)
				if r == None:
					# user canceled.
					fname = None
					break
				elif r == False:
					# let user pick another file
					pass
				else:
					# User chose to overwrite fname
					break
			else:
				break
		return fname


	def saveFile(self, fname=None):
		if self._curdir:
			os.chdir(self._curdir)
		if fname == None:
			try:
				fname = self._fileName
			except AttributeError:
				fname = self._newFileName
		
		if not fname or (fname == self._newFileName):
			# We are being asked to save a new file that doesn't exist on disk yet.
			fname = self.promptForSaveAs()
			if fname is None:
				# user canceled in the prompt: don't continue
				return False
		
		try:
			open(fname, "wb").write(self.GetText().encode(self.Encoding))
		except OSError:
			dabo.ui.stop("Could not save %s. Please check your write permissions." % fname)
			return False
		# set self._fileName, in case it was changed with a Save As
		self._fileName = fname
		self._clearDocument(clearText=False)
		# Save the appearance settings
		app = self.Application
		app.setUserSetting("editor.fontsize", self._fontSize)
		app.setUserSetting("editor.fontface", self._fontFace)
		# Save the bookmarks
		self._saveBookmarks()
		
		#if the file extension changed, automatically set the language if extension is known.
		fext = os.path.splitext(fname)[1]
		self.Language = fileFormatsDic.get(fext, self.Language)
		
		return True
	
	
	def _saveBookmarks(self, evt=None):
		if not self._useBookmarks:
			self._bookmarkTimer.stop()
		app = self.Application
		fname = self._fileName
		if not fname:
			return
		# Get the current status of bookmarks
		currBmks = [(nm, self.MarkerLineFromHandle(hnd))
				for nm, hnd in self._bookmarks.items()]
		if currBmks != self._lastBookmarks:
			# Save them
			self._lastBookmarks = currBmks
			justFname = os.path.split(fname)[1]
			base = ".".join(("bookmark", justFname))
			# Clear any existing settings.
			app.deleteAllUserSettings(base)
			newsettings = {}
			for nm, hnd in self._bookmarks.items():
				ln = self.MarkerLineFromHandle(hnd)
				setName = ".".join((base, nm))
				newsettings[setName] = ln
			if newsettings:
				app.setUserSettings(newsettings)
		
		
	def checkChangesAndContinue(self):
		"""Check to see if changes need to be saved, and if so prompt the user.
		
		Return False if saves were needed but not made.
		"""
		ret = True
		if self.GetModify():
			r = self.promptToSave()
			if r == None:
				# user canceled the prompt.
				ret = False
			elif r == True:
				# user wants changes saved.
				ret = self.saveFile()
			else:
				# user doesn't want changes saved.
				pass
		return ret
		
		
	def _clearDocument(self, clearText=True):
		"""Do everything needed to start the doc as if new."""
		if clearText:
			self.SetText("")
		self.SetSavePoint()
		self.EmptyUndoBuffer()
		self.setTitle()
		self.setDocumentDefaults()

		
	def newFile(self):
		"""Create a new file and edit it."""
		if self.checkChangesAndContinue():
			self._fileName = self._newFileName
			self._curdir = os.getcwd()
			self._clearDocument()
			return True
		else:
			return False
	
	
	def openFile(self, fileSpec=None):
		"""Open a new file and edit it."""
		if self.checkChangesAndContinue():
			if fileSpec is None:
				fileSpec = self.promptForFileName("Open")
				if fileSpec is None:
					return False
			try:
				f = open(fileSpec, "rb")
				text = f.read().decode(self.Encoding)
				f.close()
			except IOError:
				if os.path.exists(fileSpec):
					dabo.ui.stop("Could not open %s.  Please check that you have read permissions." % fileSpec)
					return False
				if dabo.ui.areYouSure("File '%s' does not exist."
						" Would you like to create it?" % fileSpec):
					text = ""
				else:
					return False
			self._fileName = fileSpec
			pth, fname = os.path.split(fileSpec)
			fext = os.path.splitext(fname)[1]
			self.Language = fileFormatsDic.get(fext, self.Language)
			self._curdir = pth
			self.SetText(text)
			self._clearDocument(clearText=False)
			ret = True
		else:
			ret = False
		
		# Restore the bookmarks
		app = self.Application
		fname = os.path.split(fileSpec)[1]
		keyspec = ".".join(("bookmark", fname)).lower()
		keys = app.getUserSettingKeys(keyspec)
		for key in keys:
			val = app.getUserSetting(".".join((keyspec, key)))
			self.setBookmark(key, val)
		# Restore the appearance
		self._fontFace = app.getUserSetting("editor.fontface")
		self._fontSize = app.getUserSetting("editor.fontsize")
		if self._fontFace:
			dabo.ui.callAfter(self.changeFontFace, self._fontFace)
		else:
			self._fontFace = self.GetFont().GetFaceName()
		if self._fontSize:
			dabo.ui.callAfter(self.changeFontSize, self._fontSize)
		else:
			self._fontSize = self.GetFont().GetPointSize()
		return ret


	def setTitle(self):
		"""Set the title of the editor"""
		try:
			_oldTitle = self._title
		except AttributeError:
			_oldTitle = ""
		try:
			fileName = os.path.split(self._fileName)[-1]
		except AttributeError:
			fileName = ""
		if not fileName:
			fileName = self._newFileName
			
		if self.GetModify():
			modChar = "*"
		else:
			modChar = ""
		self._title = "%s %s" % (fileName, modChar)

		if self._title != _oldTitle:
			self.raiseEvent(dEvents.TitleChanged)
			

	def increaseTextSize(self, pts=1):
		self.ZoomLevel += pts
		
		
	def decreaseTextSize(self, pts=1):
		self.ZoomLevel -= pts
		
		
	def restoreTextSize(self):
		self.ZoomLevel = 0
	
	
	def moveToBeginning(self):
		self.SetSelection(0, 0)
		self.EnsureCaretVisible()
		
		
	def moveToEnd(self):
		self.SetSelection(-1, -1)
		self.EnsureCaretVisible()
	
	
	def ensureLineVisible(self, line):
		self.EnsureVisible(line)
		self.LineNumber = line
		self.EnsureCaretVisible()


	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# Auto-completion code, used mostly unchanged from SPE
	# Copyright www.stani.be
	def autoComplete(self, object=0, minWordLen=0):
		word	= self.getWord()
		if isinstance(object, dEvents.KeyEvent):
			object = 0
		if not word: 
			if object:
				self.AddText('.')
			return
		if object:
			self.AddText('.')
			word+='.'
		if word and len(word) < minWordLen:
			return
		words	= self.getWords(word=word)
		if word[-1] == '.':
			try:
				obj = self.getWordObject(word[:-1])
				if obj:
					for attr in dir(obj):
						attr = '%s%s'%(word,attr)
						if attr not in words:
								words.append(attr)
			except IndexError:
				pass
		elif word[-1] in " ()[]{}":
			self.AutoCompCancel()
			return
		if words:
			words.sort(lambda a,b: cmp(a.upper(), b.upper()))
			# For some reason, the STC editor in Windows likes to add icons
			# even if they aren't requested. This explicitly removes them.
			wds = ["%s?0" % wd for wd in words]				
			self.AutoCompShow(len(word), " ".join(wds))

	
	def getWord(self,whole=None):
		for delta in (0,-1,1):
			word	= self._getWord(whole=whole,delta=delta)
			if word: return word
		return ''

	def _getWord(self,whole=None,delta=0):
		pos = self.GetCurrentPos()+delta
		line = self.GetCurrentLine()
		linePos = self.PositionFromLine(line)
		txt = self.GetLine(line)
		start = self.WordStartPosition(pos,1)
		if whole:
			end = self.WordEndPosition(pos,1)
		else:
			end = pos
		return txt[start-linePos:end-linePos]

	def getWords(self,word=None,whole=None):
		if not word: word = self.getWord(whole=whole)
		if not word:
			return []
		else:
			if self.AutoCompGetIgnoreCase:
				flag = re.I
			else:
				flag = 0
			retAll = ([x for x in re.findall(r"\b" + word + r"\w+\b", self._getTextSource(), flag)
				if x.find(',')==-1 and x[0]!= ' '])
			ret = dict.fromkeys(retAll).keys()
			return ret
	
	def _getTextSource(self):
		"""Override to include other sources."""
		return self.GetText()
		
		
	def getWordObject(self,word=None,whole=None):
		if not word: word=self.getWord(whole=whole)
		return self.evaluate(word)
	# End of auto-completion code
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	def _getRuntimeObjectName(self):
		"""Go backwards from the current position and get the runtime object name
		that the user is currently editing. For example, if they entered a '.' after
		'self', the runtime object name would be 'self'.
		"""
		end = self.GetCurrentPos()
		cur = end
		text = []
		while True:
			if cur < 1:
				break
			char = self.GetTextRange(cur-1, cur)
			if cur == end and char in (".", "("):
				# skip the char
				pass
			else:
				if ord(char) in (10,13,32,27,20) or char in (
					"()!@^%&*+="):
					break
				text.append(char)
			cur -= 1
		text.reverse()
		text = ''.join(text).strip()
		return text


	def _makeContainingClassIntoSelf(self):
		"""Make self refer to the class.
		
		For instance, in the following snippet:
			class MyClass(object):
				pass
				
		self would get bound to MyClass. This is to simulate the 
		runtime environment, for the purpose of getting auto-completion.
		"""
		classdef = None
		args = []
		for line in range(self.LineNumber - 1, -1, -1):
			text = self.GetLine(line).strip()
			if text[0:6] == "class ":
				# Now move forward, to get the entire classdef
				args = ""
				for line in range(line, self.LineNumber):
					text = self.GetLine(line).strip()
					if len(args) == 0 and "(" in text:
						args = text[text.index("("):]
						if "):" in args:
							args = args[0:args.index("):")]
							break
					if len(args) > 0 and "):" in text:
						args += text[0:text.index("):")]
						break
				# get rid of prepended (
				args = args[1:]
				break
		if args:
			classdef = "class self(%s): pass" % args
			try:
				exec classdef in self._namespaces
			except NameError:
				# Class is not in the namespace
				pass

		
	def _getRuntimeObject(self, runtimeObjectName):
		"""Given a runtimeObjectName, get the object.

		For example, "self" should return the class object that self would
		be an instance of at runtime.
		"""
		# Short-circuit return if the objname is empty:
		if len(runtimeObjectName.strip()) == 0:
			return None
		self._fillNamespaces()
		s = runtimeObjectName.split(".")
		outerObjectName = s[0].strip()
		if len(outerObjectName) == 0:
			return None

		if outerObjectName == "self":
			## This is a HACK, but I don't see another way. Basically, if the 
			## object name is "self", we are going to mangle it to be the class
			## that at runtime self is an instance of. Then, the object will
			## exist in the _namespaces and hence we'll get autocompletion for 
			## it. --pkm 9/20/04
			self._makeContainingClassIntoSelf()
		# Different editor usages may require additional namespace
		# hacks, such as the above. This is a hook for adding such hacks.
		self._namespaceHacks()
		o = self._namespaces.get(outerObjectName)
		if o is not None:
			innerObjectNames = '.'.join(s[1:])
			if len(innerObjectNames) > 0:
				try:
					o = eval("o.%s" % innerObjectNames)
				except (AttributeError, SyntaxError):
					o = None
		return o
	
	
	def _namespaceHacks(self):
		"""Hook method for any additional namespace hacks"""
		pass
		
	
	def _fillNamespaces(self):
		"""Get as many of the names that will exist at runtime as possible 
		into the _namespaces dict. We do this by finding all the 'import' 
		statements and executing them into the _namespaces dict.
		"""
		def genRange(rng):
			curr = 0
			while curr < rng:
				yield curr
				curr += 1
				
		self._namespaces = {}
		code2exec = []
		numGen = genRange(self.LineNumber + 1)
		for lineNum in numGen:
			line = self.GetLine(lineNum).rstrip()
			if not line.strip() or line.strip().startswith("#"):
				continue
				
			if self._importPat.search(line):
				# It's an 'import' statement, or at least a line that contains the word 'import'.
				code2exec.append(line)
				
			elif self._classPat.search(line):
				# It's a class definition statement.
				code2exec.append(line)

			elif self._defPat.search(line):
				# Add that def, but ignore any code
				while line.endswith("\n"):
					line = line[:-1]
				while not line.rstrip().endswith(":"):
					# Continued line
					try:
						lineNum += numGen.next()
					except StopIteration:
						break
					nextLine = self.GetLine(lineNum).strip()
					line = "%s %s" % (line, nextLine)
				line += " pass"
				code2exec.append(line)

		if code2exec:
			cd = "\n".join(code2exec)
			try:
				exec cd in self._namespaces
			except StandardError, e:
				pass


	### Property definitions start here
	def _getAutoAutoComplete(self):
		try:
			return self._autoAutoComplete
		except AttributeError:
			ret = self._autoAutoComplete = self.Application.getUserSetting("AutoAutoComplete", False)
			return ret
	
	def _setAutoAutoComplete(self, val):
		self._autoAutoComplete = val
		self.Application.setUserSetting("AutoAutoComplete", val)


	def _getAutoAutoCompleteMinLen(self):
		try:
			return self._autoAutoCompleteMinLen
		except AttributeError:
			ret = self._autoAutoCompleteMinLen = self.Application.getUserSetting("AutoAutoCompleteMinLen", 3)
			return ret
	
	def _setAutoAutoCompleteMinLen(self, val):
		self._autoAutoCompleteMinLen = val
		self.Application.setUserSetting("AutoAutoCompleteMinLen", val)


	def _getAutoCompleteList(self):
		return self._autoCompleteList

	def _setAutoCompleteList(self, val):
		if self._constructed():
			self._autoCompleteList = val
		else:
			self._properties["AutoCompleteList"] = val


	def _getAutoIndent(self):
		return self._autoIndent

	def _setAutoIndent(self, val):
		if self._constructed():
			self._autoIndent = val
		else:
			self._properties["AutoIndent"] = val


	def _getBufferedDrawing(self):
		return self._bufferedDrawing

	def _setBufferedDrawing(self, val):
		if self._constructed():
			self._bufferedDrawing = val
			self.SetBufferedDraw(val)
		else:
			self._properties["BufferedDrawing"] = val


	def _getCodeCompletion(self):
		return self._codeCompletion

	def _setCodeCompletion(self, val):
		if self._constructed():
			self._codeCompletion = val
		else:
			self._properties["CodeCompletion"] = val


	def _getColumn(self):
		return self.GetColumn(self.GetCurrentPos())

	def _setColumn(self, val):
		val = max(0, val)
		currPos = self.GetCurrentPos()
		currCol = self.GetColumn(currPos)
		diff = val - currCol
		newPos = currPos + diff
		endOfLinePos = self.GetLineEndPosition(self.LineNumber)
		newPos = min(endOfLinePos, newPos)		
		self.GotoPos(newPos)


	def _getCommentString(self):
		return self._commentString

	def _setCommentString(self, val):
		if self._constructed():
			self._commentString = val
		else:
			self._properties["CommentString"] = val


	def _getEncoding(self):
		return self._encoding

	def _setEncoding(self, val):
		if self._constructed():
			self._encoding = val
		else:
			self._properties["Encoding"] = val


	def _getEOLMode(self):
		return self._eolMode

	def _setEOLMode(self, val):
		if self._constructed():
			if val.lower() == "crlf":
				self.SetEOLMode(stc.STC_EOL_CRLF)
				self.ConvertEOLs(stc.STC_EOL_CRLF)
				self._eolMode = "CRLF"
			elif val.lower() == "lf":
				self.SetEOLMode(stc.STC_EOL_LF)
				self.ConvertEOLs(stc.STC_EOL_LF)
				self._eolMode = "LF"
			elif val.lower() == "cr":
				self.SetEOLMode(stc.STC_EOL_CR)
				self.ConvertEOLs(stc.STC_EOL_CR)
				self._eolMode = "CR"
			else:
				raise ValueError, "EOLMode value must be either 'LFCR', 'LF', or 'CR'"
		else:
			self._properties["EOLMode"] = val


	def _getFileName(self):
		return os.path.split(self._fileName)[1]


	def _getFilePath(self):
		return self._fileName


	def _getFontSize(self):
		return self._fontSize

	def _setFontSize(self, val):
		if self._constructed():
			self._fontSize = val
			self.setDefaultFont(self._fontFace, self._fontSize)
			self.setPyFont(self._fontFace, self._fontSize)
			self.Application.setUserSetting("editor.fontsize", self._fontSize)
		else:
			self._properties["FontSize"] = val


	def _getFontFace(self):
		return self._fontFace

	def _setFontFace(self, val):
		if self._constructed():
			self._fontFace = val
			self.setDefaultFont(self._fontFace, self._fontSize)
			self.setPyFont(self._fontFace, self._fontSize)
			self.Application.setUserSetting("editor.fontface", self._fontFace)
		else:
			self._properties["FontFace"] = val


	def _getHiliteCharsBeyondLimit(self):
		return self._hiliteCharsBeyondLimit

	def _setHiliteCharsBeyondLimit(self, val):
		if self._constructed():
			self._hiliteCharsBeyondLimit = val
		if val:
			self.SetEdgeMode(stc.STC_EDGE_BACKGROUND)
			self.SetEdgeColumn(self.HiliteLimitColumn)

		else:
			self._properties["HiliteCharsBeyondLimit"] = val


	def _getHiliteLimitColumn(self):
		return self._hiliteLimitColumn

	def _setHiliteLimitColumn(self, val):
		if self._constructed():
			self._hiliteLimitColumn = val
			self.SetEdgeColumn(val)
		else:
			self._properties["HiliteLimitColumn"] = val


	def _getLanguage(self):
		return self._language

	def _setLanguage(self, val):
		if self._constructed():
			if val != self._language:
				if val.lower() in LexerDic.keys():
					self._language = val.lower()
				else:
					dabo.errorLog.write(_("Currently only %s are supported") % ", ".join(LexerDic.keys()))
				self.setDefaults()
				self._defaultsSet = True

				# This forces a refresh of the coloring
				self.SyntaxColoring = self.SyntaxColoring
		else:
			self._properties["Language"] = val


	def _getLineNumber(self):
		return self._ZeroBasedLineNumber + 1

	def _setLineNumber(self, val):
		self._ZeroBasedLineNumber = val - 1


	def _getLineCount(self):
		return self.GetLineCount()


	def _getModified(self):
		return self.GetModify()


	def _getReadOnly(self):
		return self.GetReadOnly()
		
	def _setReadOnly(self, val):
		if self._constructed():
			self.SetReadOnly(val)
		else:
			self._properties["ReadOnly"] = val


	def _getSelectionBackColor(self):
		return self._selectionBackColor

	def _setSelectionBackColor(self, val):
		if self._constructed():
			self._selectionBackColor = val
			if isinstance(val, basestring):
				val = dColors.colorTupleFromName(val)
			self.SetSelBackground(1, val)
		else:
			self._properties["SelectionBackColor"] = val


	def _getSelectionEnd(self):
		return self.GetSelectionEnd()

	def _setSelectionEnd(self, val):
		if self._constructed():
			self.SetSelectionEnd(val)
		else:
			self._properties["SelectionEnd"] = val


	def _getSelectionForeColor(self):
		return self._selectionForeColor

	def _setSelectionForeColor(self, val):
		if self._constructed():
			self._selectionForeColor = val
			if isinstance(val, basestring):
				val = dColors.colorTupleFromName(val)
			self.SetSelForeground(1, val)
		else:
			self._properties["SelectionForeColor"] = val


	def _getSelectionPosition(self):
		return self.GetSelection()

	def _setSelectionPosition(self, val):
		if self._constructed():
			self.SetSelection(*val)
		else:
			self._properties["SelectionPosition"] = val


	def _getSelection(self):
		return self.GetSelectedText()


	def _getSelectionStart(self):
		return self.GetSelectionStart()

	def _setSelectionStart(self, val):
		if self._constructed():
			self.SetSelectionStart(val)
		else:
			self._properties["SelectionStart"] = val


	def _getShowCallTips(self):
		return self._showCallTips

	def _setShowCallTips(self, val):
		if self._constructed():
			self._showCallTips = val
		else:
			self._properties["ShowCallTips"] = val


	def _getShowCodeFolding(self):
		return self._codeFolding

	def _setShowCodeFolding(self, val):
		if self._constructed():
			self._codeFolding = val
			self._setCodeFoldingMarginVisibility()
		else:
			self._properties["ShowCodeFolding"] = val


	def _getShowEOL(self):
		return self._showEOL

	def _setShowEOL(self, val):
		if self._constructed():
			self._showEOL = val
			self.SetViewEOL(val)
		else:
			self._properties["ShowEOL"] = val


	def _getShowLineNumbers(self):
		return self._showLineNumbers

	def _setShowLineNumbers(self, val):
		if self._constructed():
			self._showLineNumbers = val
			self._setLineNumberMarginVisibility()
		else:
			self._properties["ShowLineNumbers"] = val


	def _getShowWhiteSpace(self):
		return self._showWhiteSpace

	def _setShowWhiteSpace(self, val):
		if self._constructed():
			self._showWhiteSpace = val
			self.SetViewWhiteSpace(val)
		else:
			self._properties["ShowWhiteSpace"] = val


	def _getSyntaxColoring(self):
		return self._syntaxColoring

	def _setSyntaxColoring(self, val):
		if self._constructed():
			self._syntaxColoring = val
			self.setSyntaxColoring(val)
		else:
			self._properties["SyntaxColoring"] = val


	def _getTabWidth(self):
		return self._tabWidth

	def _setTabWidth(self, val):
		if self._constructed():
			self._tabWidth = val
			self.SetTabWidth(val)
			self.SetIndent(val)
		else:
			self._properties["TabWidth"] = val


	def _getText(self):
		return self.GetText()

	def _setText(self, val):
		self.SetText(val)


	def _getUseAntiAliasing(self):
		return self._useAntiAliasing

	def _setUseAntiAliasing(self, val):
		if self._constructed():
			self._useAntiAliasing = val
			self.SetUseAntiAliasing(val)
		else:
			self._properties["UseAntiAliasing"] = val


	def _getUseBookmarks(self):
		return self._useBookmarks

	def _setUseBookmarks(self, val):
		if self._constructed():
			self._useBookmarks = val
			if val:
				self._bookmarkTimer.start()
			else:
				self._bookmarkTimer.stop()
		else:
			self._properties["UseBookmarks"] = val


	def _getUseStyleTimer(self):
		return self._useStyleTimer

	def _setUseStyleTimer(self, val):
		if self._constructed():
			self._useStyleTimer = val
		else:
			self._properties["UseStyleTimer"] = val


	def _getUseTabs(self):
		return self._useTabs

	def _setUseTabs(self, val):
		if self._constructed():
			self._useTabs = val
			self.SetUseTabs(val)
		else:
			self._properties["UseTabs"] = val


	def _getValue(self):
		return self.Text
		
	def _setValue(self, val):
		if self._constructed():
			if self.Text != val:
				try:
					self.Text = val
				except TypeError, e:
					dabo.errorLog.write(_("Could not set value of %s to %s. Error message: %s")
							% (self._name, val, e))
				self._afterValueChanged()
			self.flushValue()
		else:
			self._properties["Value"] = val

		
	def _getWordWrap(self):
		return self.GetWrapMode()

	def _setWordWrap(self, val):
		self.SetWrapMode(val)


	def _getZeroBasedLineNumber(self):
		return self.GetCurrentLine()

	def _setZeroBasedLineNumber(self, val):
		if self._constructed():
			try:
				# Try coercing to int
				val = int(val)
			except ValueError:
				pass
			self.GotoLine(val)
			self.EnsureCaretVisible()
		else:
			self._properties["_ZeroBasedLineNumber"] = val


	def _getZoomLevel(self):
		return self.GetZoom()

	def _setZoomLevel(self, val):
		self.SetZoom(val)


	AutoAutoComplete = property(_getAutoAutoComplete, _setAutoAutoComplete, None,
			_("Determines if auto-completion pops up without a special trigger key  (bool)"))
			
	AutoAutoCompleteMinLen = property(_getAutoAutoCompleteMinLen, _setAutoAutoCompleteMinLen, None,
			_("""When AutoAutoComplete is True, sets the minimum # of chars required
			before the autocomplete popup appears. Default=3  (int)"""))
			
	AutoCompleteList = property(_getAutoCompleteList, _setAutoCompleteList, None,
			_("""Controls if the user has to press 'Enter/Tab' to accept 
			the AutoComplete entry  (bool)"""))
	
	AutoIndent = property(_getAutoIndent, _setAutoIndent, None,
			_("Controls if a newline adds the previous line's indentation  (bool)"))
	
	BufferedDrawing = property(_getBufferedDrawing, _setBufferedDrawing, None,
			_("Setting to True (default) reduces display flicker  (bool)"))
	
	CodeCompletion = property(_getCodeCompletion, _setCodeCompletion, None,
			_("Determines if code completion is active (default=True)  (bool)"))
	
	Column = property(_getColumn, _setColumn, None,
			_("""Returns the current column position of the cursor in the 
			file  (int)"""))
	
	CommentString = property(_getCommentString, _setCommentString, None,
			_("String used to prefix lines that are commented out  (str)"))
	
	Encoding = property(_getEncoding, _setEncoding, None,
			_("Type of encoding to use. Defaults to the application's default encoding.  (str)"))
	
	EOLMode = property(_getEOLMode, _setEOLMode, None,
			_("End of line characters. Allowed values are 'CRLF', 'LF' and 'CR'. (default=os dependent) (str)"))
	
	FileName = property(_getFileName, None, None,
			_("Name of the file being edited (without path info)  (str)"))
	
	FilePath = property(_getFilePath, None, None,
			_("Full path of the file being edited  (str)"))
	
	FontFace = property(_getFontFace, _setFontFace, None,
			_("Name of the font face used in the editor  (str)"))
	
	FontSize = property(_getFontSize, _setFontSize, None,
			_("Size of the font used in the editor  (int)"))
	
	HiliteCharsBeyondLimit = property(_getHiliteCharsBeyondLimit, _setHiliteCharsBeyondLimit, None,
			_("""When True, characters beyond the column set it 
			self.HiliteLimitColumn are visibly hilited  (bool)"""))
	
	HiliteLimitColumn = property(_getHiliteLimitColumn, _setHiliteLimitColumn, None,
			_("""If self.HiliteCharsBeyondLimit is True, specifies 
			the limiting column  (int)"""))
	
	Language = property(_getLanguage, _setLanguage, None,
			_("Determines which language is used for the syntax coloring  (str)"))
	
	LineNumber = property(_getLineNumber, _setLineNumber, None,
			_("Returns the current line number being edited  (int)"))
	
	LineCount = property(_getLineCount, None, None,
			_("Total number of lines in the document  (int)"))
	
	Modified = property(_getModified, None, None,
			_("Has the content of this editor been modified?  (bool)"))
	
	ReadOnly = property(_getReadOnly, _setReadOnly, None, 
			_("Specifies whether or not the text can be edited. (bool)"))
	
	SelectionBackColor = property(_getSelectionBackColor, _setSelectionBackColor, None,
			_("Background color of selected text. Default=yellow  (str or tuple)"))
	
	SelectionEnd = property(_getSelectionEnd, _setSelectionEnd, None,
			_("Position of the end of the selected text  (int)"))
	
	SelectionForeColor = property(_getSelectionForeColor, _setSelectionForeColor, None,
			_("Forecolor of the selected text. Default=black  (str or tuple)"))
	
	Selection = property(_getSelection, None, None,
			_("Selected text. (read-only) (str)"))
	
	SelectionPosition = property(_getSelectionPosition, _setSelectionPosition, None,
			_("Tuple containing the start/end positions of the selected text.  (2-tuple of int)"))
	
	SelectionStart = property(_getSelectionStart, _setSelectionStart, None,
			_("Position of the start of the selected text  (int)"))
	
	ShowCallTips = property(_getShowCallTips, _setShowCallTips, None,
			_("Determines if call tips are shown (default=True)  (bool)"))
	
	ShowCodeFolding = property(_getShowCodeFolding, _setShowCodeFolding, None,
			_("""Determines if the code folding symbols are displayed 
			in the left margin (default=True)  (bool)"""))
	
	ShowEOL = property(_getShowEOL, _setShowEOL, None,
			_("""Determines if end-of-line markers are visible 
			(default=False)  (bool)"""))
	
	ShowLineNumbers = property(_getShowLineNumbers, _setShowLineNumbers, None,
			_("""Determines if line numbers are shown in the left 
			margin (default=True)  (bool)"""))
	
	ShowWhiteSpace = property(_getShowWhiteSpace, _setShowWhiteSpace, None,
			_("""Determines if white space characters are displayed 
			(default=True)  (bool)"""))
	
	SyntaxColoring = property(_getSyntaxColoring, _setSyntaxColoring, None,
			_("Determines if syntax coloring is used (default=True)  (bool)"))
	
	TabWidth = property(_getTabWidth, _setTabWidth, None,
			_("""Approximate number of spaces taken by each tab character 
			(default=4)  (int)"""))
	
	Text = property(_getText, _setText, None,
			_("Current contents of the editor  (str)"))
	
	UseAntiAliasing = property(_getUseAntiAliasing, _setUseAntiAliasing, None,
			_("Controls whether fonts are anti-aliased (default=True)  (bool)"))
	
	UseBookmarks = property(_getUseBookmarks, _setUseBookmarks, None,
			_("Are we tracking bookmarks in the editor? Default=False  (bool)"))
	
	UseStyleTimer = property(_getUseStyleTimer, _setUseStyleTimer, None,
			_("""Syntax coloring can slow down sometimes. Set this to 
			True to improve performance.  (bool)"""))
	
	UseTabs = property(_getUseTabs, _setUseTabs, None,
			_("""Indentation will only use space characters if useTabs 
			is False; if True, it will use a combination of tabs and 
			spaces (default=True)  (bool)"""))
	
	Value = property(_getValue, _setValue, None,
		_("""Specifies the current contents of the editor.  (basestring)"""))
				
	WordWrap = property(_getWordWrap, _setWordWrap, None,
			_("""Controls whether text lines that are wider than the window
			are soft-wrapped or clipped. (bool)"""))
	
	_ZeroBasedLineNumber = property(_getZeroBasedLineNumber, _setZeroBasedLineNumber, None,
			_("This is the underlying property that handles the wxPython zero-based line numbering. It's equal to LineNumber-1  (int)"))

	ZoomLevel = property(_getZoomLevel, _setZoomLevel, None,
			_("Point increase/decrease from normal viewing size  (int)"))
	

	
class _dEditor_test(dEditor):
	def afterInit(self):
		self.Language = "Python"

if __name__ == '__main__':
	import test
	test.Test().runTest(_dEditor_test)