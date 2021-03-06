import webapp2
import json

import logging

from constants import *

from datastore import AbstractionLayer

#For extensions add to this list, or abstract to some type of properties file

class Comments(webapp2.RequestHandler):

	def get(self):
		#Default status if none are set
		self.response.set_status(HTTP_OK,"")

		#Check for optional parameters:
		commentType = self.request.get("type")

		if commentType:
			#We have an optional parameter. Is it well formed?

			if commentType.upper() in COMMENT_TYPES:
				#Yes it is well formed and we may execute a datastore query for the comments
				pass
			else:
				#Semantically incorrect query
				self.response.set_status(HTTP_REQUEST_SEMANTICS_PROBLEM)
				self.response.write(ERROR_STR % (HTTP_REQUEST_SEMANTICS_PROBLEM,"Unrecognized type"))
				return
		#Check for other optional parameter:
		page = self.request.get("page")
		if page:
			#We have a paging parameter, is it well formed?
			try:
				int(page)
				page = abs(int(page)) #We'll accept a negative number, but we'll make it positive. The specification says the value should be unsigned, so we should throw a semantic error here. But that's up to debate
			except Exception, e:
				#Poorly formed page parameter
				self.response.set_status(HTTP_REQUEST_SEMANTICS_PROBLEM)
				self.response.write(ERROR_STR % (HTTP_REQUEST_SEMANTICS_PROBLEM, "Non-integer page value not allowed"))
				return
		else:
			#No page given, so start it off
			page = 1
		#If we're here we have (possibly) a comment type and a page to retrieve

		#After retrieving the page we need to send back pagination information as well
		previous = None
		if page == 1:
			#There is no previous
			pass
		else:
			previous = "%s%s%s%s%s%s%i" % (BASE_URL,CONTEXT_PATH,COMMENTS_RESOURCE_PATH,'?type=',commentType.replace(' ','+'),'&page=',page -1)
		next = "%s%s%s%s%s%s%i" % (BASE_URL,CONTEXT_PATH,COMMENTS_RESOURCE_PATH,'?type=',commentType.replace(' ','+'),'&page=',page +1)

		#Get comments:
		layer = AbstractionLayer().getComments(cType=commentType,page=page)

		#write out the comments in json form
		comments = layer
		response = { "status_code" : HTTP_OK, "comments" : comments, "page" : {"next" : next, "previous" : previous}}

		#Send out the response
		self.response.set_status(HTTP_OK,"")
		self.response.write(json.dumps(response))	

	def post(self):
		self.response.set_status(HTTP_OK,"")

		#Confirm that all elements of the json are there.
		try:
			json.loads(self.request.body)
		except Exception, e:
			#The request body is malformed. 
			self.response.set_status(HTTP_REQUEST_SYNTAX_PROBLEM,"")
			self.response.write(ERROR_STR % (HTTP_REQUEST_SYNTAX_PROBLEM, "Request body is malformed"))
			#Don't allow execution to proceed any further than this
			return
		info = json.loads(self.request.body)

		#Request is well formed, but does it hold the proper semantic meaning for us? (all keys present)
		try:
			info['type']
			info['message']
		except Exception, e:
			#The request body lacks proper keys
			self.response.set_status(HTTP_REQUEST_SEMANTICS_PROBLEM)
			self.response.write(ERROR_STR % (HTTP_REQUEST_SEMANTICS_PROBLEM,"Required keys not present in request"))
			return

		#Request has proper required keys
		typeOfComment = info['type']
		commentMessage = info['message']

		if typeOfComment is None or commentMessage is None:
			self.response.set_status(HTTP_REQUEST_SEMANTICS_PROBLEM)
			self.response.write(ERROR_STR % (HTTP_REQUEST_SEMANTICS_PROBLEM, "Cannot accept null data for required parameters"))
			return

		#Determine if type is semantically correct
		if typeOfComment.upper() in COMMENT_TYPES:
			pass
		else:
			self.response.set_status(HTTP_REQUEST_SEMANTICS_PROBLEM)
			self.response.write(ERROR_STR %( HTTP_REQUEST_SEMANTICS_PROBLEM,  "Unrecognized Type" ))
			return

		pin = None
		try:
			info['pin']
			pin = int(info['pin'])
		except ValueError, v:
			self.response.set_status(HTTP_REQUEST_SEMANTICS_PROBLEM)
			self.response.write( ERROR_STR % (HTTP_REQUEST_SEMANTICS_PROBLEM,"If pin information is sent in a request, it must be a numeric id"))
			return
		except Exception, e:
			#Die silently if the pin is not there as it is optional
			pass

		# validate the message
		if (len(info['message'].strip(" ")) == 0) or (info['message'] == None):
			self.response.set_status(HTTP_REQUEST_SEMANTICS_PROBLEM)
			self.response.write(ERROR_STR % (HTTP_REQUEST_SEMANTICS_PROBLEM, "Cannot accept an empty message" ))
			return

		if len(info['message']) > 140:
			self.response.set_status(HTTP_REQUEST_SEMANTICS_PROBLEM)
			self.response.write(ERROR_STR %(HTTP_REQUEST_SEMANTICS_PROBLEM, "Message exceeds 140 characters" ))
			return

		#All information present and valid. Store information in the database
		AbstractionLayer().submitComments(commentType=typeOfComment.upper(), message=commentMessage, pin=pin)

		self.response.write('{ "status_code" : %i, "message" : "Successfuly submitted new comment" }' % HTTP_OK)

		

application = webapp2.WSGIApplication([
    ('/api/comments', Comments),

], debug=True)