# -*- coding: utf-8 -*-
import copy
import datetime

import decimal
Decimal = decimal.Decimal

import locale
import sys
import os
######################################################
# Very first thing: check for required libraries:
_failedLibs = []
for lib in ("reportlab", "PIL"):
	try:
		__import__(lib)
	except ImportError:
		_failedLibs.append(lib)

if len(_failedLibs) > 0:
	msg = """
The Dabo Report Writer has dependencies on libraries you
don't appear to have installed. You still need:

	%s

PIL is the Python Imaging Library available from
http://www.pythonware.com/products/pil

reportlab is the ReportLab toolkit available from
http://www.reportlab.org

If you are on a Debian Linux system, just issue:
sudo apt-get install python-reportlab
sudo apt-get install python-imaging

	""" % "\n\t".join(_failedLibs)

	raise ImportError(msg)
del(_failedLibs)
#######################################################

import cStringIO
import reportlab.pdfgen.canvas as canvas
import reportlab.graphics.shapes as shapes
import reportlab.lib.pagesizes as pagesizes
import reportlab.lib.units as units
import reportlab.lib.styles as styles
import reportlab.platypus as platypus
#import reportlab.lib.colors as colors
from dabo.lib.xmltodict import xmltodict
from dabo.lib.xmltodict import dicttoxml
from dabo.dLocalize import _
from dabo.lib.caselessDict import CaselessDict
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage
import reportUtils

# The below block tried to use the experimental para.Paragraph which
# handles more html tags, including hyperlinks. However, I couldn't 
# get it to work... among other things, para doesn't accept None as
# the availableHeight argument to wrap().
if False:
	try:
		from reportlab.platypus.para import Paragraph as ParaClass
	except ImportError:
		print "No Para class, using Paragraph."
		ParaClass = platypus.Paragraph
else:
	ParaClass = platypus.Paragraph


def toPropDict(dataType, default, doc):
	return {"dataType": dataType, "default": default, "doc": doc}


class ReportObjectCollection(list):
	"""Abstract ordered list of things like variables, groups, and band objects."""

	def __init__(self, parent=None, *args, **kwargs):
		super(ReportObjectCollection, self).__init__(*args, **kwargs)
		self.parent = parent

	def addObject(self, cls):
		obj = cls(self)
		self.append(obj)
		return obj

	def getPropDoc(self, prop):
		return ""

	def _getDesProps(self):
		return {}

	DesignerProps = property(_getDesProps, None, None,
		_("""Returns a dict of editable properties for the control, with the 
		prop names as the keys, and the value for each another dict, 
		containing the following keys: 'type', which controls how to display
		and edit the property, and 'readonly', which will prevent editing
		when True. (dict)""") )


class Variables(ReportObjectCollection): pass
class Groups(ReportObjectCollection): pass
class Objects(ReportObjectCollection): pass


class ReportObject(CaselessDict):
	"""Abstract report object, such as a drawable object, a variable, or a group."""
	def __init__(self, parent=None, *args, **kwargs):
		super(ReportObject, self).__init__(*args, **kwargs)
		self.parent = parent
		self.initAvailableProps()
		self.insertRequiredElements()

	def __getattr__(self, att):
		rw = self.Report.reportWriter

		# 1) Try mapping the requested attribute to the reportWriter. This will handle
		#    things like 'self.Application'.
		try:
			return getattr(rw, att)
		except AttributeError:
			pass

		# 2) Try mapping to a variable (self.ord_amount -> self.Variables["ord_amount"])
		if self.Variables.has_key(att):
			return self.Variables.get(att)

		# 3) Try mapping to a field in the dataset (self.ordid -> self.Record["ordid"])
		if self.Record.has_key(att):
			return self.Record.get(att)

		raise AttributeError("Can't get attribute '%s'." % att)


	def initAvailableProps(self):
		self.AvailableProps["Comment"] = toPropDict(str, "", 
				"""You can add a comment here, the report will ignore it.""")

	def insertRequiredElements(self):
		"""Insert any missing required elements into the object."""
		pass

	def addElement(self, cls):
		"""Add a new element, replacing existing one of same name."""
		obj = cls(self)
		self[obj.__class__.__name__] = obj
		return obj

	def addObject(self, cls, collectionClass=Objects):
		obj = cls(self)
		collectionName = Objects.__name__
		objects = self.get(collectionName, collectionClass(self))
		objects.append(obj)
		self[collectionName] = objects
		return obj

	def getMemento(self, start=None):
		"""Return a copy of all the key/values of this and all sub-objects."""
		if start is None:
			start = self
		m = {"type": start.__class__.__name__}

		for k, v in start.items():
			if isinstance(v, dict):
				m[k] = self.getMemento(v)
			elif isinstance(v, list):
				m[k] = []
				for c in v:
					m[k].append(self.getMemento(c))
			else:
				m[k] = v
		return m			


	def getProp(self, prop, evaluate=True, returnException=False):
		"""Return the value of the property.

		If defined, it will be eval()'d. Otherwise,	the default will be returned.
		If there isn't a default, an exception will be raised as the object isn't
		set up to have the passed prop.
		"""
		def getDefault():
			if self.AvailableProps.has_key(prop):
				val = self.AvailableProps[prop]["default"]
				if not evaluate:
					# defaults are not stringified:
					val = repr(val)
				return val
			else:
				raise ValueError("Property name '%s' unrecognized." % prop)

		if self.has_key(prop):
			if not evaluate or prop == "type":
				return self[prop]
			try:
				return eval(self[prop])
			except Exception, e:
				# eval() failed. Return the default or the exception string.
				if returnException:
					return e
				return getDefault()
		else:
			# The prop isn't defined, use the default.
			return getDefault()


	def setProp(self, prop, val):
		"""Update the value of the property."""
		if not self.AvailableProps.has_key(prop):
			raise ValueError("Property '%s' doesn't exist." % prop)
		self[prop] = val


	def getPropVal(self, propName):
		return self.getProp(propName, evaluate=False)

	def getPropDoc(self, propName):
		return self.AvailableProps[propName]["doc"]

	def updatePropVal(self, propName, propVal):
		self.setProp(str(propName), str(propVal))


	def _getAvailableProps(self):
		if hasattr(self, "_AvailableProps"):
			val = self._AvailableProps
		else:
			val = self._AvailableProps = CaselessDict()
		return val

	def _setAvailableProps(self, val):
		self._AvailableProps = val


	def _getBands(self):
		return self.Report.reportWriter.Bands


	def _getDesProps(self):
		strType = {"type" : str, "readonly" : False, "alsoDirectEdit": True}
		props = self.AvailableProps.keys()
		desProps = {}
		for prop in props:
			desProps[prop] = strType.copy()
			if "color" in prop.lower():
				desProps[prop]["customEditor"] = "editColor"
## 2006/1/30: The commented code below makes a dropdown list for the standard 
#             fonts. However, it blows away the user being able to type in a
#             font that isn't in the standard list. Same with the other props.
#             We need to get a combobox editor working, so that the user can 
#             free-form type as well as select a predefined value from the list.
#			if prop.lower() == "fontname":
#				desProps[prop]["type"] = list
#				desProps[prop]["values"] = ['"Courier"', '"Courier-Bold"', 
#						'"Courier-Oblique"', '"Courier-BoldOblique"', '"Helvetica"', 
#						'"Helvetica-Bold"', '"Helvetica-Oblique"', '"Helvetica-BoldOblique"',
#						'"Times-Roman"', '"Times-Bold"', '"Times-Italic"', 
#						'"Times-BoldItalic"', '"Symbol"', '"ZapfDingbats"']
#			if prop.lower() == "hanchor":
#				desProps[prop]["type"] = list
#				desProps[prop]["values"] = ['"Left"', '"Center"', '"Right"'] 
#			if prop.lower() == "vanchor":
#				desProps[prop]["type"] = list
#				desProps[prop]["values"] = ['"Bottom"', '"Middle"', '"Top"']
#			if prop.lower() == "orientation" and self.__class__.__name__ == "Page":
#				desProps[prop]["type"] = list
#				desProps[prop]["values"] = ['"Portrait"', '"Landscape"']
		return desProps


	def _getRecord(self):
		if hasattr(self.Report, "_liveRecord"):
			return self.Report._liveRecord
		return {}


	def _getReport(self):
		parent = self
		while not isinstance(parent, Report):
			parent = parent.parent
		return parent


	def _getVariables(self):
		return self.Report.reportWriter.Variables


	AvailableProps = property(_getAvailableProps, _setAvailableProps)
	Bands = property(_getBands)

	DesignerProps = property(_getDesProps, None, None,
		_("""Returns a dict of editable properties for the control, with the 
		prop names as the keys, and the value for each another dict, 
		containing the following keys: 'type', which controls how to display
		and edit the property, and 'readonly', which will prevent editing
		when True. (dict)""") )

	Record = property(_getRecord)
	Report = property(_getReport)
	Variables = property(_getVariables)


class Drawable(ReportObject):
	"""Abstract drawable report object, such as a rectangle or string."""
	def initAvailableProps(self):
		super(Drawable, self).initAvailableProps()

		self.AvailableProps["DesignerLock"] = toPropDict(bool, False, 
				"""Specifies whether the object's geometry can be changed interactively.

				Setting designerLock to True protects you from accidentally changing
				the size and position of the object with the mouse at design time.""")

		self.AvailableProps["x"] = toPropDict(float, 0.0, 
				"""Specifies the horizontal position of the object, relative to hAnchor.""")

		self.AvailableProps["y"] = toPropDict(float, 0.0, 
				"""Specifies the vertical position of the object, relative to vAnchor.""")

		self.AvailableProps["Width"] = toPropDict(float, 55.0, 
				"""Specifies the width of the object.""")

		self.AvailableProps["Height"] = toPropDict(float, 18.0, 
				"""Specifies the height of the object.""")

		self.AvailableProps["Rotation"] = toPropDict(float, 0.0, 
				"""Specifies the rotation of the object, in degrees.""")

		self.AvailableProps["hAnchor"] = toPropDict(str, "left", 
				"""Specifies where horizontal position is relative to.

				Must evaluate to 'left', 'center', or 'right'.""")

		self.AvailableProps["vAnchor"] = toPropDict(str, "bottom", 
				"""Specifies where vertical position is relative to.

				Must evaluate to 'bottom', 'middle', or 'top'.""")

		self.AvailableProps["Show"] = toPropDict(bool, True, 
				"""Determines if the object is shown on the report.

				Specify an expression that evaluates to True or False. If False,
				the object will not be shown on the report. Otherwise, it will.
				Just like all other properties, your expression will be evaluated
				every time this object is to be printed.
				""")


