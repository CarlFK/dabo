import os
import reportlab.pdfgen.canvas as canvas
import reportlab.graphics.shapes as shapesimport reportlab.lib.pagesizes as pagesizes
import reportlab.lib.units as units
#import reportlab.lib.colors as colors


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
	feeding it the Cursor, Report Form, and OutputName.

	More documentation will come.
	"""

	## The following defaults will be used for properties that weren't defined in
	## the spec file (no need to explicitly define properties if you want the 
	## defaults). Subclass to change defaults to your needs.
	default_pageSize = "letter"            # you may want 'a4' outside of the US
	default_pageOrientation = "portrait"   # the other option is "landscape"
	default_width = 55
	default_height = 18
	default_x = 0
	default_y = 0
	default_rotation = 0                   # (0-359)
	default_hAnchor = "left"               # hor. anchor (what x is relative to)
	default_vAnchor = "bottom"             # vert. anchor (what y is relative to)
	default_strokeWidth = 1                # the brush stroke width for shapes
	default_fillColor = None               # None: transparent or (r,g,b) tuple
	default_strokeColor = (0, 0, 0)        # (black)
	default_strokeDashArray = None         # (use for dashed lines)
	default_borderWidth = 0                # width of border around strings
	default_borderColor = (0, 0, 0)        # color of border around strings
	default_align = "left"                 # string alignment
	default_fontName = "Helvetica"
	default_fontSize = 10
	default_fontColor = (0, 0, 0)      
	default_imageMask = None               # Transparency mask for images
	default_scaleMode = "scale"            # "clip" or "scale" for images.


	def draw(self, object, origin):
		"""Draw the given object on the Canvas.

		The object is a dictionary containing properties, and	origin is the (x,y)
		tuple where the object's (x,y) properties should be relative to.
		"""
		c = self.Canvas
		x,y = origin

		c.saveState()
	
		try: 
			width = self.getPt(eval(object["width"]))
		except (KeyError, TypeError, ValueError): 
			width = self.default_width
	
		try: 
			height = self.getPt(eval(object["height"]))
		except (KeyError, TypeError, ValueError): 
			height = self.default_height
	
		try: 
			rotation = eval(object["rotation"])
		except KeyError:
			rotation = self.default_rotation
	
		try:
			hAnchor = eval(object["hAnchor"])
		except:
			hAnchor = self.default_hAnchor
	
		try:
			vAnchor = eval(object["vAnchor"])
		except:
			vAnchor = self.default_vAnchor
	
		if hAnchor == "right":
			x = x - width
		elif hAnchor == "center":
			x = x - (width / 2)
		
		if vAnchor == "top":
			y = y - height
		elif vAnchor == "center":
			y = y - (height / 2)
	
		if object["type"] == "rect":
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
	
			try:
				props["strokeWidth"] = self.getPt(eval(object["strokeWidth"]))
			except KeyError: 
				props["strokeWidth"] = self.default_strokeWidth
	
			try:
				props["fillColor"] = eval(object["fillColor"])
			except KeyError:
				props["fillColor"] = self.default_fillColor
	
			try:
				props["strokeColor"] = eval(object["strokeColor"])
			except KeyError:
				props["strokeColor"] = self.default_strokeColor
	
			try:
				props["strokeDashArray"] = eval(object["strokeDashArray"])
			except KeyError:
				props["strokeDashArray"] = self.default_strokeDashArray
	
			r = shapes.Rect(0, 0, width, height)
			r.setProperties(props)
			d.add(r)
			d.drawOn(c, x, y)
	
		elif object["type"] == "string":
			c.translate(x, y)
			c.rotate(rotation)
			try: 
				borderWidth = self.getPt(eval(object["borderWidth"]))
			except KeyError: 
				borderWidth = self.default_borderWidth
	
			try: 
				borderColor = eval(object["borderColor"])
			except KeyError: 
				borderColor = self.default_borderColor
	
			c.setLineWidth(borderWidth)
			c.setStrokeColor(borderColor)
	
			if borderWidth > 0:
				stroke = 1
			else:
				stroke = 0
	
			# clip the text to the specified width and height
			p = c.beginPath()
	
			p.rect(0, 0, width, height)
			c.clipPath(p, stroke=stroke)
	
			try:
				align = eval(object["align"])
			except KeyError:
				align = self.default_align

			funcs = {"center": c.drawCentredString,
				  "right": c.drawRightString,
				  "left": c.drawString}
			func = funcs[align]
			if eval(object["align"]) == "center":
				posx = (width / 2)
			elif eval(object["align"]) == "right":
				posx = width
			else:
				posx = 0
	
			try:
				fontName = eval(object["fontName"])
			except KeyError:
				fontName = self.default_fontName
	
			try:
				fontSize = eval(object["fontSize"])
			except KeyError:
				fontSize = self.default_fontSize
	
			try:
				fontColor = eval(object["fontColor"])
			except KeyError:
				fontColor = self.default_fontColor
	
			c.setFillColor(fontColor)
			c.setFont(fontName, fontSize)
	
			s = eval(object["expr"])
			func(posx,0,s)
	
		elif object["type"] == "image":
			c.translate(x, y)
			c.rotate(rotation)
			try: 
				borderWidth = self.getPt(eval(object["borderWidth"]))
			except KeyError: 
				borderWidth = self.default_borderWidth
	
			try: 
				borderColor = eval(object["borderColor"])
			except KeyError: 
				borderColor = self.default_borderColor
	
			c.setLineWidth(borderWidth)
			c.setStrokeColor(borderColor)
	
			if borderWidth > 0:
				stroke = 1
			else:
				stroke = 0
	
			try: 
				mask = eval(object["imageMask"])
			except: 
				mask = self.default_imageMask
	
			try:
				mode = eval(object["scaleMode"])
			except:
				mode = self.default_scaleMode
	
			# clip around the outside of the image:
			p = c.beginPath()
			p.rect(-1, -1, width+2, height+2)
			c.clipPath(p, stroke=stroke)
	
			if mode == "clip":
				# Need to set w,h to None for the drawImage, which will draw it in its
				# "natural" state 1:1 pixel:point, which could flow out of the object's
				# width/height, resulting in clipping.
				width, height = None, None
			c.drawImage(eval(object["expr"]), 0, 0, width, height, mask)
		c.restoreState()


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
		if type(val) in (int, long, float):
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
			c.setLineWidth(0.1)
			c.setStrokeColorRGB(0.8, 0.5, 0.7)
			c.setDash(1, 2)
			c.rect(x, y, width, height)
			c.setFont("Helvetica", 8)
			c.setFillColor((0.6, 0.8, 0.7))
			c.drawString(x, y, band)
			c.restoreState()
		
		
	def write(self):			
		_form = self.ReportForm
		if _form is None:
			raise ValueError, "ReportForm must be set first."

		_outputName = self.OutputName
		if _outputName is None:
			raise ValueError, "OutputName must be set first."

		
		## Set the Page Size:
		# get the string pageSize value from the spec file:
		try:
			pageSize = eval(_form.Page["size"])
		except KeyError:
			pageSize = self.default_pageSize
		# reportlab expects the pageSize to be upper case:
		pageSize = pageSize.upper()
		# convert to the reportlab pageSize value (tuple(width,height)):
		pageSize = eval("pagesizes.%s" % pageSize)
		# run it through the portrait/landscape filter:
		try:
			orientation = eval(_form.Page["orientation"])
		except KeyError:
			orientation = self.default_pageOrientation
		func = eval("pagesizes.%s" % orientation)
		pageSize = func(pageSize)
		pageWidth, pageHeight = pageSize
		print "Page Size:", pageSize
		## end Page Size setting (refactor to a separate function)
		
		
		# Create the reportlab canvas:
		c = self._canvas = canvas.Canvas(_outputName, pagesize=pageSize)
		
		
		# Get the page margins into variables:
		ml = self.getPt(eval(_form.Page["marginLeft"]))
		mt = self.getPt(eval(_form.Page["marginTop"]))
		mr = self.getPt(eval(_form.Page["marginRight"]))
		mb = self.getPt(eval(_form.Page["marginBottom"]))
		
		# Page header/footer origins are needed in various places:
		pageHeaderOrigin = (ml, pageHeight - mt 
		                    - self.getPt(eval(_form.PageHeader["height"])))
		pageFooterOrigin = (ml, mb)
		
		
		
		
		# Print the static bands:
		for band in ("PageBackground", "PageHeader", "PageFooter"):
			self.Bands[band] = {}
			bandDict = eval("_form.%s" % band)
		
			# Find out geometry of the band and fill into report["bands"][band]
			x = ml
			if band == "PageHeader":
				y = pageHeaderOrigin[1]
			elif band == "PageFooter":
				y = pageFooterOrigin[1]
			elif band == "PageBackground":
				x,y = 0,1
			
			if band == "PageBackground":
				width, height = pageWidth-1, pageHeight-1
			else:
				width = pageWidth - ml - mr
				height = self.getPt(eval(bandDict["height"]))
		
			self.Bands[band]["x"] = x
			self.Bands[band]["y"] = y
			self.Bands[band]["width"] = width
			self.Bands[band]["height"] = height
		
			if self.ShowBandOutlines:
				self.printBandOutline(band, x, y, width, height)
		
			for object in bandDict["objects"]:
		
				if bandDict == _form.PageHeader:
					origin = pageHeaderOrigin
				elif bandDict == _form.PageFooter:
					origin = pageFooterOrigin
				elif bandDict == _form.PageBackground:
					origin = (0,1)
		
				x = self.getPt(eval(object["x"])) + origin[0]
				y = origin[1] + self.getPt(eval(object["y"]))
		
				self.draw(object, (x, y))
		
		# Print the dynamic bands (Detail, GroupHeader, GroupFooter):
		y = pageHeaderOrigin[1]
		groups = _form.Groups
		
		self._recordNumber = 0
		for record in self.Cursor:
			self.Record = record
			for band in ("Detail",):
				bandDict = eval("_form.%s" % band)
				self.Bands[band] = {}
		
				x = ml
				y = y - self.getPt(eval(bandDict["height"]))
				width = pageWidth - ml - mr
				height = self.getPt(eval(bandDict["height"]))
		
				self.Bands[band]["x"] = x
				self.Bands[band]["y"] = y
				self.Bands[band]["width"] = width
				self.Bands[band]["height"] = height
		
				if self.ShowBandOutlines:
					self.printBandOutline("%s (record %s)" % (band, self.RecordNumber), 
					                                     x, y, width, height)
				for object in bandDict["objects"]:
					x = ml + self.getPt(eval(object["x"]))
					y1 = y + self.getPt(eval(object["y"]))
					self.draw(object, (x, y1))
						
				self._recordNumber += 1
		
		c.save()



	def _setFormFromXML():
		## Called from _setReportFormFile() and _setReportFormXML().
		## Interprets the xml in ReportFormXML into a Python module, and sets
		## ReportForm to that module.
		pass


	def _getBands(self):
		try:
			v = self._bands
		except AttributeError:
			v = self._bands = {}
		return v

	Bands = property(_getBands, None, None,
		"""Provides runtime access to bands of the currently running report.""")


	def _getCanvas(self):
		try:
			v = self._canvas
		except AttributeError:
			v = self._canvas = None
		return v

	Canvas = property(_getCanvas, None, None,
		"""Returns a reference to the reportlab canvas object.""")	


	def _getCursor(self):
		if self.UseTestCursor:
			try:
				v = self.ReportForm.TestCursor
			except AttributeError:
				v = []
		else:
			try:
				v = self._cursor
			except AttributeError:
				v = self._cursor = None
		return v

	def _setCursor(self, val):
		self._cursor = val
		self.UseTestCursor = False
		
	Cursor = property(_getCursor, _setCursor, None, 
		"""Specifies the data cursor that the report runs against.""")


	def _getOutputName(self):
		try:
			v = self._outputName
		except AttributeError:
			v = self._outputName = None
		return v
		
	def _setOutputName(self, val):
		s = os.path.split(val)
		if os.path.exists(s[0]):
			self._outputName = val
		else:
			raise ValueError, "Path '%s' doesn't exist." % s[0]

	OutputName = property(_getOutputName, _setOutputName, None,
		"""Specifies the output file name, which will get written to in PDF format.""")


	def _getRecord(self):
		try:
			v = self._record
		except AttributeError:
			v = self._record = {}
		return v

	def _setRecord(self, val):
		self._record = val

	Record = property(_getRecord, _setRecord, None,
		"""Specifies the dictionary that represents the current record.

		The report writer will automatically fill this in during the running 
		of the report. Allows expressions in the report form like:

			self.Record['cFirst']
		""")


	def _getRecordNumber(self):
		try:
			v = self._recordNumber
		except AttributeError:
			v = self._recordNumber = None
		return v

	RecordNumber = property(_getRecordNumber, None, None,
		"""Returns the current record number of Cursor.""")


	def _getReportForm(self):
		try:
			v = self._reportForm
		except AttributeError:
			v = self._reportForm = None
		return v
		
	def _setReportForm(self, val):
		self._reportForm = val
		self._reportFormXML = None
		self._reportFormFile = None
		
	ReportForm = property(_getReportForm, _setReportForm, None,
		"""Specifies the python report form as a Python module.""")
	

	def _getReportFormFile(self):
		try:
			v = self._reportFormFile
		except AttributeError:
			v = self._reportFormFile = None
		return v
		
	def _setReportFormFile(self, val):
		if os.path.exists(val):
			ext = os.path.splitext(val)[1] 
			if ext == ".py":
				# The file is a python module, import it:
				s = os.path.split(val)
				sys.path.append(s[0])
				exec("import %s as form" % s[1])
				sys.path.pop()
				self._reportForm = form
				self._reportFormXML = None
					
			elif ext == ".rfxml":
				# The file is a report form xml file. Open it and set ReportFormXML:
				self._reportFormXML = open(val, "r").read()
				self._setFormFromXML()
			else:
				raise ValueError, "Invalid file type."
			self._reportFormFile = val
		else:
				raise ValueError, "Specified file does not exist."
		
	ReportFormFile = property(_getReportFormFile, _setReportFormFile, None,
		"""Specifies the path and filename of the report form spec file.""")
		

	def _getReportFormXML(self):
		try:
			v = self._reportFormXML
		except AttributeError:
			v = self._reportFormXML = None
		return v
		
	def _setReportFormXML(self, val):
		self._reportFormXML = val
		self._reportFormFile = None
		self._setFormFromXML()
		
	ReportFormXML = property(_getReportFormXML, _setReportFormXML, None,
		"""Specifies the report format xml.""")


	def _getShowBandOutlines(self):
		try:
			v = self._showBandOutlines
		except AttributeError:
			v = False
		return v

	def _setShowBandOutlines(self, val):
		self._showBandOutlines = bool(val)

	ShowBandOutlines = property(_getShowBandOutlines, _setShowBandOutlines, None,
		"""Specifies whether the report bands are printed with outlines for
		debugging and informational purposes. In addition to the band, there is also
		a caption with the band name at the x,y origin point for the band.""")
		

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

	UseTestCursor = property(_getUseTestCursor, _setUseTestCursor, None, 
		"""Specifies whether the TestCursor in the spec file is used.""")
			
			
if __name__ == "__main__":
	rw = ReportWriter()
	import samplespec
	rw.ReportForm = samplespec
	rw.OutputName = "./test.pdf"
	#rw.Cursor = [{"cArtist": "Cornershop"}]
	rw.ShowBandOutlines = True
	rw.UseTestCursor = True
	rw.write()
