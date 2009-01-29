# -*- coding: utf-8 -*-
import __builtin__
import time
import wx
import wx.stc as stc
import wx.py
from wx.py import pseudo
import dabo
import dabo.dEvents as dEvents
from dabo.dLocalize import _
from dSplitForm import dSplitForm
from dabo.ui import makeDynamicProperty
from dPemMixin import dPemMixin

dabo.ui.loadUI("wx")
from dabo.ui import dKeys


class _LookupPanel(dabo.ui.dPanel):
	"""Used for the command history search"""
	def afterInit(self):
		self._history = None
		self._displayedHistory = None
		self.currentSearch = ""
		self.needRefilter = False
		self.lblSearch = dabo.ui.dLabel(self)
		self.lstMatch = dabo.ui.dListBox(self, ValueMode="string", Choices=[],
				OnMouseLeftDoubleClick=self.selectCmd, OnKeyChar=self.onListKey)
		self.Sizer = dabo.ui.dSizer("v", DefaultBorder=4)
		self.Sizer.append(self.lblSearch, halign="center")
		self.Sizer.append(self.lstMatch, "x", 1)
		self.Width = 400
		self.layout()


	def clear(self):
		"""Reset to original state."""
		self.ok = False
		self.currentSearch = self.lblSearch.Caption = ""
		self.refilter()


	def onListKey(self, evt):
		"""Process keypresses in the command list control"""
		kc = evt.keyCode
		char = evt.keyChar
		if kc in (dKeys.key_Return, dKeys.key_Numpad_enter):
			self.closeDialog(True)
			return
		elif kc == dKeys.key_Escape:
			self.closeDialog(False)
		if kc in dKeys.arrowKeys.values() or char is None:
			#ignore
			return
		if kc == dKeys.key_Back:
			self.currentSearch = self.currentSearch[:-1]
		else:
			self.currentSearch += char
		self.lblSearch.Caption = self.currentSearch
		self.layout()
		self.needRefilter = True
		evt.stop()	


	def closeDialog(self, ok):
		"""Hide the dialog, and set the ok/cancel flag"""
		self.ok = ok
		self.Form.hide()


	def getCmd(self):
		return self.lstMatch.Value


	def selectCmd(self, evt):
		self.closeDialog(True)


	def onIdle(self, evt):
		"""For performance, don't filter on every keypress. Wait until idle."""
		if self.needRefilter:
			self.needRefilter = False
			self.refilter()


	def refilter(self):
		"""Display only those commands that contain the search string"""
		self.DisplayedHistory = self.History.filter("cmd", self.currentSearch, "contains")
		sel = self.lstMatch.Value
		self.lstMatch.Choices = [rec["cmd"] for rec in self.DisplayedHistory]
		if sel:
			try:
				self.lstMatch.Value = sel
			except ValueError:
				self._selectFirst()
		else:
			self._selectFirst()


	def _selectFirst(self):
		"""Select the first item in the list, if available."""
		if len(self.lstMatch.Choices):
			self.lstMatch.PositionValue = 0


	def _getHistory(self):
		if self._history is None:
			self._history = dabo.db.dDataSet()
		return self._history

	def _setHistory(self, val):
		if self._constructed():
			self._history = self._displayedHistory = val
			try:
				self.lstMatch.Choices = [rec["cmd"] for rec in self.DisplayedHistory]
				self._selectFirst()
			except AttributeError:
				pass
		else:
			self._properties["History"] = val


	def _getDisplayedHistory(self):
		if self._displayedHistory is None:
			self._displayedHistory = self.History
		return self._displayedHistory

	def _setDisplayedHistory(self, val):
		if self._constructed():
			self._displayedHistory = val
		else:
			self._properties["DisplayedHistory"] = val


	DisplayedHistory = property(_getDisplayedHistory, _setDisplayedHistory, None,
			_("Filtered copy of the History  (dDataSet)"))

	History = property(_getHistory, _setHistory, None,
			_("Dataset containing the command history  (dDataSet)"))



