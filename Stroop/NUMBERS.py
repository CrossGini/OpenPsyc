#!/usr/bin/env python

import sys, os, time, copy, pickle
import bailey_shuffler
import experiments
from experiments import printWord

import stroop_stats
import wx
import pygame
from pygame.locals import *

import Subject
import VisionEgg
from VisionEgg.Core import *
from VisionEgg.FlowControl import Presentation, ConstantController
from VisionEgg.DaqLPT import raw_lpt_module
from VisionEgg.Text import *
from VisionEgg.Textures import *

def showStimulus(screen, text, colour):
	word, viewport = printWord(screen, text, 200, colour)
	p = Presentation(go_duration=(0.5,'seconds'),viewports=[viewport])
	p.go()
	start = time.clock()
	exit = 0
	while not exit:
		data = raw_lpt_module.inp(0x379) & 0x20		
		#print data
		if not data:
			#print "hello"
			RT = time.clock()
			p.parameters.go_duration = (0.032, 'seconds')
			dataList.append ([text, colour, start, RT])
			exit = 1
		else:
			pass

		#insStim, insView = printText(screen, insText, 30, (255, 255,255))
		#instructions = Presentation(go_duration=('forever',), viewports=[insView])


class subFrame(wx.Frame):
	def __init__(self, parent, id, title):
		wx.Frame.__init__(self, parent, id, title)

		mainSizer = wx.FlexGridSizer(4,2,10,10)

		self.number = wx.TextCtrl(self, -1, '')

		mainSizer.Add(wx.StaticText(self, -1, 'Participant Number: '))

		mainSizer.Add(self.number)

		self.male = wx.RadioButton(self, -1, 'Female', style=wx.RB_GROUP)
		self.female = wx.RadioButton(self, -1, 'Male')

		self.left = wx.RadioButton(self, -1, 'Left', style=wx.RB_GROUP)
		self.right = wx.RadioButton(self, -1, 'Right')


		handbox = wx.BoxSizer(wx.HORIZONTAL)
		sexbox = wx.BoxSizer(wx.HORIZONTAL)
	
		handbox.Add(self.left)
		handbox.Add(self.right)

		sexbox.Add(self.female)
		sexbox.Add(self.male)

		mainSizer.Add(wx.StaticText(self, -1, 'Sex: '))

		mainSizer.Add(sexbox)

		mainSizer.Add(wx.StaticText(self, -1, 'Hand: '))

		mainSizer.Add(handbox)

		mainSizer.Add(wx.Button(self, -1, 'OK'))
	
		self.Bind(wx.EVT_BUTTON, self.onOK)

		self.SetSizer(mainSizer)

		self.Layout()

	def onOK(self, event):
		if self.male.GetValue():
			sex = 2
		else:
			sex = 1
		if self.left.GetValue():
			hand = 1		
		else:
			hand = 2
		
		sub = Subject.Subject(self.number.GetValue(), sex, hand)

		sub.save("numberdata")

		self.Destroy()

class subInfo(wx.App):
	def OnInit(self):
		frame = subFrame(None, -1, 'Enter Participant Info')
		frame.Centre()
		frame.Show(True)
		return True	


def main():

	subjectApp = subInfo(0)
	subjectApp.MainLoop()

	pygame.init()
	screen = get_default_screen()
	screen.parameters.bgcolor = (0.0,0.0,0.0,0.0)
	pygame.display.set_caption("Welcome to the Experiment")

	global dataList

	dataList = []

	numList = bailey_shuffler.makePracticeList(32)

	for item in numList:
		showStimulus(screen, item[0], item[1])

	myloader = Subject.SubLoader()

	sub = myloader.load()

	filename = os.path.join(sub.path, (sub.name + "_number_data.pck"))

	textfile = os.path.join(sub.path, (sub.name + "_number_data.txt"))

	f = open(filename, 'w')

	pickle.dump(dataList, f)

	f.close()

	f = open(textfile, 'w')
	
	for line in dataList:
		f.write(str(line)+ "\n")

	f.close()

	stroop_stats.addSubNumberData(sub)



if __name__ == '__main__': main()
