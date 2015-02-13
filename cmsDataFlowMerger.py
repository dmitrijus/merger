#!/usr/bin/env python
import os, time, sys, getopt, fcntl
import shutil
import json
import glob
import multiprocessing
from multiprocessing.pool import ThreadPool
import logging
import thread
import datetime
import fileinput
import socket
import filecmp
import cmsActualMergingFiles
import cmsDataFlowCleanUp
import cmsDataFlowMakeFolders
import zlibextras
import requests

from Logging import getLogger
log = getLogger()

# program to merge (cat) files given a list

"""
Do actual merging
"""

def esMonitorMapping(esServerUrl,esIndexName,numberOfShards,numberOfReplicas,debug):
# subroutine which creates index and mappings in elastic search database
   indexExists = False
   # check if the index exists:
   try:
      checkIndexResponse=requests.get(esServerUrl+'/'+esIndexName+'/_stats/_shards/')
      if '_shards' in json.loads(checkIndexResponse.text):
         if(float(debug) >= 10): log.info('found index '+esIndexName+' containing '+str(json.loads(checkIndexResponse.text)['_shards']['total'])+' total shards')
         indexExists = True
      else:
         if(float(debug) >= 10): log.info('did not find existing index '+esIndexName+', attempting to create it now...')
         indexExists = False
   except requests.exceptions.ConnectionError as e:
      log.error('esMonitorMapping: Could not connect to ElasticSearch database!')
   if indexExists:
      # if the index already exists, we put the mapping in the index for redundancy purposes:
      # JSON follows:
      run_mapping = {
         'run' : {
            '_routing' :{
               'required' : True,
               'path'     : 'runNumber'
            },
            '_id' : {
               'path' : 'runNumber'
            },
            'properties' : {
               'runNumber':{
                  'type':'integer'
                  },
               'startTimeRC':{
                  'type':'date'
                  },
               'stopTimeRC':{
                  'type':'date'
                  },
               'startTime':{
                  'type':'date'
                  },
               'endTime':{
                  'type':'date'
                  },
               'completedTime' : {
                  'type':'date'
                  }
            },
            '_timestamp' : {
               'enabled' : True,
               'store'   : 'yes'
               }
         }
      }
      minimerge_mapping = {
         'minimerge' : {
            '_id'        :{'path':'id'},
            '_parent'    :{'type':'run'},
            'properties' : {
               'fm_date'       :{'type':'date'},
               'id'            :{'type':'string'}, #run+appliance+stream+ls
               'appliance'     :{'type':'string'},
               'stream'        :{'type':'string','index' : 'not_analyzed'},
               'ls'            :{'type':'integer'},
               'processed'     :{'type':'integer'},
               'accepted'      :{'type':'integer'},
               'errorEvents'   :{'type':'integer'},
               'size'          :{'type':'long'},
            }
         }
      }
      macromerge_mapping = {
         'macromerge' : {
            '_id'        :{'path':'id'},
            '_parent'    :{'type':'run'},
            'properties' : {
               'fm_date'       :{'type':'date'},
               'id'            :{'type':'string'}, #run+appliance+stream+ls
               'appliance'     :{'type':'string'},
               'stream'        :{'type':'string','index' : 'not_analyzed'},
               'ls'            :{'type':'integer'},
               'processed'     :{'type':'integer'},
               'accepted'      :{'type':'integer'},
               'errorEvents'   :{'type':'integer'},
               'size'          :{'type':'long'},
            }
         }
      }
      try:
         putMappingResponse=requests.put(esServerUrl+'/'+esIndexName+'/_mapping/run',data=json.dumps(run_mapping))
         putMappingResponse=requests.put(esServerUrl+'/'+esIndexName+'/_mapping/minimerge',data=json.dumps(minimerge_mapping))
         putMappingResponse=requests.put(esServerUrl+'/'+esIndexName+'/_mapping/macromerge',data=json.dumps(macromerge_mapping))
      except requests.exceptions.ConnectionError as e:
         log.error('esMonitorMapping: Could not connect to ElasticSearch database!')
   else:   
      # if the index/mappings don't exist, we must create them both:
      # JSON data for index settings, and merge document mappings
      settings = {
         "analysis":{
            "analyzer": {
               "prefix-test-analyzer": {
                  "type": "custom",
                     "tokenizer": "prefix-test-tokenizer"
                  }
            },
            "tokenizer": {
               "prefix-test-tokenizer": {
                  "type": "path_hierarchy",
                  "delimiter": " "
               }
            }
         },
         "index":{
            'number_of_shards' : numberOfShards,
            'number_of_replicas' : numberOfReplicas
         },
      }
      mapping = {
         'run' : {
            '_routing' :{
               'required' : True,
               'path'     : 'runNumber'
            },
            '_id' : {
               'path' : 'runNumber'
            },
            'properties' : {
               'runNumber':{
                  'type':'integer'
                  },
               'startTimeRC':{
                  'type':'date'
                  },
               'stopTimeRC':{
                  'type':'date'
                  },
               'startTime':{
                  'type':'date'
                  },
               'endTime':{
                  'type':'date'
                  },
               'completedTime' : {
                  'type':'date'
                  }
            },
            '_timestamp' : {
               'enabled' : True,
               'store'   : 'yes'
               }
         },
         'minimerge' : {
            '_id'        :{'path':'id'},
            '_parent'    :{'type':'run'},
            'properties' : {
               'fm_date'       :{'type':'date'},
               'id'            :{'type':'string'}, #run+appliance+stream+ls
               'appliance'     :{'type':'string'},
               'stream'        :{'type':'string','index' : 'not_analyzed'},
               'ls'            :{'type':'integer'},
               'processed'     :{'type':'integer'},
               'accepted'      :{'type':'integer'},
               'errorEvents'   :{'type':'integer'},
               'size'          :{'type':'integer'},
            }
         },
         'macromerge' : {
            '_id'        :{'path':'id'},
            '_parent'    :{'type':'run'},
            'properties' : {
               'fm_date'       :{'type':'date'},
               'id'            :{'type':'string'}, #run+appliance+stream+ls
               'appliance'     :{'type':'string'},
               'stream'        :{'type':'string','index' : 'not_analyzed'},
               'ls'            :{'type':'integer'},
               'processed'     :{'type':'integer'},
               'accepted'      :{'type':'integer'},
               'errorEvents'   :{'type':'integer'},
               'size'          :{'type':'integer'},
            }
         }
      }
      try:
         createIndexResponse=requests.post(esServerUrl+'/'+esIndexName,data=json.dumps({ 'settings': settings, 'mappings': mapping }))
      except requests.exceptions.ConnectionError as e:
         log.error('esMonitorMapping: Could not connect to ElasticSearch database!')