class Report(ReportObject):
	"""Represents the report."""

	def initAvailableProps(self):
		super(Report, self).initAvailableProps()

		self.AvailableProps["Author"] = toPropDict(str, "", 
				"""Specifies the author of the report. Appears in PDF properties.""")

		self.AvailableProps["Subject"] = toPropDict(str, "", 
				"""Specifies the subject of the report. Appears in PDF properties.""")

		self.AvailableProps["Keywords"] = toPropDict(tuple, (), 
				"""Specifies keywords for the report. Appears in PDF properties.""")

		self.AvailableProps["Title"] = toPropDict(str, "", 
		"""Specifies the title of the report. Appears in PDF properties.""")

		self.AvailableProps["ColumnCount"] = toPropDict(int, 1, 
				"""Specifies the number of columns to divide the report into.""")

	def insertRequiredElements(self):
		"""Insert any missing required elements into the report form."""
		self.setdefault("Title", '"Dabo Report"')
		self.setdefault("Subject", '"http://dabodev.com"')
		self.setdefault("Author", '"Dabo Report Writer"')
		self.setdefault("Keywords", '("dabo", "report", "writer", "banded", "free")')
		self.setdefault("Page", Page(self))
		self.setdefault("PageHeader", PageHeader(self))
		self.setdefault("Detail", Detail(self))
		self.setdefault("PageFooter", PageFooter(self))
		self.setdefault("PageBackground", PageBackground(self))
		self.setdefault("PageForeground", PageForeground(self))
		self.setdefault("ReportBegin", ReportBegin(self))
		self.setdefault("ReportEnd", ReportEnd(self))
		self.setdefault("Groups", Groups(self))
		self.setdefault("Variables", Variables(self))


class Page(ReportObject):
	"""Represents the page."""
	def initAvailableProps(self):
		super(Page, self).initAvailableProps()
		self.AvailableProps["MarginBottom"] = toPropDict(float, ".5 in", 
				"""Specifies the page's bottom margin.""")

		self.AvailableProps["MarginLeft"] = toPropDict(float, ".5 in", 
				"""Specifies the page's left margin.""")

		self.AvailableProps["MarginTop"] = toPropDict(float, ".5 in", 
				"""Specifies the page's top margin.""")

		self.AvailableProps["MarginRight"] = toPropDict(float, ".5 in", 
				"""Specifies the page's right margin.""")

		self.AvailableProps["Orientation"] = toPropDict(str, "portrait", 
				"""Specifies the page orientation.

				Must evaluate to one of 'portrait' or 'landscape'.""")

		self.AvailableProps["Size"] = toPropDict(str, "letter", 
				"""Specifies the page size.

				This is a tuple of (width, heigth) such as:
				  ('8 in', '5.5 in')

				You may also use, in place of the tuple,  some common 
				identifiers such as:
				  'Letter'
				  'A4'

				See also the Orientation property, which merely swaps
				the width and height values. """)


class Group(ReportObject):
	"""Represents report groups."""
	def initAvailableProps(self):
		super(Group, self).initAvailableProps()
		self.AvailableProps["expr"] = toPropDict(str, None, 
				"""Specifies the group expression.

				When the value of the group expression changes, a new group will
				be started.""")

		self.AvailableProps["StartOnNewPage"] = toPropDict(bool, False, 
				_("""Specifies whether new groups should begin on a new page."""))

		self.AvailableProps["ReprintHeaderOnNewPage"] = toPropDict(bool, False, 
				_("""Specifies whether the group header gets reprinted on new pages."""))

		self.AvailableProps["ResetPageNumber"] = toPropDict(bool, False, 
				_("""Specifies whether the page number gets reset with a new group."""))

	def insertRequiredElements(self):
		if not self.has_key("GroupHeader"):
			self["GroupHeader"] = GroupHeader(self)
		if not self.has_key("GroupFooter"):
			self["GroupFooter"] = GroupFooter(parent=self)

class Variable(ReportObject):
	"""Represents report variables."""
	def initAvailableProps(self):
		super(Variable, self).initAvailableProps()
		self.AvailableProps["InitialValue"] = toPropDict(str, None, 
				"""Specifies the variable's initial value.""")

		self.AvailableProps["expr"] = toPropDict(str, None, 
				"""Specifies the variable expression.

				At every new record in the cursor, the variable expression will be
				evaluated.""")

		self.AvailableProps["Name"] = toPropDict(str, None, 
				"""Specifies the name of the variable.""")

		self.AvailableProps["ResetAt"] = toPropDict(str, None, 
				"""Specifies when to reset the variable to the initial value.

				Typically, this will match a particular group expression.""")



class Band(ReportObject):
	"""Abstract band."""
	def initAvailableProps(self):
		super(Band, self).initAvailableProps()
		self.AvailableProps["Height"] = toPropDict(float, 0.0, 
				"""Specifies the height of the band, not including growable objects.

				If the height evaluates to None, the height of the band will size
				itself dynamically at runtime.""")

		self.AvailableProps["TotalHeight"] = toPropDict(float, 0.0, 
				"""Specifies the height of the band, including growable objects.

				Read-only/calculated at runtime. Specifies the height of the band
				on the page, and gets reevaluated for each page the band continues
				printing on.""")

		self.AvailableProps["DesignerLock"] = toPropDict(bool, False, 
				"""Specifies whether the band height can be changed interactively.

				Setting designerLock to True protects you from accidentally changing
				the height of the band with the mouse at design time.""")

		self.AvailableProps["Show"] = toPropDict(bool, True, 
				"""Determines if the band is shown or skipped.

				Specify an expression that evaluates to True or False. If False,
				the band will not print. 

				Just like all other properties, your expression will be evaluated
				every time this object is to be printed.
				""")

	def insertRequiredElements(self):
		"""Insert any missing required elements into the band."""
		self.setdefault("Objects", Objects(self))

	def _getBandName(self):
		name = self.__class__.__name__
		return "%s%s" % (name[0].lower(), name[1:])
		

class PageBackground(Band): pass
class PageHeader(Band): pass
class Detail(Band): pass
class PageFooter(Band): pass
class GroupHeader(Band): pass
class GroupFooter(Band): pass
class PageForeground(Band): pass

class ReportBegin(Band):
	def initAvailableProps(self):
		super(ReportBegin, self).initAvailableProps()
		self.AvailableProps["PageBreakAfter"] = toPropDict(bool, False, 
				"""Specifies whether a page break is inserted after the band prints.""")

class ReportEnd(Band):
	def initAvailableProps(self):
		super(ReportEnd, self).initAvailableProps()
		self.AvailableProps["PageBreakBefore"] = toPropDict(bool, False, 
				"""Specifies whether a page break is inserted before the band prints.""")


class Rectangle(Drawable):
	"""Represents a rectangle."""
	def initAvailableProps(self):
		super(Rect, self).initAvailableProps()
		self.AvailableProps["FillColor"] = toPropDict(tuple, None, 
				"""Specifies the fill color.

				If None, the fill color will be transparent.""")

		self.AvailableProps["StrokeWidth"] = toPropDict(float, 1, 
				"""Specifies the width of the stroke, in points.""")

		self.AvailableProps["StrokeColor"] = toPropDict(tuple, (0, 0, 0), 
				"""Specifies the stroke color.""")

		self.AvailableProps["StrokeDashArray"] = toPropDict(tuple, None, 
				"""Specifies the stroke dash.

				For instance, (1,1) will give you a dotted look, (1,1,5,1) will
				give you a dash-dot look.""")

## backwards compatibility:
Rect = Rectangle

class String(Drawable):
	"""Represents a text string."""
	def initAvailableProps(self):
		super(String, self).initAvailableProps()
		self.AvailableProps["expr"] = toPropDict(str, None, 
				"""Specifies the string to print.""")

		self.AvailableProps["BorderWidth"] = toPropDict(float, 0, 
				"""Specifies the width of the border around the string.""")

		self.AvailableProps["BorderColor"] = toPropDict(tuple, (0, 0, 0), 
				"""Specifies the border color.""")

		self.AvailableProps["Align"] = toPropDict(str, "left", 
				"""Specifies the string alignment.

				This must evaluate to one of 'left', 'center', or 'right'.""")

		self.AvailableProps["FontName"] = toPropDict(str, "Helvetica", 
				"""Specifies the font name, boldface, and italics all in one.

				There are only a handful of reliable selections:
					Courier
					Courier-Bold
					Courier-Oblique
					Courier-BoldOblique

					Helvetica
					Helvetica-Bold
					Helvetica-Oblique
					Helvetica-BoldOblique

					Times-Roman
					Times-Bold
					Times-Italic
					Times-BoldItalic

					Symbol

					ZapfDingbats

				Please note that for predictable cross-platform results, you need to
				stick to the fonts above. Otherwise, you'll need to ensure any TTF
				fonts you specify are distributed to all systems that create the 
				reports. If you specify a font name that doesn't exist, the Dabo report
				writer will default to 'Helvetica'.
				""")

		self.AvailableProps["FontSize"] = toPropDict(float, 10, 
				"""Specifies the size of the font, in points.""")

		self.AvailableProps["FontColor"] = toPropDict(tuple, (0, 0, 0), 
				"""Specifies the color of the text.""")

		self.AvailableProps["ScalePercent"] = toPropDict(tuple, (100.0, 100.0), 
				"""Specifies the scaling of the string. Set to (150,100) to make it wide.""")


