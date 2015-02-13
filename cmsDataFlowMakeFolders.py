#!/usr/bin/env python
import os

"""
making theOutput folders
"""
def doMakeFolders(theOutputMergedFolder, theOutputSMMergedFolder, theOutputDQMMergedFolder, theOutputECALMergedFolder, theOutputBadFolder, theOutputSMBadFolder, theMergeType):

   if not os.path.exists(theOutputMergedFolder):
      try:
	 os.makedirs(theOutputMergedFolder)
      except OSError, e:
	  log.warning("Looks like the directory {0} has just been created by someone else...".format(theOutputMergedFolder))

   if not os.path.exists(theOutputSMMergedFolder):
      try:
	 os.makedirs(theOutputSMMergedFolder)
      except OSError, e:
	  log.warning("Looks like the directory {0} has just been created by someone else...".format(theOutputSMMergedFolder))

   if not os.path.exists(theOutputDQMMergedFolder) and theMergeType == "macro":
      try:
	 os.makedirs(theOutputDQMMergedFolder)
      except OSError, e:
	  log.warning("Looks like the directory {0} has just been created by someone else...".format(theOutputDQMMergedFolder))

   if not os.path.exists(theOutputECALMergedFolder) and theMergeType == "macro":
      try:
	 os.makedirs(theOutputECALMergedFolder)
      except OSError, e:
	  log.warning("Looks like the directory {0} has just been created by someone else...".format(theOutputECALMergedFolder))

   if not os.path.exists(theOutputBadFolder):
      try:
	 os.makedirs(theOutputBadFolder)
      except OSError, e:
	  log.warning("Looks like the directory {0} has just been created by someone else...".format(theOutputBadFolder))

   if not os.path.exists(theOutputSMBadFolder):
      try:
	 os.makedirs(theOutputSMBadFolder)
      except OSError, e:
	  log.warning("Looks like the directory {0} has just been created by someone else...".format(theOutputSMBadFolder))
