import pymongo
from pymongo import Connection
from pymongo.code import Code
import copy

import glob
import os

class MongoAdmin:
	"""
	This is a simple class to provide easy
	access to a mongo database
	"""
	def __init__(self, db="test_database"):
		self.connection = Connection()
		self.db = self.connection[db]
		return None

	def getDB(self):
		return self.db

	def getTable(self, table="test_table"):
		return self.db[table]

def KeySafe(key):
	key = key.replace(".", "_")
	return key

def StringToType(value):
	if value.isdigit():
		val = int(value)

	elif value.count('.') == 1:
		val = value.split('.')
		if val[0].isdigit() and val[1].isdigit():
			val = float(value)

	else:
		val = value

	return val

def strip(i):
	i = i.strip()
	return i

class RecursiveTrim:
	def __init__(self, cursor, measure, maxSD):
		#first determine the M and SD of the posts
		db = MongoAdmin("Trimmer")

		posts = db.getTable("Trim").posts
		#print posts

		posts.remove({})

		for row in cursor:
			#print row
			posts.insert(row)

		self.posts = posts

		self.measure = measure
		self.maxSD = maxSD

		self.Trim()


	def Trim(self):

		reduceFunc = Code("function(obj,prev) { meas = obj.%s; prev.csum += meas; prev.ccount++; prev.ss += meas * meas;}" % self.measure)

		initial = {"csum":0, "ccount":0, "ss":0, "avg":0, "std":0}
		finalize = Code("function(prev){ prev.avg = prev.csum / prev.ccount; prev.std = Math.sqrt((prev.ss - (prev.csum * prev.csum/ prev.ccount)) / prev.ccount);}")

		mapFunc = Code("function () {emit(this.%s, 1);}" % self.measure)

		summary = self.posts.group({}, {}, initial, reduceFunc, finalize)

		if summary:

			self.avg = summary[0]['avg']
			self.std = summary[0]['std']
			self.count = summary[0]['ccount']

			mapFunc = Code("function() {"
						"emit(this.%s, 1);"
						 "}" % (self.measure))

			#zscore = Math.abs(this.%s - %s) / %s; emit(zscore, zscore);}" % (measure, avg, std))
			reduceFunc = Code("function(obj, prev) {"
						"zscore = Math.abs(obj - %s) / %s;"
						"return zscore; }" % (self.avg, self.std))

			result = self.posts.map_reduce(map=mapFunc, reduce=reduceFunc)

			item = result.find().sort('value', -1)[0]

			if item['value'] > self.maxSD:
				#print "Removing %s : %s" % (self.measure, item['_id'])
				self.posts.remove({self.measure:item['_id']})
				self.Trim()
		else:
			self.avg = 0
			self.std = 0
			self.count = 0


	def GetValues(self):
		return self.avg, self.std, self.count


class ReadTable:
	"""
	Class to read single or a set of data files
	Args are...
	fileName (String) - name of the file, or a pattern to be globbed
	dbName (String) - name of the DB you'd like to submit this data to
	tableName (String) - name of the table you'd like to enter this data into
	clear (Boolean) - Whether or not to erase the contents of the table 
					  before uploading this data into it
	startLine (int) - The line on which the headers appear in the file
	columns (String List) - If you want to upload only specific columns
						    from the data files, put the header names in this list
	sep (String) - the character which separates data in your data file
	"""
	def __init__(self, fileName, dbName, tableName, kind="", clear=False, startLine=0, columns=[], sep=","):

		db = MongoAdmin(dbName)
		table = db.getTable(tableName)

		if clear:
			table.posts.remove({})

		self.posts = table.posts
		self.sep = ","


		if fileName.count('*'):
			self.fileList = glob.glob(fileName)
		else:
			self.fileList = [fileName]

		self.startLine = startLine
		self.columns = columns
	
		for f in self.fileList:
			if kind != "eprime":
				self.processCSV(f)
			else:
				self.processEPrime(f)
	

	def processCSV(self, csv):
		f = open(csv, 'r')
		lines = f.readlines()

		#get the headers, make the variables
		headers = lines[self.startLine].split(',')
		headers = map(strip, headers)
		VARs = {}
		index = {}
		for k in headers:
			if self.columns:
				if k in self.columns:
					index[k] = headers.index(k)
					VARs[k] = []
			else:
				index[k] = headers.index(k)
				VARs[k] = []


		for line in lines[self.startLine+1:]:
			line = line.split(',')
			line = map(strip, line)
			row = {}
			for k in VARs.keys():
				value = line[index[k]]
				if value:
					row[k] = StringToType(value)

			self.posts.insert(row)
		print "The contents of %s have been uploaded" % (csv)

	def processEPrime(self, txt):
		f = open(txt, 'r')
		lines = map(strip, f.readlines())

		i1 = lines.index("*** Header Start ***")
		i2 = lines.index("*** Header End ***")

		header = lines[i1+1:i2]

		info = {}

		data = {}

		for h in header:
			frags = h.split(":")
			frags = map(strip, frags)

			if self.columns:
				if frags[0] in self.columns:
					info[KeySafe(frags[0])] = StringToType(frags[1])
			else:
				info[KeySafe(frags[0])] = StringToType(frags[1])

		i1 = lines.index("Level: 2")

		dataLines = lines[i1 + 1:]

		row = {}
		for d in dataLines:
			for k in info.keys():
				row[k] = info[k]
			if d.count(":"):
				frags = d.split(":")
				frags = map(strip, frags)
				if self.columns:
					if frags[0] in self.columns:
						row[KeySafe(frags[0])] = StringToType(frags[1])
				else:
					row[KeySafe(frags[0])] = StringToType(frags[1])
		
			elif d == "*** LogFrame End ***":
				if row:
					self.posts.insert(row)
				row = {}
				
		print "The contents of %s have been uploaded" % (txt)

			