class Image(Drawable):
	"""Represents an image."""
	def initAvailableProps(self):
		super(Image, self).initAvailableProps()
		self.AvailableProps["expr"] = toPropDict(str, "", 
				"""Specifies the image to use.""")

		self.AvailableProps["BorderWidth"] = toPropDict(float, 0, 
				"""Specifies the width of the image border.""")

		self.AvailableProps["BorderColor"] = toPropDict(tuple, (0, 0, 0), 
				"""Specifies the color of the image border.""")

		self.AvailableProps["ImageMask"] = toPropDict(tuple, None, 
				"""Specifies the image mask.""")

		self.AvailableProps["ScaleMode"] = toPropDict(str, "scale", 
				"""Specifies how to handle frame and image of differing size.

				"scale" or "stretch" will change the image size to fit the frame. 
				"clip" will display the image in the frame as-is.
				"proportional" resizes the image to fit in the frame without changing its proportions.""")

class BarGraph(Drawable):
        """Represents a bar graph"""
	def initAvailableProps(self):
		super(BarGraph, self).initAvailableProps()

		self.AvailableProps["expr"] = toPropDict(list, [], 
				"""Specifies the data to display on the graph.""")

		self.AvailableProps["Labels"] = toPropDict(list, [], 
				"""Specifies the lables to display on the bottom.""")
		
		self.AvailableProps["Title"] = toPropDict(str, "Title", 
				"""Specifies the title to display on the graph.""")
		
		self.AvailableProps["XLabel"] = toPropDict(str, "X-Label", 
				"""Specifies the label to display on the x axis.""")
		
		self.AvailableProps["YLabel"] = toPropDict(str, "Y-Label", 
				"""Specifies the label to display on the y axis.""")
		
		self.AvailableProps["XGrid"] = toPropDict(bool, False, 
				"""Specifies if a grid should be displayed on the major ticks of the x axis.""")
		
		self.AvailableProps["YGrid"] = toPropDict(bool, False, 
				"""Specifies if a grid should be displayed on the major ticks of the y axis.""")		

		self.AvailableProps["Orientation"] = toPropDict(str, "horizontal", 
				"""Orientation of the graph (vertical, horizontal).""")			

		self.AvailableProps["Log"] = toPropDict(bool, False,
				"""True sets orientation axis to log scale""")			
								
		self.AvailableProps["LabelTextSize"] = toPropDict(str, "x-small", 
				"""The size of the text to display for the labels.""")

		self.AvailableProps["BarColor"] = toPropDict(str, "blue", 
				"""Specifies the colour of the bars.""")
		
		self.AvailableProps["BarBorder"] = toPropDict(int, 0, 
				"""Specifies the size of the border of the bar.""")

		self.AvailableProps["BarBorderColor"] = toPropDict(str, "black", 
				"""Specifies the colour of the border of the bar.""")			
				
		self.AvailableProps["Error"] = toPropDict(list, [], 
				"""Specifies the error bars to display on the graph.""")		
		
		self.AvailableProps["CapSize"] = toPropDict(int, 3, 
				"""Determines the length in points of the error bar caps""")
		
		self.AvailableProps["ErrorBarColor"] = toPropDict(str, "black", 
				"""Specifies the colour of the error bars.""")			
						
		self.AvailableProps["BorderWidth"] = toPropDict(float, 0, 
				"""Specifies the width of the image border.""")

		self.AvailableProps["BorderColor"] = toPropDict(tuple, (0, 0, 0), 
				"""Specifies the color of the image border.""")
		
		self.AvailableProps["BackgroundColor"] = toPropDict(str, "white", 
				"""Specifies the colour of the border of the bar.""")			
				
		self.AvailableProps["ScaleMode"] = toPropDict(str, "scale", 
				"""Specifies how to handle frame and image of differing size.

				"scale" will change the image size to fit the frame. "clip" will
				display the image in the frame as-is.""")        
		
class Line(Drawable):
	"""Represents a line."""
	def initAvailableProps(self):
		super(Line, self).initAvailableProps()
		self.AvailableProps["LineSlant"] = toPropDict(str, "-", 
				"""Specifies the slant of the line.

				Valid values are "-", "|", "/", and "\\". Note that the 
				backslash character needs to be escaped in Python by making
				it a double-backslash.
				""")

		self.AvailableProps["StrokeWidth"] = toPropDict(float, 1, 
				"""Specifies the width of the stroke, in points.""")

		self.AvailableProps["StrokeColor"] = toPropDict(tuple, (0, 0, 0), 
				"""Specifies the stroke color.""")

		self.AvailableProps["StrokeDashArray"] = toPropDict(tuple, None, 
				"""Specifies the stroke dash.

				For instance, (1,1) will give you a dotted look, (1,1,5,1) will
				give you a dash-dot look.""")


class SpanningLine(Line):
	"""Represents a line that spans from a group or page header to a group or page footer."""
	def initAvailableProps(self):
		super(SpanningLine, self).initAvailableProps()
		del self.AvailableProps["x"]
		del self.AvailableProps["y"]
		del self.AvailableProps["LineSlant"]
		self.AvailableProps["x"] = toPropDict(float, 0.0, 
				"""Specifies the x of the starting point of the line, in the group or page header.""")
		self.AvailableProps["y"] = toPropDict(float, 0.0, 
				"""Specifies the y of the starting point of the line, in the group or page header.""")
		self.AvailableProps["xFooter"] = toPropDict(float, 0.0, 
				"""Specifies the x of the ending point of the line, in the group or page footer.""")
		self.AvailableProps["yFooter"] = toPropDict(float, 0.0, 
				"""Specifies the y of the ending point of the line, in the group or page footer.""")


class Frameset(Drawable):
	"""Represents a frameset."""
	def initAvailableProps(self):
		super(Frameset, self).initAvailableProps()

		self.AvailableProps["FrameId"] = toPropDict(str, None, 
				"""(to remove)""")

		self.AvailableProps["BorderWidth"] = toPropDict(float, 0, 
				"""Specifies the width of the frame border.""")

		self.AvailableProps["BorderColor"] = toPropDict(tuple, (0, 0, 0), 
				"""Specifies the border color.""")

		self.AvailableProps["PadLeft"] = toPropDict(float, 0, 
				"""Specifies the padding on the left side of the frame.""")

		self.AvailableProps["PadRight"] = toPropDict(float, 0, 
				"""Specifies the padding on the right side of the frame.""")

		self.AvailableProps["PadTop"] = toPropDict(float, 0, 
				"""Specifies the padding on the top side of the frame.""")

		self.AvailableProps["PadBottom"] = toPropDict(float, 0, 
				"""Specifies the padding on the bottom side of the frame.""")

		self.AvailableProps["ColumnCount"] = toPropDict(int, 1, 
				"""Specifies the number of columns in the frame.""")


	def insertRequiredElements(self):
		"""Insert any missing required elements into the frameset."""
		self.setdefault("Objects", Objects(self))


class Paragraph(Drawable):
	"""Represents a paragraph."""
	def initAvailableProps(self):
		super(Paragraph, self).initAvailableProps()
		self.AvailableProps["Style"] = toPropDict(str, "Normal", 
				"""Reportlab allows defining styles, but for now leave this as "Normal".""")

		self.AvailableProps["FontSize"] = toPropDict(float, 10, 
				"""Specifies the font size.""")

		self.AvailableProps["FontName"] = toPropDict(str, "Helvetica", 
				"""Specifies the font name.""")

		self.AvailableProps["Leading"] = toPropDict(float, 0, 
				"""Specifies the font size.""")

		self.AvailableProps["SpaceAfter"] = toPropDict(float, 0, 
				"""Specifies the font size.""")

		self.AvailableProps["SpaceBefore"] = toPropDict(float, 0, 
				"""Specifies the font size.""")

		self.AvailableProps["LeftIndent"] = toPropDict(float, 0, 
				"""Specifies the font size.""")

		self.AvailableProps["FirstLineIndent"] = toPropDict(float, 0, 
				"""Specifies the font size.""")

		self.AvailableProps["expr"] = toPropDict(str, "", 
				"""Specifies the text to print.""")

class TestCursor(ReportObjectCollection):
	def addRecord(self, record):
		tRecord = TestRecord(self)
		for k, v in record.items():
			tRecord[k] = v
		tRecord.initAvailableProps()
		self.append(tRecord)

class TestRecord(ReportObject):
	def initAvailableProps(self):
		for k, v in self.items():
			self.AvailableProps[k] = toPropDict(str, "", "")
	