def mergeFiles(outputMergedFolder, outputSMMergedFolder, outputDQMMergedFolder, outputECALMergedFolder, doCheckSum, outMergedFile, outMergedJSON, inputDataFolder, infoEoLS, eventsO, filesDyn, checkSum, fileSize, filesJSONDyn, errorCode, mergeType, doRemoveFiles, outputEndName, optionMerging, esServerUrl, esIndexName, debug):

   # making them local
   files     = [word_in_list for word_in_list in filesDyn]
   filesJSON = [word_in_list for word_in_list in filesJSONDyn]

   # streamDQMHistograms stream uses always with optionA
   fileNameString = filesJSON[0].replace(inputDataFolder,"").replace("/","").split('_')

   if ((optionMerging == "optionA") or ("DQM" in fileNameString[2]) or ("streamError" in fileNameString[2]) or ("streamHLTRates" in fileNameString[2]) or ("streamL1Rates" in fileNameString[2])):
      try:
         cmsActualMergingFiles.mergeFilesA(outputMergedFolder,                       outputDQMMergedFolder, outputECALMergedFolder, doCheckSum, outMergedFile, outMergedJSON, inputDataFolder, infoEoLS, eventsO, files, checkSum, fileSize, filesJSON, errorCode, mergeType, doRemoveFiles, outputEndName, esServerUrl, esIndexName, debug)
      except OSError, e:
         log.error("cmsActualMergingFilesA crashed: {0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}, {9}".format(outputMergedFolder, outMergedFile, outMergedJSON, inputDataFolder, infoEoLS, eventsO, files, checkSum, fileSize, filesJSON, errorCode))

   elif (optionMerging == "optionB"):
      try:
         cmsActualMergingFiles.mergeFilesB(outputMergedFolder, outputSMMergedFolder,                        outputECALMergedFolder, doCheckSum, outMergedFile, outMergedJSON, inputDataFolder, infoEoLS, eventsO, files, checkSum, fileSize, filesJSON, errorCode, mergeType, doRemoveFiles, outputEndName, esServerUrl, esIndexName, debug)
      except OSError, e:
         log.error("cmsActualMergingFilesB crashed: {0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}, {9}".format(outputMergedFolder, outMergedFile, outMergedJSON, inputDataFolder, infoEoLS, eventsO, files, checkSum, fileSize, filesJSON, errorCode))

   elif (optionMerging == "optionC"):
      try:
         cmsActualMergingFiles.mergeFilesC(outputMergedFolder, outputSMMergedFolder,                        outputECALMergedFolder, doCheckSum, outMergedFile, outMergedJSON, inputDataFolder, infoEoLS, eventsO, files, checkSum, fileSize, filesJSON, errorCode, mergeType, doRemoveFiles, outputEndName, esServerUrl, esIndexName, debug)
      except OSError, e:
         log.error("cmsActualMergingFilesC crashed: {0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}, {9}".format(outputMergedFolder, outMergedFile, outMergedJSON, inputDataFolder, infoEoLS, eventsO, files, checkSum, fileSize, filesJSON, errorCode))

   else:
      log.error("Wrong option!: {0}".format(optionMerging))
      msg = "Wrong option!: %s" % (optionMerging)
      raise RuntimeError, msg

"""
Function to copy files
"""
def copyFiles(debug, inputDataFolder, outputMergedFolder, fileName, jsonName, theRunNumber):
   if(float(debug) >= 10): log.info("moving parameters files: {0} {1} {2} {3}".format(inputDataFolder, outputMergedFolder, fileName, jsonName))
   inpMergedFileFullPath       = os.path.join(inputDataFolder,    fileName)
   inpMergedJSONFullPath       = os.path.join(inputDataFolder,    jsonName)

   outputMergedFolderFullPath      = outputMergedFolder + "/../" + theRunNumber
   outputMergedFolderFullPathOpen  = outputMergedFolder + "/../" + theRunNumber + "/open"

   outMergedFileFullPath       = outputMergedFolderFullPath + "/open/" + fileName
   outMergedJSONFullPath       = outputMergedFolderFullPath + "/open/" + jsonName
   outMergedFileFullPathStable = outputMergedFolderFullPath + "/"      + fileName
   outMergedJSONFullPathStable = outputMergedFolderFullPath + "/"      + jsonName.replace("_TEMP.jsn",".jsn")

   initMergingTime = time.time()
   now = datetime.datetime.now()
   if(float(debug) > 0): log.info("{0}: Start moving of {1}".format(now.strftime("%H:%M:%S"), outMergedFileFullPathStable))

   if not os.path.exists(outputMergedFolderFullPathOpen):
      log.warning("Moving operation, folder did not exist, {0}, creating it".format(outputMergedFolderFullPathOpen))
      try:
   	 os.makedirs(outputMergedFolderFullPathOpen)
      except OSError, e:
   	 log.warning("Looks like the directory {0} has just been created by someone else...".format(outputMergedFolderFullPathOpen))

   if(float(debug) >= 10): log.info("moving info: {0} {1} {2} {3} {2} {3}".format(inpMergedFileFullPath, outMergedFileFullPath, outMergedFileFullPathStable, 
                                                                                  inpMergedJSONFullPath, outMergedJSONFullPath, outMergedJSONFullPathStable))

   # moving dat files
   if not os.path.exists(inpMergedFileFullPath):
      log.error("COPY PROBLEM, inpMergedFileFullPath does not exist: {0}".format(inpMergedFileFullPath))

   try:
      shutil.move(inpMergedFileFullPath,outMergedFileFullPath)
   except OSError, e:
      log.error("copy dat file failed: {0}, {1}".format(inpMergedFileFullPath,outMergedFileFullPath))

   if not os.path.exists(outMergedFileFullPath):
      log.error("COPY PROBLEM, outMergedFileFullPath does not exist: {0}".format(outMergedFileFullPath))

   try:
      shutil.move(outMergedFileFullPath,outMergedFileFullPathStable)
   except OSError, e:
      log.error("move dat file failed: {0}, {1}".format(outMergedFileFullPath,outMergedFileFullPathStable))

   # moving json files
   if not os.path.exists(inpMergedJSONFullPath):
      log.error("COPY PROBLEM, inpMergedJSONFullPath does not exist: {0}".format(inpMergedJSONFullPath))

   try:
      shutil.move(inpMergedJSONFullPath,outMergedJSONFullPath)
   except OSError, e:
      log.error("copy json file failed: {0}, {1}".format(inpMergedJSONFullPath,outMergedJSONFullPath))

   # moving json files
   if not os.path.exists(outMergedJSONFullPath):
      log.error("COPY PROBLEM, outMergedJSONFullPath does not exist: {0}".format(outMergedJSONFullPath))

   try:
      shutil.move(outMergedJSONFullPath,outMergedJSONFullPathStable)
   except OSError, e:
      log.error("move json file failed: {0}, {1}".format(outMergedJSONFullPath,outMergedJSONFullPathStable))

   endMergingTime = time.time() 
   now = datetime.datetime.now()
   if(float(debug) > 0): log.info("{0}, : Time for moving({1}): {2}".format(now.strftime("%H:%M:%S"), outMergedFileFullPathStable, endMergingTime-initMergingTime))

