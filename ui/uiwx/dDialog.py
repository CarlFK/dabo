# -*- coding: utf-8 -*-
import wx
import dabo
if __name__ == "__main__":
	dabo.ui.loadUI("wx")
import dabo.dEvents as dEvents
import dabo.dConstants as kons
from dabo.dLocalize import _
import dFormMixin as fm
from dabo.ui import makeDynamicProperty


class dDialog(fm.dFormMixin, wx.Dialog):
	"""Creates a dialog, which is a lightweight form.

	Dialogs are like forms, but typically are modal and are requesting a very
	specific piece of information from the user, and/or offering specific
	information to the user.
	"""
	def __init__(self, parent=None, properties=None, *args, **kwargs):
		self._baseClass = dDialog
		self._modal = True
		self._centered = True
		self._fit = True

		defaultStyle = wx.DEFAULT_DIALOG_STYLE
		try:
			kwargs["style"] = kwargs["style"] | defaultStyle
		except KeyError:
			kwargs["style"] = defaultStyle

		preClass = wx.PreDialog
		fm.dFormMixin.__init__(self, preClass, parent, properties=properties, 
				*args, **kwargs)

		# Hook method, so that we add the buttons last
		self._addControls()

		# Needed starting with wx 2.7, for the first control to have the focus:
		self.setFocus()


	def _afterInit(self):
		self.MenuBarClass = None
		self.Sizer = dabo.ui.dSizer("V")
		super(dDialog, self)._afterInit()
		self.bindKey("esc", self._onEscape)


	def Show(self, show=True, *args, **kwargs):
		self._gtk_show_fix(show)
		wx.Dialog.Show(self, show, *args, **kwargs)

	def ShowModal(self, *args, **kwargs):
		self._gtk_show_fix(True)
		wx.Dialog.ShowModal(self, *args, **kwargs)


	def showModal(self):
		"""Show the dialog modally."""
		## pkm: We had to override this, because the default in dPemMixin doesn't 
		##      actually result in a modal dialog.
		self.Modal = True
		self.show()


	def showModeless(self):
		"""Show the dialog non-modally."""
		self.Modal = False
		self.show()


	def _afterShow(self):
		if self.AutoSize:
			self.Fit()
		if self.Centered:
			self.Centre()


	def show(self):
		# Call _afterShow() once immediately, and then once after the dialog is visible, which
		# will correct minor mistakes such as the height of wordwrapped labels not being 
		# accounted for. If we only called it after the dialog was already shown, then we
		# risk the dialog being too jumpy.
		self._afterShow()
		dabo.ui.callAfter(self._afterShow)
		retVals = {wx.ID_OK : kons.DLG_OK, 
				wx.ID_CANCEL : kons.DLG_CANCEL}
		if self.Modal:
			ret = self.ShowModal()
		else:
			ret = self.Show(True)
		return retVals.get(ret)
		

	def _onEscape(self, evt):
		evt.stop()
		if self.ReleaseOnEscape:
			self.release()
			self.Close()


	def _addControls(self):
		"""Any controls that need to be added to the dialog 
		can be added in this method in framework classes, or
		in addControls() in instances.
		"""
		self.addControls()
	

	def addControls(self):
		"""Add your custom controls to the dialog.

		This is a hook, called at the appropriate time by the framework.
		"""
		pass


	def release(self):
		""" Need to augment this to make sure the dialog
		is removed from the app's forms collection.
		"""
		if self.Application is not None:
			try:
				self.Application.uiForms.remove(self)
			except: pass
		super(dDialog, self).release()
	
	
	def _setEscapeBehavior(self):
		"""Allow subclasses to respond to changes in the ReleaseOnEscape property."""
		pass
		

	def _getAutoSize(self):
		return self._fit

	def _setAutoSize(self, val):
		self._fit = val


	def _getCaption(self):
		return self.GetTitle()

	def _setCaption(self, val):
		if self._constructed():
			self.SetTitle(val)
		else:
			self._properties["Caption"] = val


	def _getCentered(self):
		return self._centered

	def _setCentered(self, val):
		self._centered = val


	def _getModal(self):
		return self._modal

	def _setModal(self, val):
		self._modal = val
	

	def _getReleaseOnEscape(self):
		try:
			val = self._releaseOnEscape
		except AttributeError:
			val = True
		return val

	def _setReleaseOnEscape(self, val):
		self._releaseOnEscape = bool(val)
		self._setEscapeBehavior()


	def _getShowStat(self):
		# Dialogs cannot have status bars.
		return False
	_showStatusBar	= property(_getShowStat)


	AutoSize = property(_getAutoSize, _setAutoSize, None,
			"When True, the dialog resizes to fit the added controls.  (bool)")

	Caption = property(_getCaption, _setCaption, None,
			"The text that appears in the dialog's title bar  (str)" )

	Centered = property(_getCentered, _setCentered, None,
			"Determines if the dialog is displayed centered on the screen.  (bool)")

	Modal = property(_getModal, _setModal, None,
			"Determines if the dialog is shown modal (default) or modeless.  (bool)")
	
	ReleaseOnEscape = property(_getReleaseOnEscape, _setReleaseOnEscape, None,
			"Determines if the <Esc> key releases the dialog. Default=True.  (bool)")


	DynamicAutoSize = makeDynamicProperty(AutoSize)
	DynamicCaption = makeDynamicProperty(Caption)
	DynamicCentered = makeDynamicProperty(Centered)



