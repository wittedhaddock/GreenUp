#Import google sign in
from google.appengine.ext import db

import webapp2
import json

import api
from constants import *
from  datastore import *

import logging


class Heatmap(webapp2.RequestHandler):

	def get(self):
		parameters = 0

		#load optional parameters
		latDegrees = self.request.get("latDegrees")
		lonDegrees = self.request.get("lonDegrees")
		latOffset = self.request.get("latOffset")
		lonOffset = self.request.get("lonOffset")
		precision = self.request.get("precision")
		raw = self.request.get("raw")

		renderRaw = False
		if raw is not None:
			if raw.upper().__eq__('TRUE'):
				renderRaw = True
		
		
		#validate parameters
		if latDegrees is not None and latDegrees is not "":
			try:
				#Check that latDegrees is within the correct range and is numeric. throw syntax on numeric error, semantic on range
				float(latDegrees)
				#check range
				latDegrees = float(latDegrees)
				if latDegrees < -90.0 or latDegrees > 90.0:
					raise SemanticError("latDegrees must be within the range of -90.0 and 90.0")
				if latDegrees == "":
					latDegrees = None
				parameters+= 1
			except ValueError, v:
				#Syntactic error
				self.response.set_status(HTTP_REQUEST_SYNTAX_PROBLEM)
				self.response.write(ERROR_STR % (HTTP_REQUEST_SYNTAX_PROBLEM,"latDegrees parameter must be numeric"))
				return
			except SemanticError, s:
				self.response.set_status(HTTP_REQUEST_SEMANTICS_PROBLEM,s.message)
				self.response.write(ERROR_STR % (HTTP_REQUEST_SEMANTICS_PROBLEM,s.message))
				return
		else:
			latDegrees = None
		

		if lonDegrees is not None and lonDegrees is not "":
			try:
				float(lonDegrees)
				#check range
				lonDegrees = float(lonDegrees)
				if lonDegrees < -180.0 or lonDegrees > 180.0:
					raise SemanticError("lonDegrees must be within the range of -180.0 and 180.0")
				parameters+=1
			except ValueError, v:
				self.response.set_status(HTTP_REQUEST_SYNTAX_PROBLEM)
				self.response.write(ERROR_STR % (HTTP_REQUEST_SYNTAX_PROBLEM,"lonDegrees parameter must be numeric"))
				return
			except SemanticError, s:
				self.response.set_status(HTTP_REQUEST_SEMANTICS_PROBLEM,s.message)
				self.response.write(ERROR_STR % (HTTP_REQUEST_SEMANTICS_PROBLEM , s.message))
				return
		else:
			lonDegrees = None
		
		#Check precision
		if precision is not None and precision is not "":
			try:
				precision = abs((int(precision)))
				parameters += 1
			except ValueError, e:
				self.response.set_status(HTTP_REQUEST_SYNTAX_PROBLEM)
				self.response.write(ERROR_STR % (HTTP_REQUEST_SYNTAX_PROBLEM, "Precision value must be a numeric integer"))
				return
		else:
			precision = DEFAULT_ROUNDING_PRECISION		
		
		#Check offsets
		#If one offset is present the other must be too
		#It'd be great if python had XOR for objects instead of just bitwise ^
		if (lonOffset and not latOffset) or (latOffset and not lonOffset):
			self.response.set_status(HTTP_REQUEST_SEMANTICS_PROBLEM)
			self.response.write(ERROR_STR % (HTTP_REQUEST_SEMANTICS_PROBLEM ,"Both lonOffset and latOffset must be present if either is used"))
			return

		#the choice of lon is arbitrary, either lat or lon offset would work here		
		if lonOffset is not None and lonOffset is not "":
			try:
				lonOffset = abs((float(lonOffset)))
				latOffset = abs((float(latOffset)))
				parameters+=2
				#We could check to see if the offsets cause us to go out of range for our queries, but really that's unneccesary and would cause unneccesary calculation on the clientside to deal making sure they're within range.
			except ValueError, e:
				self.response.set_status(HTTP_REQUEST_SYNTAX_PROBLEM)
				self.response.write(ERROR_STR % (HTTP_REQUEST_SYNTAX_PROBLEM,"Offsets defined must both be integers"))
				return
		else:
			#default
			lonOffset = 1
			latOffset = 1

		#If no parameters are specified we'll return everything we have for them
		response = []
		layer = AbstractionLayer()
		response = layer.getHeatmap(latDegrees,latOffset,lonDegrees,lonOffset, precision,renderRaw)

		#By this point we have a response and we simply have to send it back
		self.response.set_status(HTTP_OK)
		self.response.write(json.dumps({'status_code' : HTTP_OK, 'grid' : response}))	

	def put(self):
		#Check for the existence of required parameters
		try:
			json.loads(self.request.body)
		except Exception, e:
			#The request body is malformed. 
			self.response.set_status(HTTP_REQUEST_SYNTAX_PROBLEM,"")
			self.response.write(ERROR_STR % (HTTP_REQUEST_SYNTAX_PROBLEM,"Request body is malformed"))
			#Don't allow execution to proceed any further than this
			return
		info = json.loads(self.request.body)


		#For each pin we recieve we will enter them into the database. If any pins are malformed then no pointss are added
		points = []
		for i in range(len(info)):
			try:
				info[i]["latDegrees"]
				info[i]["lonDegrees"]
				info[i]["secondsWorked"]
			except Exception, e:
				#Request does not have proper keys
				self.response.set_status(HTTP_REQUEST_SYNTAX_PROBLEM,"")
				self.response.write(ERROR_STR % (HTTP_REQUEST_SYNTAX_PROBLEM,"Required keys not present in request"))
				return
			


			latDegrees = info[i]["latDegrees"]
			lonDegrees = info[i]["lonDegrees"]
			secondsWorked = info[i]["secondsWorked"]

			if latDegrees is None or lonDegrees is None or secondsWorked is None:
				self.response.set_status(HTTP_REQUEST_SEMANTICS_PROBLEM)
				self.response.write(ERROR_STR % (HTTP_REQUEST_SEMANTICS_PROBLEM,"Cannot accept null data for required parameters"))
				return

			try:
				latDegrees = float(latDegrees)
				if latDegrees < -180.0 or latDegrees > 180.0:
					raise SemanticError("latDegrees must be within the range of -180.0 and 180.0")
			except ValueError, e:
				self.response.set_status(HTTP_REQUEST_SYNTAX_PROBLEM)
				self.response.write(ERROR_STR % (HTTP_REQUEST_SYNTAX_PROBLEM,"latDegrees parameter must be numeric"))
				return
			except SemanticError, s:
				self.response.set_status(HTTP_REQUEST_SEMANTICS_PROBLEM)
				self.response.write(ERROR_STR % (HTTP_REQUEST_SEMANTICS_PROBLEM,s.message))
				return

			try:
				lonDegrees = float(lonDegrees)
				if lonDegrees <  -90.0 or lonDegrees > 90.0:
					raise SemanticError("Longitude degrees must be within the range of -90 to 90 degree")
			except ValueError, e:
				self.response.set_status(HTTP_REQUEST_SYNTAX_PROBLEM)
				self.response.write(ERROR_STR % (HTTP_REQUEST_SYNTAX_PROBLEM,"lonDegrees parameter must be numeric"))
				return
			except SemanticError, s:
				self.response.set_status(HTTP_REQUEST_SEMANTICS_PROBLEM)
				self.response.write(ERROR_STR % (HTTP_REQUEST_SEMANTICS_PROBLEM,s.message))
				return

			try:
				secondsWorked = int(secondsWorked)
				if secondsWorked < 0:
					raise SemanticError("Seconds worked must be a non negative unsigned integer value")
			except ValueError, e:
				self.response.set_status(HTTP_REQUEST_SYNTAX_PROBLEM)
				self.response.write(ERROR_STR % (HTTP_REQUEST_SYNTAX_PROBLEM, "Seconds worked must be an unsigned integer value"))
				return
			except SemanticError, s:
				self.response.set_status(HTTP_REQUEST_SEMANTICS_PROBLEM)
				self.response.write(ERROR_STR% (HTTP_REQUEST_SEMANTICS_PROBLEM,s.message))
				return

			#All required parameters are here and validated.
			#Add it to the list of points to be added, checking the previous point to see if it is the same
			if (info[i-1]['latDegrees'] == info[i]['latDegrees']) and (info[i-1]['lonDegrees'] == info[i]['lonDegrees']):
				if len(points) > 0:
					points[-1]['secondsWorked'] += secondsWorked
				else:
					points.append(info[i])
			else:
				points.append(info[i])

		#Add all points to datastore
		layer = AbstractionLayer()
		layer.updateHeatmap(points)

		self.response.set_status(HTTP_OK)
		self.response.write('{"status_code": %i, "message" : "Successful submit" }' % HTTP_OK)

	def post(self):
		return self.put()
		

application = webapp2.WSGIApplication([
    ('/api/heatmap', Heatmap),

], debug=True)
