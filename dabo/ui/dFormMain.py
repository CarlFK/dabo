# -*- coding: utf-8 -*-
import time
import wx
import dabo
from dabo.ui.dFormMixin import dFormMixin


class dFormMainBase(dFormMixin):
    """This is the main top-level form for the application."""
    def __init__(self, preClass, parent=None, properties=None, *args, **kwargs):
        print("dFormMainBase INIT")
        super(dFormMainBase, self).__init__(preClass, parent, properties,
                *args, **kwargs)
        print("dFormMainBase SUPER called")


    def _beforeClose(self, evt=None):
        # In wxPython 4.x, a 'dead object' is now a logical False.
        forms2close = [frm for frm in self.Application.uiForms
                if frm and frm is not self]
        while forms2close:
            frm = forms2close[0]
            # This will allow forms to veto closing (i.e., user doesn't
            # want to save pending changes).
            if frm.close() == False:
                # The form stopped the closing process. The user
                # must deal with this form (save changes, etc.)
                # before the app can exit.
                frm.bringToFront()
                return False
            else:
                forms2close.remove(frm)


class dFormMain(dFormMainBase, wx.Frame):
    def __init__(self, parent=None, properties=None, *args, **kwargs):
        print("dFormMain INIT")
        self._baseClass = dFormMain

        if dabo.MDI:
            # Hack this into an MDI Parent:
            dFormMain.__bases__ = (wx.MDIParentFrame, dFormMainBase)
            self._mdi = True
        else:
            # This is a normal SDI form:
            dFormMain.__bases__ = (wx.Frame, dFormMainBase)
            self._mdi = False
        ## (Note that it is necessary to run the above block each time, because
        ##  we are modifying the dFormMain class definition globally.)

        super(dFormMain, self).__init__(parent, properties, *args, **kwargs)
        print("dFormMain SUPER called")


if __name__ == "__main__":
    from dabo.ui import test
    test.Test().runTest(dFormMain)