class dOkCancelDialog(dDialog):
	"""Creates a dialog with OK/Cancel buttons and associated functionality.

	Add your custom controls in the addControls() hook method, and respond to
	the pressing of the Ok and Cancel buttons in the onOK() and onCancel() 
	event handlers. The default behavior in both cases is just to close the
	form, and you can query the Accepted property to find out if the user 
	pressed "OK" or not.
	"""
	def __init__(self, parent=None, properties=None, *args, **kwargs):
		super(dOkCancelDialog, self).__init__(parent=parent, properties=properties, *args, **kwargs)
		self._baseClass = dOkCancelDialog
		self._accepted = False


	def _addControls(self):
		# Set some default Sizer properties (user can easily override):
		sz = self.Sizer
		sz.DefaultBorder = 20
		sz.DefaultBorderLeft = sz.DefaultBorderRight = True
		sz.append((0, sz.DefaultBorder))

		# Define Ok/Cancel, and tell wx that we want stock buttons.
		# We are creating them now, so that the user code can access them if needed.
		self.btnOK = dabo.ui.dButton(self, id=wx.ID_OK, DefaultButton=True)
		self.btnOK.bindEvent(dEvents.Hit, self.onOK)
		self.btnCancel = dabo.ui.dButton(self, id=wx.ID_CANCEL, CancelButton=True)
		self.btnCancel.bindEvent(dEvents.Hit, self.onCancel)
		
		# Put the buttons in a StdDialogButtonSizer, so they get positioned/sized
		# per the native platform conventions:
		buttonSizer = wx.StdDialogButtonSizer()
		buttonSizer.AddButton(self.btnOK)
		buttonSizer.AddButton(self.btnCancel)
		buttonSizer.Realize()
	
		self._btnSizer = bs = dabo.ui.dSizer("v")
		bs.append((0, sz.DefaultBorder/2))
		bs.append(buttonSizer, "x")
		bs.append((0, sz.DefaultBorder))

		# Wx rearranges the order of the buttons per platform conventions, but
		# doesn't rearrange the tab order for us. So, we do it manually:
		buttons = []
		for child in buttonSizer.GetChildren():
			win = child.GetWindow()
			if win is not None:
				buttons.append(win)
		buttons[1].MoveAfterInTabOrder(buttons[0])

		# Let the user add their controls
		super(dOkCancelDialog, self)._addControls()

		# Just in case user changed Self.Sizer, update our reference:
		sz = self.Sizer

		if self.ButtonSizerPosition is None:
			# User code didn't add it, so we must.
			sz.append(bs, "x")
		
		self.layout()

	
	def addControls(self):
		"""Use this method to add controls to the dialog. 

		The OK/Cancel	buttons will be added after this method runs, so that they 
		appear at the bottom of the dialog.
		"""
		pass
	
	
	def _setEscapeBehavior(self):
		"""Bind/unbind the Cancel button to the escape key."""
		try:
			self.btnCancel.CancelButton = self.ReleaseOnEscape
			if self.ReleaseOnEscape:
				self.SetEscapeId(wx.ID_ANY)
			else:
				self.SetEscapeId(wx.ID_NONE)
		except AttributeError:
			# Button hasn't been added yet
			dabo.ui.callAfter(self._setEscapeBehavior)

	
	def addControlSequence(self, seq):
		"""This takes a sequence of 3-tuples or 3-lists, and adds controls 
		to the dialog as a grid of labels and data controls. The first element of
		the list/tuple is the prompt, the second is the data type, and the third
		is the RegID used to retrieve the entered value.
		"""
		gs = dabo.ui.dGridSizer(HGap=5, VGap=8, MaxCols=2)
		for prmpt, typ, rid in seq:
			chc = None
			gs.append(dabo.ui.dLabel(self, Caption=prmpt), halign="right")
			if typ in (int, long):
				cls = dabo.ui.dSpinner
			elif typ is bool:
				cls = dabo.ui.dCheckBox
			elif isinstance(typ, list):
				cls = dabo.ui.dDropdownList
				chc = typ
			else:
				cls = dabo.ui.dTextBox
			ctl = cls(self, RegID=rid)
			gs.append(ctl)
			if chc:
				ctl.Choices = chc
		gs.setColExpand(True, 1)
		self.Sizer.insert(self.LastPositionInSizer, gs, "x")
		self.layout()
		
		
	def onOK(self, evt):
		self.Accepted = True
		self.EndModal(kons.DLG_OK)

	def onCancel(self, evt):
		self.Accepted = False
		self.EndModal(kons.DLG_CANCEL)


	def _getAccepted(self):
		return self._accepted		

	def _setAccepted(self, val):
		self._accepted = val
	
	
	def _getButtonSizer(self):
		return getattr(self, "_btnSizer", None)


	def _getButtonSizerPosition(self):
		return self.ButtonSizer.getPositionInSizer()


	def _getCancelButton(self):
		return self.btnCancel


	def _getOKButton(self):
		return self.btnOK
		

	Accepted = property(_getAccepted, _setAccepted, None,
			_("Specifies whether the user accepted the dialog, or canceled.  (bool)"))

	ButtonSizer = property(_getButtonSizer, None, None,
			_("Returns a reference to the sizer controlling the Ok/Cancel buttons.  (dSizer)"))

	ButtonSizerPosition = property(_getButtonSizerPosition, None, None,
			_("""Returns the position of the Ok/Cancel buttons in the sizer.  (int)"""))

	CancelButton = property(_getCancelButton, None, None,
			_("Reference to the Cancel button on the form  (dButton)."))
	
	LastPositionInSizer = ButtonSizerPosition   ## backwards compatibility

	OKButton = property(_getOKButton, None, None,
			_("Reference to the OK button on the form  (dButton)."))
	
	


if __name__ == "__main__":
	import test
	test.Test().runTest(dDialog)
	test.Test().runTest(dOkCancelDialog)
