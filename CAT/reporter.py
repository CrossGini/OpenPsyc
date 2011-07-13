import sys
import os

sys.path.append(os.path.split(os.getcwd())[0])

import mongoTools

DB = "CAT3" 

posts = mongoTools.MongoAdmin(DB).getTable("subject_stats")

for k in ['verified', 'erratics']:
	for s in ['mem', 'calc']:
		for row in posts.find({'%s.%s.tests.p' % (k, s) : {'$gt' : 0.05}}):
			print "Nulls accepted for " + row['sid'], k, s + ":"
			for test in row[k][s]['tests']:
				if test['p'] > 0.05:
					print test['name'], test['statistic'], test['p']