class ReportWriter(object):
	"""Reads a report form specification, iterates over a data cursor, and
	outputs a pdf file. Allows for lots of fine-tuned control over layout, and
	dynamic evaluation of object properties. Works with the concept of bands,
	letting the designer lay out the page header, footer, groups, and detail
	separately. 

	At runtime, you feed ReportWriter a data cursor (a list of dictionaries
	where each list index is a 'row' and each dictionary key is a 'field'.)
	The detail band will print once for every row.

	Define your properties in the report form specification file, which is
	either xml or pure Python, depending on your preferences. There are (will
	be) examples of both types of specification files here. In the future 
	there will be a Dabo Report Designer that will create the xml report form
	specification files for you.

	In the context of a running report, the property values of the specification
	can refer to 'self', which is the ReportWriter instance. Thus, you can use
	the self instance to get to whatever value you want for the property.

	For example, to get the value of a field to print in your detail band, just 
	put a string object into the detail band, positioned and sized how you want,
	and set the 'expr' property to refer to the field. If the field name is
	'cArtist', the expr for the string object would be 'self.Record["cArtist"]'.

	You'll need to craft denormalized data, as ReportWriter only wants to operate
	on a single table and there is no provision for relating one table to another.
	This is, IMO, the right way to go anyway, offering the most control and 
	flexibility yet still keeping it really simple. Just have the calling program
	get the data denormalized into one cursor, and then call ReportWriter 
	feeding it the Cursor, Report Form, and OutputFile.

	More documentation will come.
	"""
	_clearMemento = True

	def storeSpanningObject(self, obj, origin=(0,0), group=None):
		"""Store the passed spanning object for printing when the group or
		page ends. Pass the group expr to identify group headers, or None to refer
		to the pageHeader.
		"""
		obj["xFrom"] = origin[0]
		obj["yFrom"] = origin[1]
		if group is not None:
			group = group["expr"]
		spanList = self._spanningObjects.setdefault(group, [])
		if obj not in spanList:
			spanList.append(obj)

	def drawSpanningObjects(self, origin=(0,0), group=None):
		"""Draw all spanning objects. Called when page is changing or group is ending."""
		x,y = origin
		if group is None:
			spanList = []
			spanList_page = []
			for g in self._spanningObjects:
				for l in self._spanningObjects[g]:
					if g is None:
						spanList_page.append(l)
					else:
						spanList.append(l)
		else:
			spanList = self._spanningObjects.setdefault(group["expr"], [])
			spanList_page = []
		for obj in spanList:
			y1 = self.getPt(obj.getProp("yFooter")) + y
			x1 = self.getPt(obj.getProp("xFooter")) + x
			self.draw(obj, (x1, y1))
		for obj in spanList_page:
			y1 = self.getPt(obj.getProp("yFooter")) + self.getPt(self.ReportForm["page"].getProp("marginBottom"))
			x1 = self.getPt(obj.getProp("xFooter")) + x
			self.draw(obj, (x1, y1))

	def clearSpanningObjects(self, group=None):
		if group is not None:
			group = group["expr"]
		try:
			del self._spanningObjects[group]
		except KeyError:
			pass
 		
	def draw(self, obj, origin=(0,0),	availableHeight=None, deferred=None):
		"""Draw the given object on the Canvas.

		The object is a dictionary containing properties, and	origin is the (x,y)
		tuple where the object will be drawn. 

		availableHeight is the height available on the current page; deferred is 
		the contents of the object partially printed on the last page that needs
		to continue printing now (paragraph story). 
		"""
		## (Can't get x,y directly from object because it may have been modified 
		## by the calling program to adjust for	band position, and draw() 
		## doesn't know about bands.)
		neededHeight = 0
		objType = obj.__class__.__name__
		c = self.Canvas
		x,y = origin

		## We'll be tweaking with the canvas settings below, so we need to save
		## the state first so we can restore when done. Do not do any short-circuit
		## returns between c.saveState() and c.restoreState()!
		c.saveState()

		neededHeight = 0

		## These properties can apply to all objects:
		width = self.getPt(obj.getProp("width"))
	
		rotation = obj.getProp("rotation")
		hAnchor = obj.getProp("hAnchor").lower()
		vAnchor = obj.getProp("vAnchor").lower()

		if hAnchor == "right":
			x = x - width
		elif hAnchor == "center":
			x = x - (width / 2)
	
		if objType != "Frameset":	
			height = self.getPt(obj.getProp("Height"))
			if vAnchor == "top":
				y = y - height
			elif vAnchor == "middle":
				y = y - (height / 2)
	
		
		## Do specific things based on object type:
		if objType == "Rectangle":
			d = shapes.Drawing(width, height)
			d.rotate(rotation)
	
			props = {}
			## props available in reportlab that we use:
			##   x,y,width,height
			##   fillColor: None for transparent, or (r,g,b)
			##   strokeColor: None for transparent, or (r,g,b)
			##   strokeDashArray: None
			##   strokeWidth: 0.25
	
			## props available that we don't currently use:
			##   rx, ry
			##   strokeMiterLimit: 0
			##   strokeLineJoin: 0
			##   strokeLineCap: 0
			##
	
			for prop in ("strokeWidth", "fillColor", "strokeColor", 
					"strokeDashArray", ):
				props[prop] = obj.getProp(prop)
			props["strokeWidth"] = self.getPt(props["strokeWidth"])

			r = shapes.Rect(0, 0, width, height)
			r.setProperties(props)
			d.add(r)
			d.drawOn(c, x, y)
	
		if objType in ("Line", "SpanningLine"):
			props = {}
			## props available in reportlab that we use:
			##   x,y,width,height
			##   fillColor: None for transparent, or (r,g,b)
			##   strokeColor: None for transparent, or (r,g,b)
			##   strokeDashArray: None
			##   strokeWidth: 0.25
	
			## props available that we don't currently use:
			##   rx, ry
			##   strokeMiterLimit: 0
			##   strokeLineJoin: 0
			##   strokeLineCap: 0
			##
	
			for prop in ("strokeWidth", "strokeColor", "strokeDashArray", ):
				props[prop] = obj.getProp(prop)
			props["strokeWidth"] = self.getPt(props["strokeWidth"])

			if objType == "SpanningLine":
				# Line gets drawn from fixed (x,y) to fixed (xFooter, yFooter) points.
				x = obj["xFrom"]
				y = obj["yFrom"]
				xFooter, yFooter = origin
				c.setStrokeColorRGB(*props["strokeColor"])
				c.setLineWidth(props["strokeWidth"])
				c.line(x, y, xFooter, yFooter)
			else:
				d = shapes.Drawing(width, height)
				d.rotate(rotation)
	
				lineSlant = obj.getProp("lineSlant")
				anchors = {"left": 0,
						"center": width/2,
						"right": width,
						"top": height,
						"middle": height/2,
						"bottom": 0}

				if lineSlant == "-":
					# draw line from (left,middle) to (right,middle) anchors
					beg = (anchors["left"], anchors["middle"])
					end = (anchors["right"], anchors["middle"])
				elif lineSlant == "|":
					# draw line from (center,bottom) to (center,top) anchors
					beg = (anchors["center"], anchors["bottom"])
					end = (anchors["center"], anchors["top"])
				elif lineSlant == "\\":
					# draw line from (right,bottom) to (left,top) anchors
					beg = (anchors["right"], anchors["bottom"])
					end = (anchors["left"], anchors["top"])
				elif lineSlant == "/":
					# draw line from (left,bottom) to (right,top) anchors
					beg = (anchors["left"], anchors["bottom"])
					end = (anchors["right"], anchors["top"])
				else:
					# don't draw the line
					lineSlant = None

				if lineSlant:
					r = shapes.Line(beg[0], beg[1], end[0], end[1])
					r.setProperties(props)
					d.add(r)
					d.drawOn(c, x, y)

		elif objType == "String":
			## Set the props for strings:
			borderWidth = self.getPt(obj.getProp("borderWidth"))
			borderColor = obj.getProp("borderColor")
			align = obj.getProp("align")
			fontName = obj.getProp("fontName")
			fontSize = obj.getProp("fontSize")
			fontColor = obj.getProp("fontColor")
			scalePercent = [val/100.0 for val in obj.getProp("scalePercent")]

			## Set canvas props based on our props:
			c.translate(x, y)
			c.rotate(rotation)
			c.scale(scalePercent[0], scalePercent[1])
			c.setLineWidth(borderWidth)
			c.setStrokeColor(borderColor)
			c.setFillColor(fontColor)
			try:
				c.setFont(fontName, fontSize)
			except StandardError:
				# An unavailable fontName was likely specified. The rw docs promise to
				# default to Helvetica in this case.
				c.setFont("Helvetica", fontSize)
	
			if borderWidth > 0:
				stroke = 1
			else:
				stroke = 0
	
			# clip the text to the specified width and height
			p = c.beginPath()
	
			## HACK! the -5000 thing is to keep the area below the font's baseline
			## from being clipped. I've got to learn the right way to handle this, probably
			## by calculating the amount needed based on the font size. But, 5000 is enough
			## for anything, and we don't need to clip anything but the horizontal anyway. 
			p.rect(0, -5000, width, height+5000)
			c.clipPath(p, stroke=stroke)
	
			funcs = {"center": c.drawCentredString,
					"right": c.drawRightString,
					"left": c.drawString}
			func = funcs[align]

			if align == "center":
				posx = (width / 2)
			elif align == "right":
				posx = width
			else:
				posx = 0
	
			# draw the string using the function that matches the alignment:
			s = obj.getProp("expr", returnException=True)

			if isinstance(s, basestring):
				try:
					s = s.encode(self.Encoding)
				except UnicodeDecodeError:
					# s must have already been encoded, and the default encoding is ascii.
					pass
			else:
				s = unicode(s)
			func(posx, 0, s)
	
		elif objType == "Frameset":
			# A frame is directly related to reportlab's platypus Frame.
				
			borderWidth = self.getPt(obj.getProp("borderWidth"))
			borderColor = obj.getProp("borderColor")
			columnCount = obj.getProp("columnCount")
			columnWidth = width/columnCount
			padLeft = self.getPt(obj.getProp("padLeft"))
			padRight = self.getPt(obj.getProp("padRight"))
			padTop = self.getPt(obj.getProp("padTop"))
			padBottom = self.getPt(obj.getProp("padBottom"))
			frameId = obj.getProp("frameId")

			if deferred:
				story = deferred
				neededHeight = sum([s[1] for s in story])
			else:
				story, neededHeight = self.getStory(obj)

			dynamicHeight = obj.getProp("Height") is None

			printStory = story
			deferredStory = []
			tot_p_height = 0
			printStoryHeight = deferredStoryHeight = 0

			if dynamicHeight and neededHeight >= availableHeight:
				printStory = []
				for p, p_height in story:
					tot_p_height += p_height
					if tot_p_height + padTop + padBottom >= availableHeight:
						deferredStory.append((p, p_height))
						deferredStoryHeight += p_height
					else:
						printStory.append((p, p_height))
						printStoryHeight += p_height
				neededHeight = printStoryHeight + padTop + padBottom

			if not dynamicHeight:
				frameHeight = self.getPt(obj.getProp("Height"))
			else:
				frameHeight = neededHeight

			if vAnchor == "top":
				y = y - neededHeight
			elif vAnchor == "middle":
				y = y - (neededHeight / 2)

			## Set canvas props based on our props:
			c.translate(x, y)
			c.rotate(rotation)
			c.setLineWidth(borderWidth)
			c.setStrokeColor(borderColor)
	
			if borderWidth > 0:
				boundary = 1
			else:
				boundary = 0

			for columnIndex in range(columnCount):
				f = platypus.Frame(columnIndex*columnWidth, 0, columnWidth, frameHeight, leftPadding=padLeft,
						rightPadding=padRight, topPadding=padTop,
						bottomPadding=padBottom, id=frameId, 
						showBoundary=boundary)
				f.addFromList([s[0] for s in printStory], c)
	
			deferred = deferredStory
			neededHeight = deferredStoryHeight


		elif objType == "Image":
			borderWidth = self.getPt(obj.getProp("borderWidth"))
			borderColor = obj.getProp("borderColor")
			mask = obj.getProp("imageMask")
			mode = obj.getProp("scaleMode")
			preserveRatio = False

			c.translate(x, y)
			c.rotate(rotation)
			c.setLineWidth(borderWidth)
			c.setStrokeColor(borderColor)
	
			if borderWidth > 0:
				stroke = 1
			else:
				stroke = 0
	
			# clip around the outside of the image:
			p = c.beginPath()
			p.rect(-1, -1, width+2, height+2)
			c.clipPath(p, stroke=stroke)
	
			img = obj.getProp("expr")
			if isinstance(img, basestring) and "\0" not in img:
				# this is a path to image file, not the image itself
				if not os.path.exists(img):
					img = os.path.join(self.HomeDirectory, img)
			else:
				# convert stream to PIL image:
				#buffer = cStringIO.StringIO()
				#buffer.write(img)
				#buffer.seek(0)				
				#img = PILImage.open(buffer)
				# (pkm: the above doesn't work in all reportlab versions. Safer to save a 
				#       temp file unfortunately.)
				imageFileName = reportUtils.getTempFile(ext="png")
				imageFile = open(imageFileName, "wb")
				imageFile.write(img)
				imageFile.close()
				img = imageFileName

			if mode == "clip":
				# Need to set w,h to None for the drawImage, which will draw it in its
				# "natural" state 1:1 pixel:point, which could flow out of the object's
				# width/height, resulting in clipping.
				width, height = None, None

			elif mode == "proportional":
				preserveRatio = True

			if img:
				try:
					c.drawImage(img, 0, 0, width, height, mask, preserveAspectRatio=preserveRatio)
				except StandardError:
					c.drawCentredString(0, 0, "<< Image expr error >>")

		elif objType == "BarGraph":
			# Do these imports here so as not to require the huge matplotlib unless
			# necessary (I was unable to get my py2exe configured correctly to handle
			# matplotlib). -- pkm
			from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
			from matplotlib.figure import Figure
			from pylab import Line2D
			borderWidth = self.getPt(obj.getProp("borderWidth"))
			borderColor = obj.getProp("borderColor")
			mask = obj.getProp("imageMask")
			mode = obj.getProp("scaleMode")

			c.translate(x, y)
			c.rotate(rotation)
			c.setLineWidth(borderWidth)
			c.setStrokeColor(borderColor)
	
			if borderWidth > 0:
				stroke = 1
			else:
				stroke = 0
	
			# clip around the outside of the image:
			p = c.beginPath()
			p.rect(-1, -1, width+2, height+2)
			c.clipPath(p, stroke=stroke)
	
			if mode == "clip":
				# Need to set w,h to None for the drawImage, which will draw it in its
				# "natural" state 1:1 pixel:point, which could flow out of the object's
				# width/height, resulting in clipping.
				width, height = None, None
	
			data = obj.getProp("expr")
			labels = obj.getProp("Labels")	
			title = obj.getProp("Title")	
			xlabel = obj.getProp("XLabel")	
			ylabel = obj.getProp("YLabel")	
			textsize = obj.getProp("LabelTextSize")	
			xgrid = obj.getProp("XGrid")	
			ygrid = obj.getProp("YGrid")
			orientation = obj.getProp("Orientation")
			log = obj.getProp("Log")		
			error = obj.getProp("Error")
			capsize = obj.getProp("CapSize")
			ecolor = obj.getProp("ErrorBarColor")
			barborder = obj.getProp("BarBorder")
			barbordercolor = obj.getProp("BarBorderColor")
			bgcolor = obj.getProp("BackgroundColor")
			barcolor = obj.getProp("BarColor")				

			fig = Figure(facecolor=bgcolor)
			canvas = FigureCanvas(fig)
			ax = fig.add_subplot(111)			
			xlocations = [0.25+x for x in range(len(data))]
			barwidth = 0.5
			ax.bar(xlocations, data, yerr=error, linewidth=barborder,
			       log=log, color=barcolor, ecolor=ecolor,
			       capsize=capsize, edgecolor=barbordercolor)
			ax.set_xlabel(xlabel, size=textsize)
			ax.set_ylabel(ylabel, size=textsize)
			ax.set_title(title)
			ax.grid(False)
			ax.xaxis.grid(xgrid, which='major')
			ax.yaxis.grid(ygrid, which='major')
			frame = ax.axesPatch
			frame.set_edgecolor(frame.get_facecolor())
			# Specify a line in axes coords to represent the left and bottom axes.
			bottom = Line2D([0, 1], [0, 0], transform=ax.transAxes)
			left   = Line2D([0, 0], [0, 1], transform=ax.transAxes)
			ax.add_line(bottom)
			ax.add_line(left)
			ax.set_xticks([barwidth/2+x+0.15 for x in xlocations])
			ax.set_xticklabels(labels)
			ax.set_xlim(0, xlocations[-1]+barwidth*2)
			labels = ax.get_xticklabels() + ax.get_yticklabels()
			for label in labels:
				label.set_size(textsize)           
			
			canvas.draw()
			size = canvas.get_renderer().get_canvas_width_height()
			buf = canvas.tostring_rgb()
			im = PILImage.fromstring('RGB', size, buf, 'raw', 'RGB', 0, 1)
			im.fp = "PILIMAGE"
			imageData = ImageReader(im)

			c.drawImage(imageData, 0, 0, width, height, mask)

		## All done, restore the canvas state to how we found it (important because
		## rotating, scaling, etc. are cumulative, not absolute and we don't want
		## to start with a canvas in an unknown state.)
		c.restoreState()
		return deferred, neededHeight


	def getStory(self, obj):
		width = self.getPt(obj.getProp("width"))
		padLeft = self.getPt(obj.getProp("padLeft"))
		padRight = self.getPt(obj.getProp("padRight"))
		padTop = self.getPt(obj.getProp("padTop"))
		padBottom = self.getPt(obj.getProp("padBottom"))
		columnCount = obj.getProp("columnCount")
		columnWidth = width/columnCount

		styles_ = styles.getSampleStyleSheet()

		objects = obj["Objects"]
		story = []
		for fobject in objects:
			objNeededHeight = 0

			t = fobject.__class__.__name__
			s = styles_[fobject.getProp("style")]
			expr = fobject.getProp("expr", returnException=True)

			if isinstance(s, basestring):
				expr = expr.encode(self.Encoding)
			else:
				expr = unicode(expr)
			s = copy.deepcopy(s)

			if fobject.has_key("fontSize"):
				s.fontSize = fobject.getProp("fontSize")

			if fobject.has_key("fontName"):
				s.fontName = fobject.getProp("fontName")
				
			if fobject.has_key("leading"):
				s.leading = fobject.getProp("leading")

			if fobject.has_key("spaceAfter"):
				s.spaceAfter = fobject.getProp("spaceAfter")
	
			if fobject.has_key("spaceBefore"):
				s.spaceBefore = fobject.getProp("spaceBefore")

			if fobject.has_key("leftIndent"):
				s.leftIndent = fobject.getProp("leftIndent")

			if fobject.has_key("firstLineIndent"):
				s.firstLineIndent = fobject.getProp("firstLineIndent")

			if t.lower() == "paragraph":
				paras = expr.splitlines()
				for idx, para in enumerate(paras):
					if len(para) == 0: 
						# Blank line
						p = platypus.Spacer(0, s.leading)
					else:
						def escapePara(para):
							words = para.split(" ")
							for idx, word in enumerate(words):
								if "&" in word and ";" not in word:
									word = word.replace("&", "&amp;")
								if "<" in word and ">" not in word:
									word = word.replace("<", "&lt;")
								words[idx] = word
							return " ".join(words)
						para = escapePara(para)
						p = ParaClass(para, s)
					p_height = p.wrap(columnWidth-padLeft-padRight, None)[1]
					objNeededHeight += p_height
					story.append((p, p_height))

				def hackDeferredPara():
					"""When a paragraph wraps to the next page, the last line won't print if this isn't done."""
					append_p = ParaClass("Hack: see hackDeferredPara() in reportWriter.py", s)
					p_height = p.wrap(99999, None)[1]
					story.append((append_p, p_height))
				if obj.getProp("Height") is None and paras:
					hackDeferredPara()

		neededHeight = objNeededHeight + padTop + padBottom
		return story, neededHeight


	def getColorTupleFromReportLab(self, val):
		"""Given a color tuple in reportlab format (values between 0 and 1), return
		a color tuple in 0-255 format."""
		return tuple([int(rgb*255) for rgb in val])


	def getReportLabColorTuple(self, val):
		"""Given a color tuple in rgb format (values between 0 and 255), return
		a color tuple in reportlab 0-1 format."""
		return tuple([rgb/255.0 for rgb in val])


	def ptToUnit(self, pt, unit):
		"""Given a numeric pt like 36, return a string like '0.5 in'.

		Warning, this isn't exact, and isn't intended to be.
		"""
		if unit == "in":
			return "%.4f in" % (pt/units.inch,)
		elif unit == "pt":
			return "%s pt" % (pt,)
		# hail mary that rl has the requested unit:
		return "%.3f %s" % (pt / getattr(units, unit, 1), unit)


	def getPt(self, val):
		"""Given a string or a number, convert the value into a numeric pt value.
	
		Strings can have the unit appended, like "3.5 in", "2 cm", "3 pica", "10 mm".
	
		> print self.getPt("1 in")
		72
		> print self.getPt("1")
		1
		> print self.getPt(1)
		1
		"""
		if isinstance(val, (int, long, float)):
			# return as-is as the pt value.
			return val
		else:
			# try to run it through reportlab's units.toLength() function:
			return units.toLength(val)
	
	
	def printBandOutline(self, band, x, y, width, height):
			## draw a dotted rectangle around the entire band, and type a small faded 
			## caption at the origin of the band.
			c = self.Canvas
			c.saveState()
			c.setLineWidth(0.75)
			c.setStrokeColorRGB(0.8, 0.5, 0.7)
			c.setDash(1, 2)
			c.rect(x, y, width, height)
			c.setFont("Helvetica", 8)
			c.setFillColor((0.6, 0.8, 0.7))
			c.drawString(x, y, band)
			c.restoreState()
		
		
	def write(self, save=True):
		"""Write the PDF file based on the ReportForm spec.
		
		If the save argument is True (the default), the PDF file will be
		saved and closed after the report form has been written. If False, 
		the PDF file will be left open so that additional pages can be added 
		with another call, perhaps after creating a different report form.
		"""
		self._calcObjectHeights = {}
		_form = self.ReportForm
		if _form is None:
			raise ValueError("ReportForm must be set first.")

		_form.reportWriter = self

		_outputFile = self.OutputFile

		pageSize = self.getPageSize()		
		pageWidth, pageHeight = pageSize
		self._pageNumber = 0

		c = self.Canvas
		if not c:
			# Create the reportlab canvas:
			c = self._canvas = canvas.Canvas(_outputFile, pagesize=pageSize)

		c.setAuthor(_form.getProp("Author"))
		c.setKeywords(_form.getProp("Keywords"))	
		c.setSubject(_form.getProp("Subject"))	
		c.setTitle(_form.getProp("Title"))
	
		# Get the number of columns:
		columnCount = _form.getProp("columnCount")
		

		# Initialize the groups list:
		groups = _form.get("groups", ())
		self._groupValues = {}
		for group in groups:
			vv = {}
			vv["curVal"] = None
			self._groupValues[group.get("expr")] = vv

		groupsDesc = [i for i in groups]
		groupsDesc.reverse()

		# Initialize the variables list:
		variables = _form.get("variables", ())
		self._variableValues = {}
		self.Variables = CaselessDict()
		for variable in variables:
			vv = {}
			vv["value"] = None
			vv["curReset"] = None
			varName = variable.get("Name")
			if varName:
				self.Variables[varName] = variable.getProp("InitialValue")
				self._variableValues[varName] = vv

		self._spanningObjects = {}
		self._recordNumber = 0
		self._currentColumn = 0

		## Let the page header have access to the first record:
		if len(self.Cursor) > 0:
			self.Record = self.Cursor[0]

		def processVariables(forceReset=False):
			"""Apply the user's expressions to the current value of all the report vars.

			This is called once per record iteration, before the detail for the current
			band is printed..
			"""
			variables = self.ReportForm.get("variables", ())
			for variable in variables:
				varName = variable.get("Name")
				if not varName:
					continue
				resetAt = variable.getProp("resetAt")
				vv = self._variableValues[varName]
				curReset = vv.get("curReset")
				if resetAt != curReset:
					# resetAt tripped: value to initial value
					self.Variables[varName] = variable.getProp("InitialValue")
				if not forceReset:
					vv["curReset"] = resetAt

				# run the variable expression to get the current value:
				#vv["value"] = eval(variable["expr"])
				vv["value"] = variable.getProp("expr", returnException=True)

				# update the value of the public variable:
				self.Variables[varName] = vv["value"]			
					

		def printBand(band, y=None, group=None, deferred=None):
			"""Generic function for printing any band."""

			_form = self.ReportForm
			page = _form["Page"]

			# Get the page margins into variables:
			ml = self.getPt(page.getProp("MarginLeft"))
			mt = self.getPt(page.getProp("MarginTop"))
			mr = self.getPt(page.getProp("MarginRight"))
			mb = self.getPt(page.getProp("MarginBottom"))
		
			# Page header/footer origins are needed in various places:
			pageHeaderOrigin = (ml, pageHeight - mt 
					- self.getPt(_form["PageHeader"].getProp("Height")))
			pageFooterOrigin = (ml, mb)
		
			workingPageWidth = pageWidth - ml - mr
			columnWidth = workingPageWidth / columnCount