class WriteTable:
	def __init__(self, measure, groupBy, screen_condition, condition, dbName, table, name="", maxSD = 3, subject="s_id"):
		self.groupBy = groupBy

		dbA = MongoAdmin(dbName)
		my_table = dbA.getTable(table)

		self.posts = my_table.posts

		self.screen_condition = screen_condition
		self.condition = condition
		self.maxSD = maxSD
		if name:
			self.name = name
		else:
			self.name = "%s_%s" % (dbName, table)	
			for g in groupBy:
				self.name = self.name + "_" + g
			self.name = self.name + "_" + measure
		
		self.measure = measure
		self.subject = subject

		#initialization and finalization for the groupBy query - note that the reduce functions are constructed at run time to correspond with the necessary subject SD screen
		self.initial = {"csum":0, "ccount":0, "ss":0, "avg":0, "std":0}
		self.finalize = Code("function(prev){ prev.avg = prev.csum / prev.ccount; prev.std = Math.sqrt(Math.abs(prev.ss - prev.avg * prev.csum) / prev.ccount);} ")

		self.s_ids = self.posts.distinct(subject)
		
		self.Compute()
		
	def Compute(self):
		sDict = {}

		gDict = {}

		#get a list of all the conditions within each grouping factor

		matchingPosts = self.posts.find(self.condition)

		for g in self.groupBy:
			cats = matchingPosts.distinct(g)
			gDict[g] = cats


		myString = "headerItems = []\nheaderList = []\n"
		tabby = ""

		gString = str(self.groupBy)
		gString = gString.strip('[')
		gString = gString.strip(']')
		
		dString = ""
		lString = ""


		for g in self.groupBy:
			dString = "%s,'%s' : %s" % (dString, g, g)
			if lString == "":
				lString = "str(%s)" % g
			else:
				lString = lString + "+ \"_\" + str(" + g + ")"


		dString = "{" + dString.lstrip(',') + "}"


		#create the big ol' for loop, one for each grouping factor
		for g in self.groupBy:
			myString = "%s%sfor %s in gDict['%s']:\n" % (myString, tabby, g, g)
			tabby = tabby + "\t" 

		myString = "%s%sheaderItems.append(%s)\n" % (myString, tabby, dString)
		myString = "%s%sheaderList.append(%s)" % (myString, tabby, lString)

		exec(myString)

		finalHeaders = []
		for h in headerList:
			finalHeaders.append(h + "_%s" % self.measure)
			finalHeaders.append(h + "_count")

		subjects = self.posts.distinct(self.subject)

		groupBy = [self.subject] + self.groupBy

		#filter by subject SD

		lines = []

		for s_id in self.s_ids:
			c = copy.deepcopy(self.condition)
			c[self.subject] = s_id

			reduceFunc = Code("""
			function(obj,prev) { 
				meas = obj.%s;
				prev.csum += meas; 
				prev.ccount++; 
				prev.ss += meas * meas;
				}
			""" % (self.measure))

			gbKey = {}

			for g in groupBy:
				gbKey[g] = True

			items = []

			for h in headerItems:

				r = {self.subject : s_id}
				myC = copy.deepcopy(c)

				for k in h.keys():
					r[k] = h[k]
					c[k] = h[k]
						
				rows = self.posts.find(c)

				if rows.count():
					trimmer = RecursiveTrim(rows, self.measure, self.maxSD)
					avg, std, count = trimmer.GetValues()
				else:
					avg = "NA"
					std = "NA"
					count = 0
				
				r['avg'] = avg
				r['std'] = std
				r['count'] = int(count)
			
				items.append(copy.deepcopy(r))

			#compute the total amount of measurements here
			total = 0.
			for i in items:
				total = total + i['count']

			#add a frequency field to the items
			for i in items:
				i['freq'] = i['count'] / total * 100.

			sDict[str(s_id)] = items

		self.sDict = sDict


	def WriteForR(self):

		headers = [self.subject] + self.groupBy + ["avg"] + ["freq"] + ["count"]

		lines = []
		for k in self.sDict.keys():
			for row in self.sDict[k]:
				line = ""
				for h in headers:
					value = row[h]
					if value:
						line = "%s,%s" % (line, row[h])
					else:
						if h == "freq" or h == "count":
							line = "%s,0" % (line)
						else:
							line = "%s,NA" % (line)
				line = line.lstrip(',')
				line = "%s" % line
				lines.append(line)

				
		self.Write(headers,lines,"dat")
		
		return "%s.dat" % (self.name)


	def WriteForSPSS(self):
		gDict = {}

		#get a list of all the conditions within each grouping factor

		matchingPosts = self.posts.find(self.condition)

		for g in self.groupBy:
			cats = matchingPosts.distinct(g)
			gDict[g] = cats


		myString = "headerItems = []\nheaderList = []\n"
		tabby = ""

		gString = str(self.groupBy)
		gString = gString.strip('[')
		gString = gString.strip(']')
		
		dString = ""
		lString = ""


		for g in self.groupBy:
			dString = "%s,'%s' : %s" % (dString, g, g)
			if lString == "":
				lString = "str(%s)" % g
			else:
				lString = lString + "+ \"_\" + str(" + g + ")"


		dString = "{" + dString.lstrip(',') + "}"


		#create the big ol' for loop, one for each grouping factor
		for g in self.groupBy:
			myString = "%s%sfor %s in gDict['%s']:\n" % (myString, tabby, g, g)
			tabby = tabby + "\t" 

		#now 
		myString = "%s%sheaderItems.append(%s)\n" % (myString, tabby, dString)
		myString = "%s%sheaderList.append(%s)" % (myString, tabby, lString)

		exec(myString)

		finalHeaders = []
		for h in headerList:
			finalHeaders.append(h + "_RT")
			finalHeaders.append(h + "_count")

		subjects = self.posts.distinct(self.subject)

		lines = []

		for s_id in self.sSD.keys():
			line = "%s" % s_id

			lineDict = {}

			reduceFunc = Code("""
			function(obj,prev) { 
				meas = obj.%s;
				if (Math.abs(meas - %s) <= (%s * %s)) {
					prev.csum += meas; 
					prev.ccount++; 
					prev.ss += meas * meas;
				}
			}
			""" % (self.measure, self.sAVG[s_id], self.sSD[s_id], self.maxSD))


			c = self.condition
			c[self.subject] = s_id

			rows = self.posts.group(key=self.groupBy, condition=c, initial=self.initial, reduce=reduceFunc, finalize = self.finalize)

			for row in rows:
				col = ""
				for g in self.groupBy:
					col = col + "_" + str(row[g])
				col = col.strip("_")
				lineDict[col+ "_RT"] = row['avg']
				lineDict[col+ "_count"] = row['ccount']

			for header in headerList:
				try:
					line = "%s, %3.3f, %i" % (line, lineDict[header + "_RT" ], int(lineDict[header + "_count"]))
				except KeyError:
					line = "%s, NA, NA" % line

			lines.append(line)

		self.Write([self.subject] + finalHeaders,lines,"csv")	
		
	def Write(self, headers, lines, ext):

		#now, write the output file
		path = os.path.join("output", "%s.%s" % (self.name, ext))

		f = open(path, "w")

		hString = ""

		for h in headers:
			hString = "%s,%s" % (hString, h)

		f.write(hString[1:])
		f.write("\n")

		
		for l in lines:
			f.write(l + "\n")

		f.close()