class _Shell(dPemMixin, wx.py.shell.Shell):
	def __init__(self, parent, properties=None, attProperties=None,
				*args, **kwargs):
		self._isConstructed = False
		self._fontSize = 10
		self._fontFace = ""
		self._baseClass = _Shell
		preClass = wx.py.shell.Shell
		dPemMixin.__init__(self, preClass, parent, properties, attProperties, *args, **kwargs)
	
	
	def _afterInit(self):
		super(_Shell, self)._afterInit()
		# Set some font defaults
		self.plat = self.Application.Platform
		if self.plat == "GTK":
			self.FontFace = "Monospace"
			self.FontSize = 10
		elif self.plat == "Mac":
			self.FontFace = "Monaco"
			self.FontSize = 12
		elif self.plat == "Win":
			self.FontFace = "Courier New"
			self.FontSize = 10	


	def processLine(self):
		"""This is part of the underlying class. We need to add the command that 
		gets processed into our internal stack.
		"""
		edt = self.CanEdit()
		super(_Shell, self).processLine()
		if edt:
			# push the latest command into the stack
			self.Form.addToHistory(self.history[0])
		
		
	def setDefaultFont(self, fontFace, fontSize):
		# Global default styles for all languages
		self.StyleSetSpec(stc.STC_STYLE_DEFAULT, "face:%s,size:%d" % (fontFace, fontSize))
		self.StyleClearAll()  # Reset all to be like the default

		# Global default styles for all languages
		self.StyleSetSpec(stc.STC_STYLE_DEFAULT,
				"face:%s,size:%d" % (self._fontFace, fontSize))
		self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,
				"back:#C0C0C0,face:%s,size:%d" % (self._fontFace, 8))
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
	

	def OnKeyDown(self, evt):
		"""Override on the Mac, as the navigation defaults are different than on Win/Lin"""
		if self.plat != "Mac":
			return super(_Shell, self).OnKeyDown(evt)
		key = evt.GetKeyCode()
		# If the auto-complete window is up let it do its thing.
		if self.AutoCompActive():
			evt.Skip()
			return
		
		# Prevent modification of previously submitted
		# commands/responses.
		controlDown = evt.ControlDown()
		altDown = evt.AltDown()
		shiftDown = evt.ShiftDown()
		cmdDown = evt.CmdDown()
		currpos = self.GetCurrentPos()
		endpos = self.GetTextLength()
		selecting = self.GetSelectionStart() != self.GetSelectionEnd()
		if cmdDown and (key == wx.WXK_LEFT):
			# Equivalent to Home
			home = self.promptPosEnd
			print home
			if currpos > home:
				self.SetCurrentPos(home)
				if not selecting and not shiftDown:
					self.SetAnchor(home)
					self.EnsureCaretVisible()
			return
		if cmdDown and (key == wx.WXK_RIGHT):
			# Equivalent to End
			linepos = self.GetLineEndPosition(self.GetCurrentLine())
			if shiftDown:
				start = currpos
			else:
				start = linepos
			self.SetSelection(start, linepos)
			return
		elif cmdDown and (key == wx.WXK_UP):
			# Equivalent to Ctrl-Home
			if shiftDown:
				end = currpos
			else:
				end = 0
			self.SetSelection(0, end)
			return
		elif cmdDown and (key == wx.WXK_DOWN):
			# Equivalent to Ctrl-End
			if shiftDown:
				start = currpos
			else:
				start = endpos
			self.SetSelection(start, endpos)
			return
		return super(_Shell, self).OnKeyDown(evt)


	def _getFontSize(self):
		return self._fontSize

	def _setFontSize(self, val):
		if self._constructed():
			self._fontSize = val
			self.setDefaultFont(self._fontFace, self._fontSize)
			self.setPyFont(self._fontFace, self._fontSize)
			self.Application.setUserSetting("shell.fontsize", self._fontSize)
		else:
			self._properties["FontSize"] = val


	def _getFontFace(self):
		return self._fontFace

	def _setFontFace(self, val):
		if self._constructed():
			self._fontFace = val
			self.setDefaultFont(self._fontFace, self._fontSize)
			self.setPyFont(self._fontFace, self._fontSize)
			self.Application.setUserSetting("shell.fontface", self._fontFace)
		else:
			self._properties["FontFace"] = val


	FontFace = property(_getFontFace, _setFontFace, None,
			_("Name of the font face used in the shell  (str)"))
	
	FontSize = property(_getFontSize, _setFontSize, None,
			_("Size of the font used in the shell  (int)"))