#			print workingPageWidth / 72, columnWidth / 72
#			print columnWidth, columnCount


			if y is None:
				y = pageHeaderOrigin[1]

			try:
				if group is not None:
					bandDict = group[band]
				else:
					bandDict = _form[band]
			except KeyError:
				# Band name doesn't exist.
				return y

			if band.lower() == "pagefooter" and bandDict.getProp("Height") == None:
				raise ValueError, "PageFooter height must be fixed (not None)."

			pf = _form.get("pageFooter")
			if pf is None or pf is bandDict:
				pfHeight = 0
			else:
				pfHeight = pf.getProp("Height")
				if pfHeight is None:
					pfHeight = self.getBandHeight(pf)
				pfHeight = self.getPt(pfHeight)

			if band.lower() == "reportend" and bandDict.getProp("PageBreakBefore"):
				endPage()
				beginPage()
	
			if bandDict.getProp("show", returnException=True) == False:
				return y
	
			self.ReportForm.Bands[band] = CaselessDict()

			bandHeight = self.getBandHeight(bandDict)
			if not deferred:
				y -= bandHeight

			width = pageWidth - ml - mr

			# Set this property as quickly as possible as other properties (y, for example)
			# could depend on it.
			self.ReportForm.Bands[band]["Height"] = bandHeight

			def getTotalBandHeight():
				maxBandHeight = bandHeight
				if deferred:
					for obj, obj_deferred, neededHeight in deferred:
						needed = neededHeight
						maxBandHeight = max(maxBandHeight, neededHeight)
				else:
					for obj in bandDict.get("Objects", []):
						if obj.getProp("Height") is None:
							story = self.getStory(obj)
							storyheight = story[1]
							needed = storyheight + bandHeight - self.getPt(obj.getProp("y"))  ## y could be dep. on band height.
							maxBandHeight = max(maxBandHeight, needed)
				availableHeight = y - (pageFooterOrigin[1] + pfHeight)
				if (maxBandHeight - bandHeight) > availableHeight:
					# Signal that we need a page change as there isn't room:
					return None
				return maxBandHeight

			maxBandHeight = getTotalBandHeight()

			if band in ("groupHeader", "groupFooter", "detail", "ReportBegin", "ReportEnd"):
				extraHeight = 0
				if band == "groupHeader":
					# Also account for the height of the first detail record: don't print the
					# group header on this page if we don't get at least one detail record
					# printed as well. Actually, this should be reworked so that any subsequent
					# group header records get accounted for as well...
					b = _form["detail"]
					extraHeight = self.getBandHeight(b)

				check = pageFooterOrigin[1] + pfHeight + extraHeight

				if y < check or maxBandHeight is None:
					if self._currentColumn >= columnCount-1:
						endPage()
						beginPage()
					else:
						self._currentColumn += 1
					y = pageHeaderOrigin[1]
					maxBandHeight = getTotalBandHeight()
					if band == "detail":
						y = reprintGroupHeaders(y)
					if not deferred:
						y -= bandHeight
				
			# Non-detail band special cases:
			if band == "pageHeader":
				x,y = pageHeaderOrigin
			elif band == "pageFooter":
				x,y = pageFooterOrigin
			elif band in ("pageBackground", "pageForeground"):
				x,y = 0,1
				width, height = pageWidth-1, pageHeight-1

			x = ml + (self._currentColumn * columnWidth)
				
			self.ReportForm.Bands[band]["x"] = x
			self.ReportForm.Bands[band]["y"] = y
			self.ReportForm.Bands[band]["Width"] = width
			self.ReportForm.Bands[band]["TotalHeight"] = maxBandHeight	

			if self.ShowBandOutlines:
				self.printBandOutline("%s (record %s)" % (band, self.RecordNumber), 
						x, y, width, bandHeight)

			del_deferred_idxs = []
			objects = bandDict.get("Objects", [])
			was_deferred = False
			if deferred:
				was_deferred = True
				objects = deferred
			for idx, obj in enumerate(objects):
				if isinstance(obj, tuple):
					# deferred (obj, obj_deferred)
					obj, obj_deferred, neededHeight = obj
				else:
					obj_deferred = None
					neededHeight = 0
				show = obj.getProp("show", returnException=True)
				if show == False:
					continue

				x1 = self.getPt(obj.getProp("x"))
				y1 = obj_y = self.getPt(obj.getProp("y"))
				x1 = x + x1
				if obj_deferred:
					y1 = y
				else:
					y1 = y + y1

				if obj.__class__.__name__ == "SpanningLine":
					self.storeSpanningObject(obj, (x1, y1), group)
					continue

				availableHeight = (y + bandHeight) - (pageFooterOrigin[1] + pfHeight)
				obj_height = obj.getProp("height")
				if obj_height is not None:
					obj_height = self.getPt(obj_height)
					if availableHeight > obj_height:
						availableHeight = obj_height
				if bandDict.getProp("height") is not None:
					if availableHeight > obj_y:
						availableHeight = obj_y
				#availableHeight = min(availableHeight, bandHeight+y)
				new_obj_deferred, neededHeight = self.draw(obj, (x1, y1),	availableHeight=availableHeight,
						deferred=obj_deferred)

				if bandDict.getProp("height") is not None:
					# Band height is fixed; cancel any deferrals.
					new_obj_deferred = None

				if new_obj_deferred:
					if obj_deferred:
						# was already deferred, and now deferred again. WARNING: if para longer 
						# than a page, we'll recurse forever. FIXME.
						deferred[idx] = (obj, new_obj_deferred, neededHeight)
					else:
						# new deferral.
						if deferred is None:
							deferred = []
						deferred.append((obj, new_obj_deferred, neededHeight))
				else:
					if obj_deferred:
						# need to delete the old deferral
						del_deferred_idxs.append(idx)

			if band == "groupFooter":
				self.drawSpanningObjects((x,y), group)
				self.clearSpanningObjects(group)

			del_deferred_idxs.sort(reverse=True)
			for idx in del_deferred_idxs:
				del(deferred[idx])

			if band.lower() == "reportbegin" and bandDict.getProp("PageBreakAfter"):
				endPage()
				beginPage()

			if was_deferred and not deferred:
				# just printed the last page of deferreds
				return y - maxBandHeight

			elif deferred:
				# the deferred objs will print on the next page. RECURSE WARNING.
				dy = printBand(band=band, y=-1, group=group, deferred=deferred)
				return dy
			else:
				# no deferreds ever involved
				if maxBandHeight > bandHeight:
					y -= (maxBandHeight-bandHeight)
				return y


		def beginPage():
			# Print the static bands that appear below detail in z-order:
			self._pageNumber += 1
			for band in ("pageBackground", "pageHeader", "pageFooter"):
				printBand(band)
			self._brandNewPage = True

		def endPage():
			self._currentColumn = 0
			x = self.getPt(self.ReportForm["Page"].getProp("MarginLeft"))
			self.drawSpanningObjects((x,y))
			printBand("pageForeground")
			self.Canvas.showPage()
		
		def reprintGroupHeaders(y):
			for group in groups:
				reprint = group.get("reprintHeaderOnNewPage")
				if reprint is not None:
					reprint = eval(reprint)
					if reprint is not None:
						y = printBand("groupHeader", y, group)
			return y

		# Need to process the variables before the first beginPage() in case
		# any of the static bands reference the variables.
		processVariables()
		beginPage()
		y = printBand("ReportBegin")

		# Print the dynamic bands (Detail, GroupHeader, GroupFooter):
		y = None
		for cursor_idx, record in enumerate(self.Cursor):
			_lastRecord = self.Record
			self.Record = record

			# print group footers for previous group if necessary:
			if cursor_idx > 0:
				# First pass, iterate through the groups outer->inner, and if any group
				# expr has changed, reset the curval for the group and all child groups.
				resetCurVals = False
				for idx, group in enumerate(groups):
					vv = self._groupValues[group["expr"]]
					if resetCurVals or vv["curVal"] != group.getProp("expr"):
						resetCurVals = True
						vv["curVal"] = None

				# Second pass, iterate through the groups inner->outer, and print the 
				# group footers for groups that have changed.
				for idx, group in enumerate(groupsDesc):
					vv = self._groupValues[group["expr"]]
					if vv["curVal"] != group.getProp("expr"):
						# We need to temporarily move back to the last record so that the
						# group footer reflects what the user expects.
						self.Record = _lastRecord
						y = printBand("groupFooter", y, group)
						self.Record = record

			if cursor_idx > 0:						
				# Any report variables need their values evaluated again:
				processVariables()

			# print group headers for this group if necessary:
			brandNewPage = False
			for idx, group in enumerate(groups):
				vv = self._groupValues[group["expr"]]
				if vv["curVal"] != group.getProp("expr"):
					rp = eval(group.get("resetPageNumber", "False"))
					if rp and self._recordNumber == 0:
						self._pageNumber = 1
					elif rp:
						self._pageNumber = 0
					vv["curVal"] = group.getProp("expr")
					np = eval(group.get("startOnNewPage", "False")) \
							and self.RecordNumber > 0
					if np and not brandNewPage:
						endPage()
						beginPage()
						y = None
						brandNewPage = True  ## don't start multiple new pages
					y = printBand("groupHeader", y, group)

			# print the detail band:
			y = printBand("detail", y)
			self._recordNumber += 1


		# print the group footers for the last group:
		for idx, group in enumerate(groupsDesc):
			y = printBand("groupFooter", y, group)

		y = printBand("ReportEnd", y)

		endPage()
		
		if save:
			if self.OutputFile is not None:
				c.save()
			self._canvas = None


	def getBandHeight(self, bandDict):
		"""Return the height of the band.

		If the band's Height property is None, the height will be
		calculated based on the objects in the band.
		"""

		bandHeight = bandDict.getProp("Height")
		if bandHeight is not None:
			# explicitly-set height
			return self.getPt(bandHeight)

		# dynamic height: figure out based on the objects in the band.
		bandHeight = 0
		objects = bandDict.get("objects", [])

		for obj in objects:
			obj_y = self.getPt(obj.getProp("y"))
			obj_ht = obj.getProp("Height")
			if obj.getProp("Show") == False:
				continue
			if obj_ht is None:
				# Dynamic object height: TotalHeight gets calc'd for the
				# object elsewhere. Assume a height of 0 but still allow
				# the position of the object to have an effect on this calc.
				obj_ht = 0
			else:
				# object height is fixed.
				obj_ht = self.getPt(obj_ht)
			thisHeight = obj_y + obj_ht
			bandHeight = max(thisHeight, bandHeight)
		return bandHeight


	def getPageSize(self):
		## Set the Page Size:
		# get the string pageSize value from the spec file:
		_form = self.ReportForm
		page = _form["page"]
		pageSize = page.getProp("size")

		if isinstance(pageSize, basestring):
			# reportlab expects the pageSize to be upper case:
			pageSize = pageSize.upper()
			# convert to the reportlab pageSize value (tuple(width,height)):
			pageSize = eval("pagesizes.%s" % pageSize)
		else:
			pageSize = (self.getPt(pageSize[0]), self.getPt(pageSize[1]))
		# run it through the portrait/landscape filter:
		orientation = page.getProp("orientation").lower()
		func = eval("pagesizes.%s" % orientation)
		return func(pageSize)


	def _getUniqueName(self):
		"""Returns a name that should be unique, but it doesn't check to make sure."""
		import time, md5, random
		t1 = time.time()
		t2 = t1 + random.random()
		base = md5.new(str(t1 +t2))
		name = "_" + base.hexdigest()
		return name
	

	def _getEmptyForm(self):
		"""Returns a report form with the minimal number of elements.

		Defaults will be filled in. Used by the report designer.
		"""
		report = Report(self)
		return report


	def _isModified(self):
		"""Returns True if the report form definition has been modified.

		Used by the report designer.
		"""
		return not (self.ReportForm is None 
				or self.ReportForm.getMemento() == self._reportFormMemento)


	def _elementSort(self, x, y):
		positions = CaselessDict({"author": 0, "title": 2,
				"subject": 3, "keywords": 4,
				"columnCount": 5, "page": 10, 
				"groups": 50, "variables": 40, "pageBackground": 55, 
				"pageHeader": 60, "groupHeader": 65, "detail": 70, 
				"groupFooter": 75, "pageFooter": 80, "pageForeground": 90, 
				"objects": 99999, "testcursor": 999999})

		posX = positions.get(x, -1)
		posY = positions.get(y, -1)
		if posY > posX:
			return -1
		elif posY < posX:
			return 1
		return cmp(x.lower(), y.lower())


	def _getXMLDictFromForm(self, form, d=None):
		"""Recursively generate the dict format required for the dicttoxml() function."""
		if d is None:
			d = {"name": "Report", "children": []}

		elements = form.keys()
		elements.sort(self._elementSort)

		for element in elements:
			if element == "type":
				continue
			child = {"name": element, "children": []}
			if isinstance(form[element], basestring):
				child["cdata"] = form[element]
			elif element.lower() == "testcursor":
				cursor = []
				for row in form["testcursor"]:
					attr = {}
					for field in sorted(row):
						attr[field] = row[field]
					cursor.append({"name": "record", "attributes": attr})
					child["children"] = cursor

			elif element.lower() in ("objects", "variables", "groups"):
				objects = []
				for index in range(len(form[element])):
					formobj = form[element][index]
					obj = {"name": formobj.__class__.__name__, "children": []}
					props = formobj.keys()
					props.sort(self._elementSort)
					if formobj.has_key(element):
						# Recurse
						self._getXMLDictFromForm(formobj, obj)
					else:
						for prop in props:
							if prop != "type":
								if isinstance(formobj[prop], dict):
									# Recurse
									self._getXMLDictFromForm(formobj, obj)
									break
								else:
									if element.lower() != "groups":
										newchild = {"name": prop, "cdata": formobj[prop]}
										obj["children"].append(newchild)
					objects.append(obj)
				child["children"] = objects

			elif isinstance(form[element], dict):
				child = self._getXMLDictFromForm(form[element], child)

			d["children"].append(child)
		return d		


	def _getXMLFromForm(self, form):
		"""Returns a valid rfxml string from a report form dict."""
		# We need to first convert the report form dict into the dict format
		# as expected by the generic dicttoxml() function. This is a tree of
		# dicts with keys on 'cdata', 'children', 'name', and 'attributes'.
		d = self._getXMLDictFromForm(form)
		# Now that the dict is in the correct format, get the xml:
		return dicttoxml(d, header=self._getXmlHeader(), 
				linesep={1: os.linesep*1})


	def _getXmlHeader(self):
		"""Returns the XML header for the rfxml document."""
		header = """<?xml version="1.0" encoding="utf-8" standalone="yes"?>

<!-- 
		This is a Dabo report form xml (rfxml) document, describing a
		report form. It was generated by the Dabo Report Writer, and can
		be edited by hand or by using the Dabo Report Designer.
-->


"""
		return os.linesep.join(header.splitlines())


	def _setMemento(self):
		"""Set the memento of the report form, which is the pristine version."""
		if self._clearMemento:
			if self._reportForm:
				m = self._reportForm.getMemento()
			else:
				m = {}
			self._reportFormMemento = m

	
	def _getFormFromXMLDict(self, xmldict, formdict=None, level=0):
		"""Recursively generate the form dict from the given xmldict."""

		if formdict is None:
			formdict = Report(None)

		if xmldict.has_key("children"):
			# children with name of "objects", "variables" or "groups" are band 
			# object lists, while other children are sub-dictionaries.
			for child in xmldict["children"]:
				if child["name"].lower() == "testcursor":
					# Previously, we saved all the field types in the attributes. We need
					# to ignore those if present, and make report["TestCursor"] a list of
					# records.
					cursor = formdict.addElement(TestCursor)
					if child.has_key("children"):
						for childrecord in child["children"]:
							cursor.addRecord(childrecord["attributes"])
				elif child.has_key("cdata"):
					formdict[child["name"]] = child["cdata"]
				elif child.has_key("attributes"):
					formdict[child["name"]] = child["attributes"]
				elif child.has_key("children"):
					if child["name"].lower() in ("objects", "groups", "variables"):
						coll = child["name"]
						formdict[coll] = self._getReportObject(coll, formdict)
						for obchild in child["children"]:
							reportObject = self._getReportObject(obchild["name"], formdict[coll])
							c = self._getFormFromXMLDict(obchild, reportObject, level+1)
							formdict[coll].append(c)
					else:
						reportObject = self._getReportObject(child["name"], formdict)
						formdict[child["name"]] = self._getFormFromXMLDict(child, 
								reportObject, level+1)

		return formdict


	def _getReportObject(self, objectType, parent):
		typeMapping = CaselessDict({"Report": Report, "Page": Page, 
				"Group": Group, "Variable": Variable,
				"PageBackground": PageBackground, "PageHeader": PageHeader, 
				"Detail": Detail, "PageFooter": PageFooter, 
				"GroupHeader": GroupHeader,	"GroupFooter": GroupFooter, 
				"PageForeground": PageForeground, "Rect": Rectangle,
				"Rectangle": Rectangle,
				"String": String, "Image": Image, "BarGraph": BarGraph, "Line": Line,
				"Frameset": Frameset, "Paragraph": Paragraph,
				"Variables": Variables, "Groups": Groups, "Objects": Objects,
				"TestCursor": TestCursor, "TestRecord": TestRecord,
				"SpanningLine": SpanningLine, "ReportBegin": ReportBegin,
				"ReportEnd": ReportEnd})

		cls = typeMapping.get(objectType)
		ref = cls(parent)
		return ref
		


	def _getFormFromXML(self, xml):
		"""Returns the report form dict given xml in rfxml format."""

		# Get the xml into a generic tree of dicts:
		xmldict = xmltodict(xml)

		if xmldict["name"].lower() == "report":
			form = self._getFormFromXMLDict(xmldict)
		else:
			print "This isn't a valid rfxml string."

		return form


	def _getBands(self):
		try:
			v = self._bands
		except AttributeError:
			v = self._bands = {}
		return v


	def _getCanvas(self):
		try:
			v = self._canvas
		except AttributeError:
			v = self._canvas = None
		return v


	def _getCursor(self):
		if self.UseTestCursor:
			try:
				v = self.ReportForm["TestCursor"]
			except KeyError:
				v = []
			liveTest = []
			for record in v:
				liveRecord = CaselessDict()
				for f, v in record.items():
					liveRecord[f] = eval(v)
				liveTest.append(liveRecord)
			v = liveTest
		else:
			try:
				v = self._cursor
			except AttributeError:
				v = self._cursor = []
		return v

	def _setCursor(self, val):
		self._cursor = val
		self.UseTestCursor = False
		

	def _getEncoding(self):
		try:
			v = self._encoding
		except AttributeError:
			v = self._encoding = "utf-8"
		return v

	def _setEncoding(self, val):
		self._encoding = val


	def _getHomeDirectory(self):
		try:
			v = self._homeDirectory
		except AttributeError:
			v = self._homeDirectory = os.getcwd()
		return v

	def _setHomeDirectory(self, val):
		self._homeDirectory = val


	def _getOutputFile(self):
		try:
			v = self._outputFile
		except AttributeError:
			v = self._outputFile = None
		return v
		
	def _setOutputFile(self, val):
		if not isinstance(val, basestring):
			# We assume it is either a file or file-like object
			self._outputFile = val
		else:
			s = os.path.split(val)
			if len(s[0]) == 0 or os.path.exists(s[0]):
				self._outputFile = val
			else:
				raise ValueError("Path '%s' doesn't exist." % s[0])

	def _getPageNumber(self):
		return self._pageNumber

	def _getRecord(self):
		try:
			v = self._record
		except AttributeError:
			v = self._record = {}
		return v

	def _setRecord(self, val):
		self._record = val
		if self.ReportForm:
			# allow access from the live report object:
			self.ReportForm._liveRecord = val


	def _getRecordNumber(self):
		try:
			v = self._recordNumber
		except AttributeError:
			v = self._recordNumber = None
		return v


	def _getReportForm(self):
		try:
			v = self._reportForm
		except AttributeError:
			v = self._reportForm = None
		return v
		
	def _setReportForm(self, val):
		self._reportForm = val
		self._setMemento()
		self._reportFormXML = None
		self._reportFormFile = None
		

	def _getReportFormFile(self):
		try:
			v = self._reportFormFile
		except AttributeError:
			v = self._reportFormFile = None
		return v
		
	def _setReportFormFile(self, val):
		if val is None:
			self._reportFormFile = None
			self._reportFormXML = None
			self._reportForm = None
			self._setMemento()
			return

		if os.path.exists(val):
			ext = os.path.splitext(val)[1] 
			if ext == ".py":
				# The file is a python module, import it and get the report dict:
				s = os.path.split(val)
				sys.path.append(s[0])
				exec("import %s as form" % s[1].split(".")[0])
				sys.path.pop()
				self._reportForm = form.report
				self._setMemento()
				self._reportFormXML = None
					
			elif ext == ".rfxml":
				# The file is a report form xml file. Open it and set ReportFormXML:
				self._reportFormXML = open(val, "r").read()
				self._reportForm = self._getFormFromXML(self._reportFormXML)
				self._setMemento()
			else:
				raise ValueError("Invalid file type.")
			self._reportFormFile = val
			self.HomeDirectory = os.path.join(os.path.split(val)[:-1])[0]
		else:
			raise ValueError("Specified file does not exist.")
		

	def _getReportFormXML(self):
		try:
			v = self._reportFormXML
		except AttributeError:
			v = self._reportFormXML = None
		return v
		
	def _setReportFormXML(self, val):
		self._reportFormXML = val
		self._reportFormFile = None
		self._reportForm = self._getFormFromXML(self._reportFormXML)
		self._setMemento()
		

	def _getShowBandOutlines(self):
		try:
			v = self._showBandOutlines
		except AttributeError:
			v = False
		return v

	def _setShowBandOutlines(self, val):
		self._showBandOutlines = bool(val)


	def _getUseTestCursor(self):
		try:
			v = self._useTestCursor
		except AttributeError:
			v = self._useTestCursor = False
		return v

	def _setUseTestCursor(self, val):
		self._useTestCursor = bool(val)
		if val:
			self._cursor = None

	Bands = property(_getBands, None, None,
		_("Provides runtime access to bands of the currently running report."))

	Canvas = property(_getCanvas, None, None,
		_("Returns a reference to the reportlab canvas object."))

	Cursor = property(_getCursor, _setCursor, None, 
		_("Specifies the data cursor that the report runs against."))

	Encoding = property(_getEncoding, _setEncoding, None,
		_("Specifies the encoding for unicode strings.  (str)"))

	HomeDirectory = property(_getHomeDirectory, _setHomeDirectory, None,
		_("""Specifies the home directory for the report.

		Resources on disk (image files, etc.) will be looked for relative to the
		HomeDirectory if specified with relative pathing. The HomeDirectory should
		be the directory that contains the report form file. If you set 
		self.ReportFormFile, HomeDirectory will be set for you automatically."""))

	OutputFile = property(_getOutputFile, _setOutputFile, None,
		_("Specifies the output PDF file (name or file object)."))

	PageNumber = property(_getPageNumber, None, None, 
			_("""Returns the current page number at runtime."""))

	Record = property(_getRecord, _setRecord, None,
		_("""Specifies the dictionary that represents the current record.

		The report writer will automatically fill this in during the running 
		of the report. Allows expressions in the report form like:

			self.Record["cFirst"]
		"""))

	RecordNumber = property(_getRecordNumber, None, None,
		_("Returns the current record number of Cursor."))

	ReportForm = property(_getReportForm, _setReportForm, None,
		_("Specifies the python report form data dictionary."))
	
	ReportFormFile = property(_getReportFormFile, _setReportFormFile, None,
		_("Specifies the path and filename of the report form spec file."))
		
	ReportFormXML = property(_getReportFormXML, _setReportFormXML, None,
		_("Specifies the report format xml."))

	ShowBandOutlines = property(_getShowBandOutlines, _setShowBandOutlines, None,
		_("""Specifies whether the report bands are printed with outlines for
		debugging and informational purposes. In addition to the band, there is also
		a caption with the band name at the x,y origin point for the band."""))
		
	UseTestCursor = property(_getUseTestCursor, _setUseTestCursor, None, 
		_("Specifies whether the TestCursor in the spec file is used."))
			
			
if __name__ == "__main__":
	rw = ReportWriter()
	rw.ShowBandOutlines = True
	rw.UseTestCursor = True

	if len(sys.argv) > 1:
		for reportForm in sys.argv[1:]:
			if reportForm == "tempfile":
				import tempfile
				print "Creating tempfile.pdf from samplespec.rfxml"
				rw.ReportFormFile = "samplespec.rfxml"
				rw.OutputFile = tempfile.TemporaryFile()
				rw.write()
				f = open("tempfile.pdf", "wb")
				rw.OutputFile.seek(0)
				f.write(rw.OutputFile.read())
				f.close()
			else:
				output = "./%s.pdf" % os.path.splitext(reportForm)[0]
				print "Creating %s from report form %s..." % (output, reportForm)
				rw.ReportFormFile = reportForm
				rw.OutputFile = output
				rw.write()
	else:
		print "Usage: reportWriter <specFile> [<specFile>...]"
