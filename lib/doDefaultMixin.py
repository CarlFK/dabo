import inspect

class DoDefaultMixin(object):
	""" An alternative way to call superclass method code.
	
	Mix this class in to your classes, and you can now use the following
	form to call superclass methods:
	
		retval = cls.doDefault([args])
	
	instead of the usual:
	
		retval = super(cls, self).<methodName>([args])
	"""

	def doDefault(cls, *args, **kwargs):
		"""Call the superclass's method code, if any.

		Arguments are sent along to the super method, and the return value from 
		that super method is returned to the caller.

		Example:
			class A(dabo.ui.dForm):
				def afterInit(self):
					print "hi"
					return A.doDefault()

		Note that doDefault() must be called on the class, and not the self reference. 

		Also, due to the implementation, the calling class must use the 'self'
		convention - don't use 'this' or some other identifier for the class instance.
		"""
		
		frame = inspect.currentframe(1)
		self = frame.f_locals["self"]
		methodName = frame.f_code.co_name
		
		# If the super() class doesn't have the method attribute, we'll pass silently
		# because that is what the user will expect: they probably defined the method
		# in their code but out of habit used the doDefault() call anyway.
		method = getattr(super(cls, self), methodName, None)
		
		# Assert that the method object is actually a method
		if inspect.ismethod(method):
			return method(*args, **kwargs)
	
	doDefault = classmethod(doDefault)

	
if __name__ == '__main__':
	class TestBase(list, DoDefaultMixin):
		# No myMethod here
		pass

	class MyTest1(TestBase):
		def myMethod(self):
			print "MyTest1.myMethod called."
			MyTest1.doDefault()
		
	class MyTest2(MyTest1): pass

	class MyTest(MyTest2):
		def myMethod(self):
			print "MyTest.myMethod called."
			MyTest.doDefault()
			
	t = MyTest()
	t.myMethod()