"""
Functions to handle errors properly
"""
def error(msg, *args):
    return multiprocessing.get_logger().error(msg, *args)

class LogExceptions(object):
    def __init__(self, callable):
        self.__callable = callable
        return

    def __call__(self, *args, **kwargs):
        try:
            result = self.__callable(*args, **kwargs)

        except Exception as e:
            # Here we add some debugging help. If multiprocessing's
            # debugging is on, it will arrange to log the traceback
            error(traceback.format_exc())
            # Re-raise the original exception so the ThreadPool worker can
            # clean up
            raise

        # It was fine, give a normal answer
        return result
    pass

class LoggingPool(ThreadPool):
    def apply_async(self, func, args=(), kwds={}, callback=None):
        return ThreadPool.apply_async(self, LogExceptions(func), args, kwds, callback)

"""
Do recovering JSON files
"""
def doTheRecovering(paths_to_watch, debug, streamType):
   inputDataFolders = glob.glob(paths_to_watch)
   log.info("Recovering: inputDataFolders: {0}".format(inputDataFolders))
   if(float(debug) >= 10): log.info("**************recovering JSON files***************")
   for nf in range(0, len(inputDataFolders)):
      inputDataFolder = inputDataFolders[nf]	   
      # reading the list of files in the given folder
      before = dict ([(f, None) for f in os.listdir (inputDataFolder)])
      after = dict ([(f, None) for f in os.listdir (inputDataFolder)])     
      afterString = [f for f in after]
      added = [f for f in after if not f in before]
      removed = [f for f in before if not f in after]

      # loop over JSON files, which will give the list of files to be recovered
      for i in range(0, len(afterString)):
         if(streamType != "0" and (afterString[i].endswith(".jsn") or afterString[i].endswith(".ini"))):
            fileString = afterString[i].split('_')
            if  (streamType == "onlyStreamA" and fileString[2] != "StreamA"): continue
            elif(streamType == "noStreamA"   and fileString[2] == "StreamA"): continue
      
         if afterString[i].endswith("_TEMP.jsn"):
            inputJsonFile = os.path.join(inputDataFolder, afterString[i])
            inputJsonRenameFile = inputJsonFile.replace("_TEMP.jsn",".jsn")
            shutil.move(inputJsonFile,inputJsonRenameFile)
         if afterString[i].endswith("_TEMP.ini"):
            inputIniFile = os.path.join(inputDataFolder, afterString[i])
            inputIniRenameFile = inputIniFile.replace("_TEMP.ini",".ini")
            shutil.move(inputIniFile,inputIniRenameFile)

"""
Check if file is completed
"""
def is_completed(filepath):
   """Checks if a file is completed by opening it in append mode.
   If no exception thrown, then the file is not locked.
   """
   completed = False
   file_object = None
   buffer_size = 8
   # Opening file in append mode and read the first 8 characters
   file_object = open(filepath, 'a', buffer_size)
   if file_object:
      completed = True
      file_object.close()

   return completed

