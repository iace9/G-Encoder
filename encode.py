import re
from math import sqrt, ceil
import turtle

# Conversion constants
POINT2IN = 1/72
POINT2MM = POINT2IN*25.4
RESOLUTION = 3.5 # Resolution When interpolating points from Bezier curve. Higher # = Lower resolution

# Regex
numPattern = r'[0-9\.\-]+'													# Number pattern
dimensionPattern = r'^%%HiResBoundingBox: (?:[0-9\.\-]*\s?){4}$' 			# Gets page size
pathPattern = r'^\s+(?:[0-9\.\-]+\s){2}(?:m|l)$.(?:\s+(?:[0-9\.\-]+\s){6}c$)+' 	# Finds all individual paths
cordPattern = r'(?:[0-9\.\-]+\s?){2}'										# Finds XY coordinate pairs
originPattern = r'^\s+((?:[0-9\.\-]+\s?){2})(?:m|l)$'								# Finds the origin coordinate
bezierPattern = r'^\s+((?:(?:[0-9\.\-]+\s?){2}){3})c$'						# Finds bezier curve format
#curvePattern = r'^\s%.*?/DeviceRGB'										# Finds entire curve with all its paths
#pathPattern = r'^\s+(?:[0-9\.\-]+\s)+(?:m|c)(?:.|\n)+?closepath$'			# Finds seperate paths within curves

class Point:
	def __init__(self, x=None, y=None, string=None):
		if((not string == None)):
			cords = re.findall(numPattern, string)
			if(len(cords) == 2):
				x = cords[0]
				y = cords[1]
			else:
				raise ValueError

		try:
			x = float(x)
			y = float(y)
		except ValueError:
			raise ValueError

		self.x = x
		self.y = y
		self.originalX = x
		self.originalY = y
		self.sizeDeltaX = 1
		self.sizeDeltaY = 1
		self.posDeltaX = 0
		self.posDeltaY = 0

	def move(self, dx, dy):
		self.x += dx
		self.y += dy
		self.posDeltaX += dx
		self.posDeltaY += dy

	def scale(self, dx, dy=None):
		if(dy == None):
			dy = dx
		self.x *= dx
		self.y *= dy
		self.sizeDeltaX *= dx
		self.sizeDeltaY *= dy

	def restore(self):
		# Restores point to its original location
		self.sizeDeltaX = 1
		self.sizeDeltaY = 1
		self.posDeltaX = 0
		self.posDeltaY = 0
		self.x = self.originalX
		self.y = self.originalY

	def getx(self):
		return self.x

	def gety(self):
		return self.y

	def distance(self, other):
		dx = self.x - other.x
		dy = self.y - other.y
		return sqrt(dx**2 + dy**2)

	def __str__(self):
		return "Point(%0.3f, %0.3f)"%(self.x,self.y)

	def __repr__(self):
		return str(self)

	def get(self):
		return [self.x, self.y]