class dShell(dSplitForm):
	def _onDestroy(self, evt):
		self._clearOldHistory()
		__builtin__.raw_input = self._oldRawInput

	
	def _beforeInit(self, pre):
		# Set the sash
		self._sashPct = 0.6
		super(dShell, self)._beforeInit(pre)
		

	def _afterInit(self):
		super(dShell, self)._afterInit()
		self.cmdHistKey = self.PreferenceManager.command_history
		self._historyPanel = None
		self._lastCmd = None

		# PyShell sets the raw_input function to a function of PyShell,
		# but doesn't set it back on destroy, resulting in errors later
		# on if something other than PyShell asks for raw_input (pdb, for
		# example).
		self._oldRawInput = __builtin__.raw_input
		self.bindEvent(dabo.dEvents.Destroy, self._onDestroy)

		splt = self.Splitter
		splt.MinimumPanelSize = 80
		splt.unbindEvent()
		self.Orientation = "H"
		self.unsplit()
		self._splitState = False
		self.MainSplitter.bindEvent(dEvents.SashDoubleClick, 
				self.sashDoubleClick)
		self.MainSplitter.bindEvent(dEvents.SashPositionChanged, 
				self.sashPosChanged)
		
		cp = self.CmdPanel = self.Panel1
		op = self.OutPanel = self.Panel2
		cp.unbindEvent(dEvents.ContextMenu)
		op.unbindEvent(dEvents.ContextMenu)
		
		cp.Sizer = dabo.ui.dSizer()
		op.Sizer = dabo.ui.dSizer()
		self.shell = _Shell(self.CmdPanel)
		# Configure the shell's behavior
		self.shell.AutoCompSetIgnoreCase(True)
		self.shell.AutoCompSetAutoHide(False)	 ## don't hide when the typed string no longer matches
		self.shell.AutoCompStops(" ")  ## characters that will stop the autocomplete
		self.shell.AutoCompSetFillUps(".(")
		# This lets you go all the way back to the '.' without losing the AutoComplete
		self.shell.AutoCompSetCancelAtStart(False)
		
		cp.Sizer.append1x(self.shell)
		self.shell.Bind(wx.EVT_RIGHT_UP, self.shellRight)
		# Bring up history search
		self.bindKey("Ctrl+R", self.onHistoryPop)
		
		# Restore the history
		self.restoreHistory()

		# create the output control
		outControl = dabo.ui.dEditBox(op, RegID="edtOut", 
				ReadOnly=True)
		op.Sizer.append1x(outControl)
		outControl.bindEvent(dEvents.MouseRightDown, 
				self.outputRightDown)
		
		self._stdOut = self.shell.interp.stdout
		self._stdErr = self.shell.interp.stderr
		self._pseudoOut = pseudo.PseudoFileOut(write=self.appendOut)
		self._pseudoErr = pseudo.PseudoFileOut(write=self.appendOut)
		self.SplitState = True
		
		# Make 'self' refer to the calling form, or this form if no calling form.
		if self.Parent is None:
			ns = self
		else:
			ns = self.Parent
		self.shell.interp.locals['self'] = ns

		self.Caption = _("dShell: self is %s") % ns.Name
		self.setStatusText(_("Use this shell to interact with the runtime environment"))
		self.fillMenu()
		self.shell.SetFocus()
		
	
	def appendOut(self, tx):
		ed = self.edtOut
		ed.Value += tx
		endpos = ed.GetLastPosition()
		# Either of these commands should scroll the edit box
		# to the bottom, but neither do (at least on OS X) when 
		# called directly or via callAfter().
		dabo.ui.callAfter(ed.ShowPosition, endpos)
		dabo.ui.callAfter(ed.SetSelection, endpos, endpos)


	def addToHistory(self, cmd):
		chk = self.cmdHistKey
		if cmd == self._lastCmd:
			# Don't add again
			return
		# Delete any old instances of this command
		chk.deleteByValue(cmd)
		self._lastCmd = cmd
		stamp = "%s" % int(round(time.time() * 100, 0))
		self.cmdHistKey.setValue(stamp, cmd)


	def _loadHistory(self):
		ck = self.cmdHistKey
		cmds = []
		for k in ck.getPrefKeys():
			cmds.append({"stamp": k, "cmd": ck.get(k)})
		dsu = dabo.db.dDataSet(cmds)
		if dsu:
			ds = dsu.sort("stamp", "desc")
			return ds
		else:
			return dsu


	def onHistoryPop(self, evt):
		"""Let the user type in part of a command, and retrieve the matching commands
		from their history.
		"""
		ds = self._loadHistory()
		hp = self._HistoryPanel
		hp.History = ds
		fp = self.FloatingPanel
		# We want it centered, so set Owner to None
		fp.Owner = None
		hp.clear()
		fp.show()
		if hp.ok:
			cmd = hp.getCmd()
			if cmd:
				pos = self.shell.history.index(cmd)
				self.shell.replaceFromHistory(pos - self.shell.historyIndex)


	def restoreHistory(self):
		"""Get the stored history from previous sessions, and set the shell's
		internal command history list to it.
		"""
		ds = self._loadHistory()
		self.shell.history = [rec["cmd"] for rec in ds]


	def _clearOldHistory(self):
		"""For performance reasons, only save up to 500 commands."""
		numToSave = 500
		ck = self.cmdHistKey
		ds = self._loadHistory()
		if len(ds) <= numToSave:
			return
		cutoff = ds[numToSave]["stamp"]
		bad = []
		for rec in ds:
			if rec["stamp"] <= cutoff:
				bad.append(rec["stamp"])
		for bs in bad:
			ck.deletePref(bs)

		
	def outputRightDown(self, evt):
		pop = dabo.ui.dMenu()
		pop.append(_("Clear"), OnHit=self.onClearOutput)
		if self.edtOut.SelectionLength:
			pop.append(_("Copy"), OnHit=self.Application.onEditCopy)
		self.showContextMenu(pop)
		evt.stop()
	
	
	def onClearOutput(self, evt):
		self.edtOut.Value = ""
	
	
	def shellRight(self, evt):
		pop = dabo.ui.dMenu()
		if self.SplitState:
			pmpt = _("Unsplit")
		else:
			pmpt = _("Split")
		pop.append(pmpt, OnHit=self.onSplitContext)
		self.showContextMenu(pop)
		evt.StopPropagation()
		

	def onSplitContext(self, evt):
		self.SplitState = (evt.EventObject.Caption == _("Split"))
		evt.stop()
		
		
	def onResize(self, evt):
		self.SashPosition = self._sashPct * self.Height
	

	def sashDoubleClick(self, evt):
		# We don't want the window to unsplit
		evt.stop()
		
		
	def sashPosChanged(self, evt):
		self._sashPct = float(self.SashPosition) / self.Height
		
		
	def fillMenu(self):
		viewMenu = self.MenuBar.getMenu("base_view")
		if viewMenu.Children:
			viewMenu.appendSeparator()
		viewMenu.append(_("Zoom &In"), HotKey="Ctrl+=", OnHit=self.onViewZoomIn,
				ItemID="view_zoomin",
				bmp="zoomIn", help=_("Zoom In"))
		viewMenu.append(_("&Normal Zoom"), HotKey="Ctrl+/", OnHit=self.onViewZoomNormal, 
				ItemID="view_zoomnormal",
				bmp="zoomNormal", help=_("Normal Zoom"))
		viewMenu.append(_("Zoom &Out"), HotKey="Ctrl+-", OnHit=self.onViewZoomOut, 
				ItemID="view_zoomout",
				bmp="zoomOut", help=_("Zoom Out"))
		editMenu = self.MenuBar.getMenu("base_edit")
		if editMenu.Children:
			editMenu.appendSeparator()
		editMenu.append(_("Clear O&utput"), HotKey="Ctrl+Back",
				ItemID="edit_clearoutput",
				OnHit=self.onClearOutput, help=_("Clear Output Window"))
		
		
	def onViewZoomIn(self, evt):
		self.shell.SetZoom(self.shell.GetZoom()+1)


	def onViewZoomNormal(self, evt):
		self.shell.SetZoom(0)


	def onViewZoomOut(self, evt):
		self.shell.SetZoom(self.shell.GetZoom()-1)


	def _getFontSize(self):
		return self.shell.FontSize

	def _setFontSize(self, val):
		if self._constructed():
			self.shell.FontSize = val
		else:
			self._properties["FontSize"] = val


	def _getFontFace(self):
		return self.shell.FontFace

	def _setFontFace(self, val):
		if self._constructed():
			self.shell.FontFace = val
		else:
			self._properties["FontFace"] = val


	def _getHistoryPanel(self):
		fp = self.FloatingPanel
		try:
			create = self._historyPanel is None
		except AttributeError:
			create = True
		if create:
			fp.clear()
			pnl = self._historyPanel = _LookupPanel(fp)
			pnl.Height = max(200, self.Height-100)
			fp.Sizer.append(pnl)
			fp.fitToSizer()
		return self._historyPanel


	def _getSplitState(self):
		return self._splitState

	def _setSplitState(self, val):
		if self._splitState != val:
			self._splitState = val
			if val:
				self.split()
				self.shell.interp.stdout = self._pseudoOut
				self.shell.interp.stderr = self._pseudoErr
			else:
				self.unsplit()
				self.shell.interp.stdout = self._stdOut
				self.shell.interp.stderr = self._stdErr
			

	FontFace = property(_getFontFace, _setFontFace, None,
			_("Name of the font face used in the shell  (str)"))
	
	FontSize = property(_getFontSize, _setFontSize, None,
			_("Size of the font used in the shell  (int)"))

	_HistoryPanel = property(_getHistoryPanel, None, None,
			_("Popup to display the command history  (read-only) (dDialog)"))

	SplitState = property(_getSplitState, _setSplitState, None,
			_("""Controls whether the output is in a separate pane (default) 
			or intermixed with the commands.  (bool)"""))
			
			
	DynamicSplitState = makeDynamicProperty(SplitState)
	
		

def main():
	app = dabo.dApp(BasePrefKey="dabo.ui.dShell")
	app.MainFormClass = dShell
	app.setup()
	app.start()

if __name__ == "__main__":
	main()