"""
Do loops
"""
def doTheMerging(paths_to_watch, path_eol, mergeType, streamType, debug, outputMerge, outputSMMerge, outputDQMMerge, outputECALMerge, doCheckSum, outputEndName, doRemoveFiles, optionMerging, triggerMergingThreshold, completeMergingThreshold, esServerUrl, esIndexName):
   filesDict      = dict() 
   fileSizeDict   = dict() 
   errorCodeDict  = dict()    
   jsonsDict      = dict()    
   eventsIDict    = dict()
   eventsODict    = dict()
   eventsEoLSDict = dict()
   nFilesBUDict   = dict() 
   checkSumDict   = dict()
   if(float(debug) >= 10): log.info("I will watch: {0}".format(paths_to_watch))
   # Maximum number with pool option (< 0 == always)
   nWithPollMax = -1
   # Maximum number of threads to be allowed with the pool option
   nThreadsMax  = 100
   # Number of loops
   nLoops = 0
   while 1:
      # conservative call
      #thePool = ThreadPool(nThreadsMax)
      # agressive call
      multiprocessing.log_to_stderr()
      multiprocessing.get_logger().setLevel(logging.ERROR)
      thePool = LoggingPool(processes=nThreadsMax)

      nLoops = nLoops + 1
      inputDataFolders = glob.glob(paths_to_watch)
      if(float(debug) >= 20 or nLoops%10000 == 1): log.info("***************NEW LOOP************** {0}".format(nLoops))
      if(float(debug) >= 20 or nLoops%10000 == 1): log.info("inputDataFolders: {0}".format(inputDataFolders))
      for nf in range(0, len(inputDataFolders)):
          inputDataFolder = inputDataFolders[nf]
	  # making output folders
	  inputDataFolderString = inputDataFolder.split('/')
	  # if statement to allow ".../" or ... for input folders 
	  if inputDataFolderString[len(inputDataFolderString)-1] == '':
	    outputMergedFolder    = os.path.join(outputMerge,    inputDataFolderString[len(inputDataFolderString)-2], "open")
	    outputSMMergedFolder  = os.path.join(outputSMMerge,  inputDataFolderString[len(inputDataFolderString)-2], "open")
	    outputDQMMergedFolder = os.path.join(outputDQMMerge, inputDataFolderString[len(inputDataFolderString)-2], "open")
	    outputECALMergedFolder= os.path.join(outputECALMerge,inputDataFolderString[len(inputDataFolderString)-2])
	    theRunNumber          = inputDataFolderString[len(inputDataFolderString)-2]
	    outputBadFolder       = os.path.join(outputMerge,    inputDataFolderString[len(inputDataFolderString)-2], "bad")
	    outputSMBadFolder     = os.path.join(outputSMMerge,  inputDataFolderString[len(inputDataFolderString)-2], "bad")
          else:
	    outputMergedFolder    = os.path.join(outputMerge,    inputDataFolderString[len(inputDataFolderString)-1], "open")
	    outputSMMergedFolder  = os.path.join(outputSMMerge,  inputDataFolderString[len(inputDataFolderString)-1], "open")
	    outputDQMMergedFolder = os.path.join(outputDQMMerge, inputDataFolderString[len(inputDataFolderString)-1], "open")
	    outputECALMergedFolder= os.path.join(outputECALMerge,inputDataFolderString[len(inputDataFolderString)-1])
	    theRunNumber          = inputDataFolderString[len(inputDataFolderString)-1] 
	    outputBadFolder       = os.path.join(outputMerge,    inputDataFolderString[len(inputDataFolderString)-1], "bad")
	    outputSMBadFolder     = os.path.join(outputSMMerge,  inputDataFolderString[len(inputDataFolderString)-1], "bad")

	  cmsDataFlowMakeFolders.doMakeFolders(outputMergedFolder, outputSMMergedFolder, outputDQMMergedFolder, outputECALMergedFolder, outputBadFolder, outputSMBadFolder, mergeType)

	  # reading the list of files in the given folder
          before = dict ([(f, None) for f in os.listdir (inputDataFolder)])
          if(float(debug) >= 50): time.sleep (1)
          if(float(debug) >= 20): log.info("Begin folder iteration")
          after = dict ([(f, None) for f in os.listdir (inputDataFolder)])     
          afterString = [f for f in after]
          added = [f for f in after if not f in before]
          if(float(debug) >= 50): log.info("afterString: {0}".format(afterString))
          removed = [f for f in before if not f in after]
          if added: 
             if(float(debug) >= 50): log.info("Added: {0}".format(added))
          if removed: 
             if(float(debug) >= 50): log.info("Removed: {0}".format(removed))

	  # loop over ini files, needs to be done first of all
	  for i in range(0, len(afterString)):

	     if(afterString[i].endswith(".ini") and "TEMP" not in afterString[i]):
          	inputName  = os.path.join(inputDataFolder,afterString[i])
          	if (float(debug) >= 10): log.info("inputName: {0}".format(inputName))

                fileIniString = afterString[i].split('_')
                if  (streamType == "onlyStreamA" and fileIniString[2] != "StreamA"): continue
                elif(streamType == "noStreamA"   and fileIniString[2] == "StreamA"): continue

          	if((mergeType == "mini") or (optionMerging == "optionA") or ("DQM" in fileIniString[2]) or ("streamError" in fileIniString[2]) or ("streamHLTRates" in fileIniString[2]) or ("streamL1Rates" in fileIniString[2])):
          	    theIniOutputFolder = outputSMMergedFolder
	  	    #if((optionMerging == "optionA") or ("DQM" in fileIniString[2]) or ("streamError" in fileIniString[2]) or ("streamHLTRates" in fileIniString[2]) or ("streamL1Rates" in fileIniString[2])):
          	    #   theIniOutputFolder = outputMergedFolder

          	if (is_completed(inputName) == True and (os.path.getsize(inputName) > 0 or fileIniString[2] == "streamError" or fileIniString[2] == "streamDQMHistograms")):
	     	   # init name: runxxx_ls0000_streamY_HOST.ini
	     	   inputNameString = afterString[i].split('_')
          	   # outputIniName will be modified in the next merging step immediately, while outputIniNameToCompare will stay forever
	     	   outputIniNameTEMP          = theIniOutputFolder +    "/" + inputNameString[0] + "_ls0000_" + inputNameString[2] + "_" +    outputEndName + ".ini_TMP1"
	     	   outputIniName              = theIniOutputFolder + "/../" + inputNameString[0] + "_ls0000_" + inputNameString[2] + "_" +    outputEndName + ".ini"
          	   outputIniNameToCompareTEMP = theIniOutputFolder +    "/" + inputNameString[0] + "_ls0000_" + inputNameString[2] + "_" +    outputEndName + ".ini_TMP2"
          	   outputIniNameToCompare     = theIniOutputFolder +    "/" + inputNameString[0] + "_ls0000_" + inputNameString[2] + "_" + "StorageManager" + ".ini"
	     	   inputNameRename  = inputName.replace(".ini","_TEMP.ini")
          	   shutil.move(inputName,inputNameRename)
          	   if(float(debug) >= 10): log.info("iniFile: {0}".format(afterString[i]))
	  	   # getting the ini file, just once per stream
	     	   if (not os.path.exists(outputIniNameToCompare) or (fileIniString[2] != "streamError" and fileIniString[2] != "streamDQMHistograms" and os.path.exists(outputIniNameToCompare) and os.path.getsize(outputIniNameToCompare) == 0)):
	     	      try:
          		 with open(outputIniNameToCompareTEMP, 'a', 1) as file_object:
          		    fcntl.flock(file_object, fcntl.LOCK_EX)
	     		    shutil.copy(inputNameRename,outputIniNameToCompareTEMP)
          		    fcntl.flock(file_object, fcntl.LOCK_UN)
	     		 file_object.close()
                         shutil.move(outputIniNameToCompareTEMP,outputIniNameToCompare)
	     	      except OSError, e:
	     		 log.warning("Looks like the outputIniNameToCompare file {0} has just been created by someone else...".format(outputIniNameToCompare))

	  	   # otherwise, checking if they are identical
	  	   else:
          	      try:
	     		 if filecmp.cmp(outputIniNameToCompare,inputNameRename) == False:
	     		    log.warning("ini files: {0} and {1} are different!!!".format(outputIniNameToCompare,inputNameRename))
          	      except IOError, e:
          		    log.error("Try to move a .ini to a _TEMP.ini, disappeared under my feet. Carrying on...")

	     	   if (not os.path.exists(outputIniName) or (fileIniString[2] != "streamError" and fileIniString[2] != "streamDQMHistograms" and os.path.exists(outputIniName) and os.path.getsize(outputIniName) == 0)):
	     	      try:
          		 with open(outputIniNameTEMP, 'a', 1) as file_object:
          		    fcntl.flock(file_object, fcntl.LOCK_EX)
	     		    shutil.copy(inputNameRename,outputIniNameTEMP)
          		    fcntl.flock(file_object, fcntl.LOCK_UN)
	     		 file_object.close()
                         shutil.move(outputIniNameTEMP,outputIniName)
	     	      except OSError, e:
	     		 log.warning("Looks like the outputIniName file {0} has just been created by someone else...".format(outputIniName))

	  	   # otherwise, checking if they are identical
	  	   else:
          	      try:
	     		 if filecmp.cmp(outputIniName,inputNameRename) == False:
	     		    log.warning("ini files: {0} and {1} are different!!!".format(outputIniName,inputNameRename))
          	      except IOError, e:
          		    log.error("Try to move a .ini to a _TEMP.ini, disappeared under my feet. Carrying on...")

          	   if(doRemoveFiles == "True"): 
          	      os.remove(inputNameRename)

                   # only for streamHLTRates and streamL1Rates, need another file
                   if(("streamHLTRates" in fileIniString[2]) or ("streamL1Rates" in fileIniString[2])):
	     	      inputJsdNameString = afterString[i].split('_')
		      inputJsdName  = inputDataFolder + "/"  + inputJsdNameString[0] + "_ls0000_" + inputJsdNameString[2] + ".jsd"
		      if(os.path.exists(inputJsdName)):
          		 # outputIniName will be modified in the next merging step immediately, while outputIniNameToCompare will stay forever
	     		 outputIniNameTEMP          = outputMergedFolder +    "/" + inputJsdNameString[0] + "_ls0000_" + inputJsdNameString[2] + "_" +    outputEndName  + ".jsd_TMP1"
	     		 outputIniName              = outputMergedFolder + "/../" + inputJsdNameString[0] + "_ls0000_" + inputJsdNameString[2]  			 + ".jsd"
          		 outputIniNameToCompareTEMP = outputMergedFolder +    "/" + inputJsdNameString[0] + "_ls0000_" + inputJsdNameString[2] + "_" +    outputEndName  + ".jsd_TMP2"
          		 outputIniNameToCompare     = outputMergedFolder +    "/" + inputJsdNameString[0] + "_ls0000_" + inputJsdNameString[2]  			 + ".jsd"
          		 if(float(debug) >= 10): log.info("iniFile: {0}".format(afterString[i]))
	  		 # getting the ini file, just once per stream
	     		 if (not os.path.exists(outputIniNameToCompare) or (os.path.exists(outputIniNameToCompare) and os.path.getsize(outputIniNameToCompare) == 0)):
	     		    try:
          		       with open(outputIniNameToCompareTEMP, 'a', 1) as file_object:
          			  fcntl.flock(file_object, fcntl.LOCK_EX)
	     			  shutil.copy(inputJsdName,outputIniNameToCompareTEMP)
          			  fcntl.flock(file_object, fcntl.LOCK_UN)
	     		       file_object.close()
                               shutil.move(outputIniNameToCompareTEMP,outputIniNameToCompare)
	     		    except OSError, e:
	     		       log.warning("Looks like the outputIniNameToCompare-Rates file {0} has just been created by someone else...".format(outputIniNameToCompare))

	  		 # otherwise, checking if they are identical
	  		 else:
          		    try:
	     		       if filecmp.cmp(outputIniNameToCompare,inputJsdName) == False:
	     			  log.warning("ini files: {0} and {1} are different!!!".format(outputIniNameToCompare,inputJsdName))
          		    except IOError, e:
          			  log.error("Try to move a .ini to a _TEMP.ini, disappeared under my feet. Carrying on...")

	     		 if (not os.path.exists(outputIniName) or (os.path.exists(outputIniName) and os.path.getsize(outputIniName) == 0)):
	     		    try:
          		       with open(outputIniNameTEMP, 'a', 1) as file_object:
          			  fcntl.flock(file_object, fcntl.LOCK_EX)
	     			  shutil.copy(inputJsdName,outputIniNameTEMP)
          			  fcntl.flock(file_object, fcntl.LOCK_UN)
	     		       file_object.close()
                               shutil.move(outputIniNameTEMP,outputIniName)
	     		    except OSError, e:
	     		       log.warning("Looks like the outputIniName-Rates file {0} has just been created by someone else...".format(outputIniName))

	  		 # otherwise, checking if they are identical
	  		 else:
          		    try:
	     		       if filecmp.cmp(outputIniName,inputJsdName) == False:
	     			  log.warning("ini files: {0} and {1} are different!!!".format(outputIniName,inputJsdName))
          		    except IOError, e:
          			  log.error("Try to move a .ini to a _TEMP.ini, disappeared under my feet. Carrying on...")

                      else:
                         log.error("jsd file does not exists!: {0}".format(inputJsdName))

	     	else:
	     	   log.info("Looks like the file {0} is being copied by someone else...".format(inputName))

	  # loop over JSON files, which will give the list of files to be merged
	  for i in range(0, len(afterString)):
	     if not afterString[i].endswith(".jsn"): continue
	     if "index" in afterString[i]: continue
	     if afterString[i].endswith("recv"): continue
	     if "EoLS" in afterString[i]: continue
	     if "BoLS" in afterString[i]: continue
	     if "EoR" in afterString[i]: continue
	     if "TEMP" in afterString[i]: continue

             fileNameString = afterString[i].split('_')
             if  (streamType == "onlyStreamA" and fileNameString[2] != "StreamA"): continue
             elif(streamType == "noStreamA"   and fileNameString[2] == "StreamA"): continue

	     if(float(debug) >= 50): log.info("FILE: {0}".format(afterString[i]))
	     inputJsonFile = os.path.join(inputDataFolder, afterString[i])
	     if(float(debug) >= 50): log.info("inputJsonFile: {0}".format(inputJsonFile))

             # avoid empty files
	     if(os.path.exists(inputJsonFile) and os.path.getsize(inputJsonFile) == 0): continue

             isFailed = False
             # moving the file to avoid issues
	     inputJsonRenameFile = inputJsonFile.replace(".jsn","_TEMP.jsn")
             shutil.move(inputJsonFile,inputJsonRenameFile)

	     try:
                settings_textI = open(inputJsonRenameFile, "r").read()
                if(float(debug) >= 50): log.info("trying to load: {0}".format(inputJsonRenameFile))
	        settings = json.loads(settings_textI)
             except ValueError, e:
                log.warning("Looks like the file {0} is not available, I'll try again...".format(inputJsonRenameFile))
	        try:
	           time.sleep (0.1)
                   settings_textI = open(inputJsonRenameFile, "r").read()
		   settings = json.loads(settings_textI)
                except ValueError, e:
                   log.warning("Looks like the file {0} is not available (2nd try)...".format(inputJsonRenameFile))
	           try:
	              time.sleep (1.0)
                      settings_textI = open(inputJsonRenameFile, "r").read()
		      settings = json.loads(settings_textI)
                   except ValueError, e:
                      log.warning("Looks like the file {0} failed for good (3rd try)...".format(inputJsonRenameFile))
	              inputJsonFailedFile = inputJsonRenameFile.replace("_TEMP.jsn","_FAILED.bad")
                      shutil.move(inputJsonRenameFile,inputJsonFailedFile)
                      isFailed = True

             # This is just for streamEvD files
             if  (isFailed == False and fileNameString[2] == "streamEvDOutput"):
                isFailed = True
		fileName = str(settings['data'][4])
                jsonName = afterString[i].replace(".jsn","_TEMP.jsn")
                theRunNumber = afterString[i].split('_')[0]

                process = thePool.apply_async(copyFiles, [debug, inputDataFolder, outputMergedFolder, fileName, jsonName, theRunNumber])

             # avoid corrupted files or streamEvD files
	     if(isFailed == True): continue

             # this is the number of input and output events, and the name of the dat file, something critical
	     # eventsOutput is actually the total number of events to merge in the macromerged stage
             eventsInput       = int(settings['data'][0])
             eventsOutput      = int(settings['data'][1])
             errorCode         = 0
	     file              = ""
	     fileErrorString   = None
	     fileSize          = 0
             nFilesBU          = 0
             eventsTotalInput  = 0
             checkSum          = 0
	     if mergeType == "mini":
                eventsOutputError = int(settings['data'][2])
		errorCode	  = int(settings['data'][3])
		file              = str(settings['data'][4])
		fileSize          = int(settings['data'][5])
		if(len(settings['data']) > 7):
		   checkSum       = int(settings['data'][7])
                #else:
                #   log.warning("wrong format for checksum: {0}".format(afterString[i]))
	        if(float(debug) >= 50): log.info("Info from json file(eventsInput, eventsOutput, eventsOutputError, errorCode, file, fileSize): {0}, {1}, {2}, {3}, {4}, {5}".format(eventsInput, eventsOutput, eventsOutputError, errorCode, file, fileSize))
	        # processed events == input + error events
		eventsInput = eventsInput + eventsOutputError
		
		if fileNameString[2] == "streamError":
		   file            = str(settings['data'][6])
		   fileErrorString = file.split(',')
	     else:
		errorCode	 = int(settings['data'][2])
		file             = str(settings['data'][3])
		fileSize         = int(settings['data'][4])
		if(len(settings['data']) > 7):
		   checkSum         = int(settings['data'][5])
                   nFilesBU         = int(settings['data'][6])
                   eventsTotalInput = int(settings['data'][7])
                else:
		   checkSum         = 0
                   nFilesBU         = int(settings['data'][5])
                   eventsTotalInput = int(settings['data'][6])
                   #log.warning("wrong format for checksum: {0}".format(afterString[i]))

             key = (fileNameString[0],fileNameString[1],fileNameString[2])
             if key in filesDict.keys():
	        if fileErrorString != None and len(fileErrorString) >= 2:
	           for theFiles in range(0, len(fileErrorString)):
		      filesDict[key].append(fileErrorString[theFiles])
	     	else:
		   filesDict[key].append(file)
	     	jsonsDict[key].append(inputJsonRenameFile)

                errorCode = (errorCodeDict[key][0]|errorCode)
	     	errorCodeDict[key].remove(errorCodeDict[key][0])
                errorCodeDict.update({key:[errorCode]})

		eventsInput = eventsIDict[key][0] + eventsInput
	     	eventsIDict[key].remove(eventsIDict[key][0])
	     	eventsIDict.update({key:[eventsInput]})

		eventsOutput = eventsODict[key][0] + eventsOutput
	     	eventsODict[key].remove(eventsODict[key][0])
	     	eventsODict.update({key:[eventsOutput]})

		# Needs to be computed before the fileSize is updated
		checkSum = zlibextras.adler32_combine(checkSumDict[key][0],checkSum,fileSize)
		checkSum = checkSum & 0xffffffff
	     	checkSumDict[key].remove(checkSumDict[key][0])
	     	checkSumDict.update({key:[checkSum]})

		fileSize = fileSizeDict[key][0] + fileSize
	     	fileSizeDict[key].remove(fileSizeDict[key][0])
	     	fileSizeDict.update({key:[fileSize]})

		nFilesBU = nFilesBUDict[key][0] + nFilesBU
	     	nFilesBUDict[key].remove(nFilesBUDict[key][0])
	     	nFilesBUDict.update({key:[nFilesBU]})

	     else:
                if(float(debug) >= 50): log.info("Adding {0} to filesDict".format(key))
	        if fileErrorString != None and len(fileErrorString) >= 2:
		   filesDict.update({key:[fileErrorString[0]]})
	           for theFiles in range(1, len(fileErrorString)):
		      filesDict[key].append(fileErrorString[theFiles])
                else:
		   filesDict.update({key:[file]})

	     	jsonsDict.update({key:[inputJsonRenameFile]})
                errorCodeDict.update({key:[errorCode]})

	     	eventsIDict.update({key:[eventsInput]})

	     	eventsODict.update({key:[eventsOutput]})

	     	checkSumDict.update({key:[checkSum]})

	     	fileSizeDict.update({key:[fileSize]})

	     	nFilesBUDict.update({key:[nFilesBU]})

             if(float(debug) >= 50): log.info("filesDict: {0}\njsonsDict: {1}\n, eventsIDict: {2}, eventsODict: {3}, checkSumDict: {4} fileSizeDict: {5}, nFilesBUDict: {6}, errorCodeDict: {7}".format(filesDict, jsonsDict, eventsIDict, eventsODict, checkSumDict, fileSizeDict, nFilesBUDict, errorCodeDict))

             theOutputEndName = outputEndName
	     if (optionMerging != "optionA" and ("DQM" not in fileNameString[2]) and ("streamError" not in fileNameString[2]) and ("streamHLTRates" not in fileNameString[2]) and ("streamL1Rates" not in fileNameString[2])):
                theOutputEndName = "StorageManager"

             extensionName = ".dat"
             if fileNameString[2] == "streamError":
                extensionName = ".raw"
             elif fileNameString[2] == "streamDQMHistograms":
                extensionName = ".pb"
             elif (fileNameString[2] == "streamHLTRates" or fileNameString[2] == "streamL1Rates"):
                extensionName = ".jsndata"

	     if mergeType == "mini": 
        	keyEoLS = (fileNameString[0],fileNameString[1])
		if keyEoLS not in eventsEoLSDict.keys():
	           EoLSName = path_eol + "/" + fileNameString[0] + "/" + fileNameString[0] + "_" + fileNameString[1] + "_EoLS.jsn"
                   if(float(debug) >= 10): log.info("EoLSName: {0}".format(EoLSName))
                   if os.path.exists(EoLSName) and os.path.getsize(EoLSName) > 0:
                      inputEoLSName = open(EoLSName, "r").read()
                      settingsEoLS  = json.loads(inputEoLSName)
                      eventsEoLS    = int(settingsEoLS['data'][0])
                      filesEoLS     = int(settingsEoLS['data'][1])
                      eventsAllEoLS = int(settingsEoLS['data'][2])
		      eventsEoLSDict.update({keyEoLS:[eventsEoLS,filesEoLS,eventsAllEoLS]})
                   else:
		      print "PROBLEM WITH: ",EoLSName

        	if keyEoLS in eventsEoLSDict.keys(): # and key in filesDict.keys():
        	#try:
		   if(float(debug) >= 20): log.info("mini-EventsEoLS/EventsInput-LS/Stream: {0}, {1}, {2}, {3}".format(eventsEoLSDict[keyEoLS][0], eventsIDict[key][0], fileNameString[1], fileNameString[2]))
                   if((eventsEoLSDict[keyEoLS][0] == eventsIDict[key][0]) or (eventsEoLSDict[keyEoLS][0]*triggerMergingThreshold <= eventsIDict[key][0] and "DQM" in fileNameString[2] and fileNameString[2] != "streamDQMHistograms")):
		      # merged files
	              outMergedFile = fileNameString[0] + "_" + fileNameString[1] + "_" + fileNameString[2] + "_" + theOutputEndName + extensionName;
	              outMergedJSON = fileNameString[0] + "_" + fileNameString[1] + "_" + fileNameString[2] + "_" +    outputEndName + ".jsn";

                      inputDataFolderModified = inputDataFolder
		      # need to modify the input data area
		      if fileNameString[2] == "streamError":
                         inputDataFolderModified = path_eol + "/" + fileNameString[0]

                      eventsInputReal = []
		      eventsInputReal.append(eventsIDict[key][0])
		      eventsInputReal.append(eventsEoLSDict[keyEoLS][1])
		      eventsInputReal.append(eventsEoLSDict[keyEoLS][2])
                      eventsIDict.update({key:[-1.01*eventsTotalInput]})
                      if(float(debug) > 0): log.info("Spawning merging of {0}".format(outMergedJSON))
                      if nLoops <= nWithPollMax or nWithPollMax < 0:
                         process = thePool.apply_async(         mergeFiles,            [outputMergedFolder, outputSMMergedFolder, outputDQMMergedFolder, outputECALMergedFolder, doCheckSum, outMergedFile, outMergedJSON, inputDataFolderModified, eventsInputReal, eventsODict[key][0], filesDict[key], checkSumDict[key][0], fileSizeDict[key][0], jsonsDict[key], errorCodeDict[key][0], mergeType, doRemoveFiles, outputEndName, optionMerging, esServerUrl, esIndexName, debug])
		      else:
                         #thread.start_new_thread( mergeFiles,                          (outputMergedFolder, outputSMMergedFolder, outputDQMMergedFolder, outputECALMergedFolder, doCheckSum, outMergedFile, outMergedJSON, inputDataFolderModified, eventsInputReal, eventsODict[key][0], filesDict[key], checkSumDict[key][0], fileSizeDict[key][0], jsonsDict[key], errorCodeDict[key][0], mergeType, doRemoveFiles, outputEndName, optionMerging, debug) )
                         process = multiprocessing.Process(target = mergeFiles, args = [outputMergedFolder, outputSMMergedFolder, outputDQMMergedFolder, outputECALMergedFolder, doCheckSum, outMergedFile, outMergedJSON, inputDataFolderModified, eventsInputReal, eventsODict[key][0], filesDict[key], checkSumDict[key][0], fileSizeDict[key][0], jsonsDict[key], errorCodeDict[key][0], mergeType, doRemoveFiles, outputEndName, optionMerging, esServerUrl, esIndexName, debug])
                         process.start()
                   else:
                      if (float(debug) >= 20):
                	  log.info("Events number does not match: EoL says {0} we have in the files: {1}".format(eventsEoLSDict[keyEoLS][0], eventsIDict[key][0]))
        	else:
        	#except Exception:
                      if (float(debug) >= 20):
                	  log.warning("Looks like {0} is not in filesDict".format(key))

             else:
		if(float(debug) >= 20): log.info("macro-EventsTotalInput/EventsInput-LS/Stream: {0}, {1}, {2}, {3}".format(eventsTotalInput,eventsIDict[key][0],fileNameString[1],fileNameString[2]))
                if((eventsTotalInput == eventsIDict[key][0]) or (eventsTotalInput*triggerMergingThreshold <= eventsIDict[key][0] and "DQM" in fileNameString[2] and fileNameString[2] != "streamDQMHistograms")):
	           # merged files
	           outMergedFile = fileNameString[0] + "_" + fileNameString[1] + "_" + fileNameString[2] + "_" + theOutputEndName + extensionName;
	           outMergedJSON = fileNameString[0] + "_" + fileNameString[1] + "_" + fileNameString[2] + "_" + theOutputEndName + ".jsn";

        	   keyEoLS = (fileNameString[0],fileNameString[1])
                   eventsEoLS	 = eventsIDict[key][0]
                   filesEoLS	 = nFilesBUDict[key][0]
                   eventsAllEoLS = eventsTotalInput
		   eventsEoLSDict.update({keyEoLS:[eventsEoLS,filesEoLS,eventsAllEoLS]})

                   eventsInputReal = []
		   eventsInputReal.append(eventsIDict[key][0])
		   eventsInputReal.append(eventsEoLSDict[keyEoLS][1])
		   eventsInputReal.append(eventsEoLSDict[keyEoLS][2])
                   eventsIDict.update({key:[-1.01*eventsTotalInput]})
                   if(float(debug) > 0): log.info("Spawning merging of {0}".format(outMergedJSON))
                   if nLoops <= nWithPollMax or nWithPollMax < 0:
                      process = thePool.apply_async(         mergeFiles,            [outputMergedFolder, outputSMMergedFolder, outputDQMMergedFolder, outputECALMergedFolder, doCheckSum, outMergedFile, outMergedJSON, inputDataFolder, eventsInputReal, eventsODict[key][0], filesDict[key], checkSumDict[key][0], fileSizeDict[key][0], jsonsDict[key], errorCodeDict[key][0], mergeType, doRemoveFiles, outputEndName, optionMerging, esServerUrl, esIndexName, debug])
                   else:
                      #thread.start_new_thread( mergeFiles,                          (outputMergedFolder, outputSMMergedFolder, outputDQMMergedFolder, outputECALMergedFolder, doCheckSum, outMergedFile, outMergedJSON, inputDataFolder, eventsInputReal, eventsODict[key][0], filesDict[key], checkSumDict[key][0], fileSizeDict[key][0], jsonsDict[key], errorCodeDict[key][0], mergeType, doRemoveFiles, outputEndName, optionMerging, debug) )
                      process = multiprocessing.Process(target = mergeFiles, args = [outputMergedFolder, outputSMMergedFolder, outputDQMMergedFolder, outputECALMergedFolder, doCheckSum, outMergedFile, outMergedJSON, inputDataFolder, eventsInputReal, eventsODict[key][0], filesDict[key], checkSumDict[key][0], fileSizeDict[key][0], jsonsDict[key], errorCodeDict[key][0], mergeType, doRemoveFiles, outputEndName, optionMerging, esServerUrl, esIndexName, debug])
                      process.start()
                else:
                   if (float(debug) >= 20):
                       log.info("Events number does not match: EoL says {0}, we have in the files: {1}".format(eventsOutput, eventsIDict[key][0]))

	  # clean-up work is done here
          EoRFileName = path_eol + "/" + theRunNumber + "/" + theRunNumber + "_ls0000_EoR.jsn"
          if(os.path.exists(EoRFileName) and os.path.getsize(EoRFileName) > 0):
	     # need to copy the file to DQM downstream
	     EoRFileNameDQMOutput       = outputMergedFolder + "/../" + theRunNumber + "_ls0000_EoR_" + outputEndName + ".jsn"
	     EoRFileNameDQMOutputFinal  = outputMergedFolder + "/../" + theRunNumber + "_ls0000_EoR.jsn"
	     EoRFileNameECALOutput      = outputMergedFolder + "/../" + theRunNumber + "_ls0000_EoR_" + outputEndName + ".jsn"
	     EoRFileNameECALOutputFinal = outputMergedFolder + "/../" + theRunNumber + "_ls0000_EoR.jsn"
	     if(mergeType == "macro"):
	        EoRFileNameDQMOutput       = outputDQMMergedFolder  + "/" + theRunNumber + "_ls0000_EoR_" + outputEndName + ".jsn"
	        EoRFileNameDQMOutputFinal  = outputDQMMergedFolder  + "/" + theRunNumber + "_ls0000_EoR.jsn"
	        EoRFileNameECALOutput      = outputECALMergedFolder + "/" + theRunNumber + "_ls0000_EoR_" + outputEndName + ".jsn"
	        EoRFileNameECALOutputFinal = outputECALMergedFolder + "/" + theRunNumber + "_ls0000_EoR.jsn"
	     # DQM guys don't want to receive the EoR file for now
	     #if(not os.path.exists(EoRFileNameDQMOutputFinal)):
             #   if(float(debug) >= 10): log.info("copying file: {0} to {1}".format(EoRFileName,EoRFileNameDQMOutputFinal))
             #   try:
	     #     shutil.copy(EoRFileName,EoRFileNameDQMOutput)
             #     shutil.move(EoRFileNameDQMOutput,EoRFileNameDQMOutputFinal)
             #   except OSError, e:
             #      log.warning("copying {0} to {1} failed".format(EoRFileName,EoRFileNameDQMOutputFinal))
	     if(not os.path.exists(EoRFileNameECALOutputFinal)):
                if(float(debug) >= 10): log.info("copying file: {0} to {1}".format(EoRFileName,EoRFileNameECALOutputFinal))
		try:
	          shutil.copy(EoRFileName,EoRFileNameECALOutput)
                  shutil.move(EoRFileNameECALOutput,EoRFileNameECALOutputFinal)
                except OSError, e:
                   log.warning("copying {0} to {1} failed".format(EoRFileName,EoRFileNameECALOutputFinal))

	     if(doRemoveFiles == "True" and mergeType == "mini"):
	        cmsDataFlowCleanUp.cleanUpRun(debug, EoRFileName, inputDataFolder, afterString, path_eol, theRunNumber, outputSMMergedFolder, outputEndName, completeMergingThreshold)

          before = after

      if nLoops <= nWithPollMax or nWithPollMax < 0:
         thePool.close()
         thePool.join()