class Bezier:
	"""
	Bezier curve. 
		- Defined by 3 points: self.p1, self.p2, self.p3
		- Defined by 4 points: self.p1, self.p2, self.p3 and p0 that's from the previous Bezier curve or an origin point
		- self.points is an array with the interpolated xy points of the bezier curve
	"""

	def __init__(self, string=None, p0=None, p1=None, p2=None, p3=None):
		# Constructor, take different kinds of inputs:
		#	1) String="x.x y.y x.x y.y x.x y.y" and p0=(Point|Bezier)
		#	2) 4 Point classes: p1=Point(x,y), p2=Point(x,y), p3=Point(x,y) and p0=(Point|Bezier)

		if (not string == None):
			cords = re.findall(numPattern, string)
			if(len(cords) == 6):
				self.p1 = Point(cords[0], cords[1])
				self.p2 = Point(cords[2], cords[3])
				self.p3 = Point(cords[4], cords[5])
			else:
				raise ValueError
		elif((not p1 == None) and (not p2 == None) and (not p3 == None) and (type(p1) == Point) and (type(p2) == Point) and (type(p3) == Point)):
			self.p1 = p1
			self.p2 = p2
			self.p3 = p3
		else:
			raise ValueError

		if((not p0 == None) and (type(p0) == Bezier)):
			self.p0 = p0.p3 # Get last Bezier point from the passed Bezier curve
		elif((not p0 == None) and (type(p0) == Point)):
			self.p0 = p0 # Use point as previous point
		else:
			raise ValueError

		self.interpolate()

	def move(self, dx, dy):
		self.p1.move(dx, dy)
		self.p2.move(dx, dy)
		self.p3.move(dx, dy)
		self.interpolate()

	def scale(self, dx, dy=None):
		if(dy == None):
			dy = dx
		self.p1.scale(dx, dy)
		self.p2.scale(dx, dy)
		self.p3.scale(dx, dy)
		self.interpolate()

	def restore(self):
		self.p1.restore
		self.p2.restore
		self.p3.restore

	def __str__(self):
		return "Bezier Curve { P1: %s, P2: %s, P3: %s }" % (self.p1, self.p2, self.p3)

	def __repr__(self):
		return str(self)

	def getBezierPoints(self):
		return [self.p1, self.p2, self.p3]

	def deCasteljaus(self, t):
		"""
		De Casteljau’s algorithm for interpolating points from the Bezier curve. t is an interval between 0.0 - 1.0. 
		To render the curve you have to interpolate at several intervals. 
		The more intervals you interpolate at, the higher the resolution of the curve. 

		Equation (3 points): P = P1*(1-t)^2 + 2*P2*t*(1-t) + P3*t^2
		Equation (4 Points): P = P0*(1-t)^3 + 3*P1*t*(1-t)^2 + 3*P2*(1-t)*t^2 + P3*t^3
		"""
		if(self.p0 == None): # 3 Point interpolation
			x = self.p1.x*(1-t)**2 + 2*self.p2.x*t*(1-t) + self.p3.x*t**2
			y = self.p1.y*(1-t)**2 + 2*self.p2.y*t*(1-t) + self.p3.y*t**2
		else:	# 4 Point interpolation
			x = self.p0.x*(1-t)**3 + 3*self.p1.x*t*(1-t)**2 + 3*self.p2.x*(1-t)*t**2 + self.p3.x*t**3
			y = self.p0.y*(1-t)**3 + 3*self.p1.y*t*(1-t)**2 + 3*self.p2.y*(1-t)*t**2 + self.p3.y*t**3

		return Point(x, y)

	def interpolate(self, resolution=RESOLUTION):
		"""
		Interpolates the xy coordinates of the Bezier curve. 
		'resolution' parameter determines how many intervals to plot per points.
		"""
		ints = ceil(self.p1.distance(self.p3)/resolution)
		if(ints < 1):
			ints = 1

		self.points = [self.deCasteljaus(i/ints) for i in range(ints+1)]


	def plot(self):
		"""
		Plots the curve using turtle.
		"""
		turtle.penup()
		turtle.pencolor("red")
		for i in self.points:
			turtle.goto(i.x, i.y)
			turtle.dot()

	def plotBezier(self):
		"""
		Plots the curve using turtle.
		"""
		turtle.penup()
		turtle.pencolor("blue")
		count = 0
		for i in self.getBezierPoints():
			if(count == 2):
				turtle.pencolor("green")
			turtle.goto(i.x, i.y)
			turtle.dot()
			count += 1

class Path:

	def __init__(self, origin=None, beziers=[]):
		if(type(origin) == Point):
			self.origin = origin
		elif(type(origin) == str):
			self.origin = Point(string=origin)
		else:
			raise TypeError

		if(len(beziers) > 0 and type(beziers[0]) == Bezier):
			self.beziers = beziers
		elif(len(beziers) > 0 and type(beziers[0]) == str):
			self.beziers = []
			self.addBezierFromStringArray(beziers)
		else:
			raise TypeError

	def addPoint(self, point):
		self.beziers.append(point)

	def addBezierFromStringArray(self, bezierArray):
		prev = self.origin
		for bez in bezierArray:
			new = Bezier(bez, prev)
			self.beziers.append(new)
			prev = new

	def move(self, dx, dy):
		self.origin.move(dx,dy)
		[i.move(dx, dy) for i in self.beziers]

	def scale(self, dx, dy=None):
		if(dy == None):
			dy = dx
		self.origin.scale(dx,dy)
		[i.scale(dx, dy) for i in self.beziers]

	def restore(self):
		self.origin.restore()
		[i.restore() for i in self.beziers]

	def interpolate(self, res=RESOLUTION):
		[i.interpolate(res) for i in self.beziers]

	def getBounds(self):
		xmin = self.origin.x
		ymin = self.origin.y
		xmax = self.origin.x
		ymax = self.origin.y

		for bez in self.beziers:
			for point in bez.getBezierPoints():
				if(point.x > xmax):
					xmax = point.x
				elif(point.x < xmin):
					xmin = point.x
				if(point.y > ymax):
					ymax = point.y
				elif(point.y < ymin):
					ymin = point.y

		return [Point(xmin, ymin), Point(xmax, ymax)]

	def plot(self):
		turtle.penup()
		turtle.goto(self.origin.x, self.origin.y)
		turtle.pendown()
		turtle.pencolor("black")
		for points in self.beziers:
			for i in points.points:
				turtle.goto(i.x, i.y)
		turtle.penup()

	def plotBezier(self):
		turtle.penup()
		turtle.goto(self.origin.x, self.origin.y)
		turtle.pendown()
		turtle.pencolor("black")
		for points in self.beziers:
			for i in points.getBezierPoints():
				turtle.goto(i.x, i.y)

		turtle.penup()

fileName = 'globe.eps'
with open(fileName, 'r') as file:
	data = file.read()
	file.close()


paths = []

pathsData = re.findall(pathPattern, data, flags=re.M|re.S)

turtle.speed(0)

for pathData in pathsData:
	originData = re.findall(originPattern, pathData, flags=re.M)[0]
	beziersData = re.findall(bezierPattern, pathData, flags=re.M|re.S)
	paths.append(Path(originData, beziersData))

for i in paths:
	#i.scale(2)
	i.move(-250,-230)
	i.plot()

