#!/usr/bin/env python

import sys, os, time, copy
import bailey_shuffler
import experiments
from experiments import printWord

import pygame
from pygame.locals import *
	
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
		if not data:
			RT = time.clock()
			p.parameters.go_duration = (0.032, 'seconds')
			#dataList.append ([text, colour, start, RT])
			exit = 1
		else:
			pass


		#insStim, insView = printText(screen, insText, 30, (255, 255,255))
		#instructions = Presentation(go_duration=('forever',), viewports=[insView])

def practice(pracList,screen):
	for item in pracList:
		showStimulus(screen, item[0], item[1])

def main():

	pygame.init()
	screen = get_default_screen()
	screen.parameters.bgcolor = (0.0,0.0,0.0,0.0)
	pygame.display.set_caption("Welcome to the Experiment")

	pracList = bailey_shuffler.makePracticeList()

	practice(pracList, screen)


if __name__ == '__main__': main()