def start_merging(paths_to_watch, path_eol, mergeType, streamType, outputMerge, outputSMMerge, outputDQMMerge, outputECALMerge, doCheckSum, outputEndName, doRemoveFiles, optionMerging, esServerUrl, esIndexName, numberOfShards, numberOfReplicas, debug):

    triggerMergingThreshold = 0.80
    completeMergingThreshold = 1.0

    if mergeType != "mini" and mergeType != "macro" and mergeType != "auto":
       msg = "Wrong type of merging: %s" % mergeType
       raise RuntimeError, msg
    
    if mergeType == "auto":
       theHost = socket.gethostname()
       if "bu" in theHost.lower():
          mergeType = "mini"
       else:
          mergeType = "macro"
    
    if mergeType == "mini":
       if not os.path.exists(path_eol):
          msg = "End of Lumi folder Not Found: %s" % path_eol
          raise RuntimeError, msg
    
    if not os.path.exists(outputMerge):
       try:
          os.makedirs(outputMerge)
       except OSError, e:
          log.warning("Looks like the directory {0} has just been created by someone else...".format(outputMerge))
    
    if not os.path.exists(outputSMMerge):
       try:
          os.makedirs(outputSMMerge)
       except OSError, e:
          log.warning("Looks like the directory {0} has just been created by someone else...".format(outputSMMerge))
    
    if not os.path.exists(outputDQMMerge) and mergeType == "macro":
       try:
          os.makedirs(outputDQMMerge)
       except OSError, e:
          log.warning("Looks like the directory {0} has just been created by someone else...".format(outputDQMMerge))
    
    if not os.path.exists(outputECALMerge) and mergeType == "macro":
       try:
          os.makedirs(outputECALMerge)
       except OSError, e:
          log.warning("Looks like the directory {0} has just been created by someone else...".format(outputECALMerge))

    if not (esServerUrl == '' or esIndexName==''):
        esMonitorMapping(esServerUrl,esIndexName,numberOfShards,numberOfReplicas,debug)

    doTheRecovering(paths_to_watch, streamType, debug)
    doTheMerging(paths_to_watch, path_eol, mergeType, streamType, debug, outputMerge, outputSMMerge, outputDQMMerge, outputECALMerge, doCheckSum, outputEndName, doRemoveFiles, optionMerging, triggerMergingThreshold, completeMergingThreshold, esServerUrl, esIndexName)
