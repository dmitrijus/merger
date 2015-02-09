#!/usr/bin/env python
import os, time, sys, getopt, fcntl
import shutil
import json
import glob

from Logging import getLogger
log = getLogger()

"""
clean up run folder if some conditions are met
"""
def cleanUpRun(debug, EoRFileName, inputDataFolder, afterString, path_eol, theRunNumber, outputSMMergedFolder, outputEndName, completeMergingThreshold):
   
   settingsEoR = ""
   try:
      settingsEoR_textI = open(EoRFileName, "r").read()
      if(float(debug) >= 50): log.info("trying to load EoR file: {0}".format(EoRFileName))
      settingsEoR = json.loads(settingsEoR_textI)
   except ValueError, e:
      log.warning("Looks like the EoR file {0} is not available, I'll try again...".format(EoRFileName))
      try:
   	 time.sleep (0.1)
   	 settingsEoR_textI = open(EoRFileName, "r").read()
         settingsEoR = json.loads(settingsEoR_textI)
      except ValueError, e:
   	 log.warning("Looks like the EoR file {0} is not available (2nd try)...".format(EoRFileName))
   	 time.sleep (1.0)
   	 settingsEoR_textI = open(EoRFileName, "r").read()
         settingsEoR = json.loads(settingsEoR_textI)
   eventsInputBU = int(settingsEoR['data'][0])

   eventsInputFU = 0
   for nb in range(0, len(afterString)):
      if not afterString[nb].endswith(".jsn"): continue
      if "index" in afterString[nb]: continue
      if afterString[nb].endswith("recv"): continue
      if "EoLS" in afterString[nb]: continue
      if "BoLS" in afterString[nb]: continue
      if not "EoR" in afterString[nb]: continue
      if "TEMP" in afterString[nb]: continue
      inputEoRFUJsonFile = os.path.join(inputDataFolder, afterString[nb])
      settingsLS = ""
      try:
   	 settingsLS_textI = open(inputEoRFUJsonFile, "r").read()
   	 if(float(debug) >= 50): log.info("trying to load: {0}".format(inputEoRFUJsonFile))
   	 settingsLS = json.loads(settingsLS_textI)
      except ValueError, e:
   	 log.warning("Looks like the file {0} is not available, I'll try again...".format(inputEoRFUJsonFile))
   	 try:
   	    time.sleep (0.1)
   	    settingsLS_textI = open(inputEoRFUJsonFile, "r").read()
            settingsLS = json.loads(settingsLS_textI)
   	 except ValueError, e:
   	    log.warning("Looks like the file {0} is not available (2nd try)...".format(inputEoRFUJsonFile))
   	    time.sleep (1.0)
   	    settingsLS_textI = open(inputEoRFUJsonFile, "r").read()
            settingsLS = json.loads(settingsLS_textI)

      eventsInputFU = eventsInputFU + int(settingsLS['data'][0])
   
   if(float(debug) >= 50): log.info("eventsInputBU vs. eventsInputFU: {0} vs. {1}".format(eventsInputBU,eventsInputFU))
   if (eventsInputBU*completeMergingThreshold <= eventsInputFU):
      numberBoLSFiles = 0
      for nb in range(0, len(afterString)):
   	 if not afterString[nb].endswith("_BoLS.jsn"): continue
         if "DQM" in afterString[nb]: continue
         if "streamError" in afterString[nb]: continue
   	 numberBoLSFiles = numberBoLSFiles + 1
      if(float(debug) >= 50): log.info("numberBoLSFiles: {0}".format(numberBoLSFiles))
      
      EoLSFolder    = os.path.join(path_eol, theRunNumber)
      eventsEoLS    = [0, 0]
      doSumEoLS(EoLSFolder, eventsEoLS)

      if(eventsEoLS[0] != eventsInputBU):
         log.info("PROBLEM eventsEoLS != eventsInputBU: {0} vs. {1}".format(eventsEoLS[0],eventsInputBU))

      # This is needed to cleanUp the macroMerger later
      EoRFileNameMiniOutput	  = outputSMMergedFolder + "/../" + theRunNumber + "_ls0000_MiniEoR_" + outputEndName + ".jsn_TEMP"
      EoRFileNameMiniOutputStable = outputSMMergedFolder + "/../" + theRunNumber + "_ls0000_MiniEoR_" + outputEndName + ".jsn"

      theEoRFileMiniOutput = open(EoRFileNameMiniOutput, 'w')
      theEoRFileMiniOutput.write(json.dumps({'eventsInputBU':   eventsInputBU, 
                                             'eventsInputFU':   eventsInputFU, 
					     'numberBoLSFiles': numberBoLSFiles,
					     'eventsTotalRun':  eventsEoLS[1]}))
      theEoRFileMiniOutput.close()

      shutil.move(EoRFileNameMiniOutput, EoRFileNameMiniOutputStable)

      if(numberBoLSFiles == 0 and eventsInputBU == eventsInputFU):
         EoLSFolder = os.path.join(path_eol, theRunNumber)
         log.info("Run folder deletion is triggered!: {0} and {1}".format(inputDataFolder,EoLSFolder))
         time.sleep(10)
         try:
            shutil.rmtree(inputDataFolder)
   	 except Exception,e:
   	    log.error("Failed removing {0} - {1}".format(inputDataFolder,e))
         try:
            if os.path.islink(EoLSFolder):
               link_dir = os.readlink(EoLSFolder)
               log.info("EoLS run directory is a symlink pointing to {0}".format(link_dir))
               os.unlink(EoLSFolder)
               EoLSFolder = link_dir
            shutil.rmtree(EoLSFolder)
   	 except Exception,e:
   	    log.error("Failed removing {0} - {1}".format(EoLSFolder,e))

def doSumEoLS(inputDataFolder, eventsEoLS):

   after = dict ([(f, None) for f in os.listdir (inputDataFolder)])     
   afterString = [f for f in after]

   # total number of processed events in a given BU
   eventsEoLS[0] = 0
   # total number of processed events in all BUs
   eventsEoLS[1] = 0
   for nb in range(0, len(afterString)):
      if not afterString[nb].endswith("EoLS.jsn"): continue

      EoLSFileName = os.path.join(inputDataFolder, afterString[nb])

      if os.path.exists(EoLSFileName) and os.path.getsize(EoLSFileName) > 0:
         inputEoLSName = open(EoLSFileName, "r").read()
         settingsEoLS  = json.loads(inputEoLSName)
         eventsEoLS[0] += int(settingsEoLS['data'][0])
         eventsEoLS[1] += int(settingsEoLS['data'][2])
