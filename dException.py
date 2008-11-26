# -*- coding: utf-8 -*-
class dException(StandardError):
	"""	Base class in the framework for passing exceptions."""
	

class FontException(dException):
	pass

class FontNotFoundException(FontException):
	pass

class BeginningOfFileException(dException):
	pass


class EndOfFileException(dException):
	pass


class NoRecordsException(dException):
	pass


class QueryException(dException):
	pass


class BusinessRuleViolation(dException):
	pass
	
class BusinessRulePassed(dException):
	pass
	
class RowNotFoundException(dException):
	pass

class FeatureNotImplementedException(dException):
	pass


class StopIterationException(dException):
	pass
	

class FeatureNotSupportedException(dException):
	pass


class MissingPKException(dException):
	pass

class ConnectionLostException(dException):
	pass

class FieldNotFoundException(dException):
	pass

class ConnectionNotFoundException(dException):
	pass

class DatabaseException(dException):
	pass

class DBNoAccessException(DatabaseException):
	pass
	
class DBNoDBOnHostException(DatabaseException):
	pass

class DBFileDoesNotExistException(DatabaseException):
	pass

class DBQueryException(DatabaseException):
	def __init__(self, err, sql=None):
		if sql is None:
			sql = ""
		self.sql = sql
		self.err_desc = "%s" % err
		
	def __str__(self):
		return self.err_desc + '\nSQL: ' + self.sql

class XmlException(dException):
	pass

class WebServerException(dException):
	pass
