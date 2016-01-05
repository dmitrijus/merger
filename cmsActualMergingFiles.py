#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, time, sys, getopt, fcntl, random
import shutil
import json
import glob
import multiprocessing
from multiprocessing.pool import ThreadPool
import thread
import datetime
import fileinput
import socket
import filecmp
import zlib
import zlibextras
import requests

from Logging import getLogger
log = getLogger()
max_size = 30 * 1024 * 1024 * 1024
max_retries = 10
max_size_checksum = 2.5 * 1024 * 1024 * 1024

def elasticMonitor(mergeMonitorData, runnumber, mergeType, esServerUrl, esIndexName, maxConnectionAttempts, debug):
   # here the merge action is monitored by inserting a record into Elastic Search database
   connectionAttempts=0 #initialize
   # make dictionary to be JSON-ified and inserted into the Elastic Search DB as a document
   keys = ["processed","accepted","errorEvents","fname","size","eolField1","eolField2","fm_date","ls","stream","id"]
   values = [int(f) if str(f).isdigit() else str(f) for f in mergeMonitorData]
   mergeMonitorDict=dict(zip(keys,values))
   mergeMonitorDict['fm_date']=float(mergeMonitorDict['fm_date'])
   while True:
      try:
  #requests.post(esServerUrl+'/_bulk','{"index": {"_parent": '+str(self.runnumber)+', "_type": "macromerge", "_index": "'+esIndexName+'"}}\n'+json.dumps(mergeMonitorDict)+'\n')
         documentType=mergeType+'merge'
         if(float(debug) >= 10):
            log.info("About to try to insert into ES with the following info:")
            log.info('Server: "' + esServerUrl+'/'+esIndexName+'/'+documentType+'/' + '"')
            log.info("Data: '"+json.dumps(mergeMonitorDict)+"'")
         #attempt to record the merge, 1s timeout!
         monitorResponse=requests.post(esServerUrl+'/'+esIndexName+'/'+documentType+'?parent='+runnumber,data=json.dumps(mergeMonitorDict),timeout=1)
         if(float(debug) >= 10): log.info("Merger monitor produced response: {0}".format(monitorResponse.text))
         break
      except (requests.exceptions.ConnectionError,requests.exceptions.Timeout) as e:
         log.error('elasticMonitor threw connection error: HTTP ' + monitorResponse.status_code)
         log.error(monitorResponse.raise_for_status())
         if connectionAttempts > maxConnectionAttempts:
            log.error('connection error: elasticMonitor failed to record '+documentType+' after '+ str(maxConnectionAttempts)+'attempts')
            break
         else:
            connectionAttempts+=1
            time.sleep(0.1)
         continue
 
"""
merging option A: merging unmerged files to different files for different BUs
"""
def mergeFilesA(inpSubFolder, outSubFolder, outputMergedFolder, outputDQMMergedFolder, outputECALMergedFolder, doCheckSum, outMergedFile, outMergedJSON, inputDataFolder, infoEoLS, eventsO, files, checkSum, fileSize, filesJSON, errorCode, transferDest, mergeType, doRemoveFiles, outputEndName, esServerUrl, esIndexName, debug):
 try:
   if(float(debug) >= 10): log.info("mergeFiles: {0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}, {9}".format(outputMergedFolder, outMergedFile, outMergedJSON, inputDataFolder, infoEoLS, eventsO, files, checkSum, fileSize, filesJSON, errorCode))
   
   outMergedFileFullPath = os.path.join(outputMergedFolder, outSubFolder, "open", outMergedFile)
   outMergedJSONFullPath = os.path.join(outputMergedFolder, outSubFolder, "open", outMergedJSON)
   if(float(debug) >= 10): log.info('outMergedFileFullPath: {0}'.format(outMergedFileFullPath))

   timeReadWrite = [0, 0]
   initMergingTime = time.time()
   if(float(debug) > 0): log.info("Start merge of {0}".format(outMergedJSONFullPath))

   if os.path.exists(outMergedFileFullPath):
      os.remove(outMergedFileFullPath)
   if os.path.exists(outMergedJSONFullPath):
      os.remove(outMergedJSONFullPath)

   inputJsonFolder = os.path.dirname(filesJSON[0])
   fileNameString = filesJSON[0].replace(inputJsonFolder,"").replace("/","").split('_')

   specialStreams = False
   if(fileNameString[2] == "streamDQMHistograms" or fileNameString[2] == "streamHLTRates" or fileNameString[2] == "streamL1Rates"):
      specialStreams = True

   if (mergeType == "macro" and specialStreams == False and infoEoLS[0] != 0):
      iniName = fileNameString[0] + "_ls0000_" + fileNameString[2] + "_" + "StorageManager" + ".ini"
      iniNameFullPath = os.path.join(outputMergedFolder, outSubFolder, "open", iniName)
      if os.path.exists(iniNameFullPath):

         checkSumIni=1
	 n_retries=0
	 while n_retries < max_retries:
            try:
               checkSumIni=1
               with open(iniNameFullPath, 'r') as fsrc:
        	  length=16*1024
      		  while 1:
   		     buf = fsrc.read(length)
   		     if not buf:
   	    		break
   		     checkSumIni=zlib.adler32(buf,checkSumIni)

               checkSumIni = checkSumIni & 0xffffffff
               checkSum = zlibextras.adler32_combine(checkSumIni,checkSum,fileSize)
               checkSum = checkSum & 0xffffffff

               fileSize = os.path.getsize(iniNameFullPath) + fileSize
               filenames = [iniNameFullPath]

               with open(outMergedFileFullPath, 'w') as fout:
                  append_files(filenames, fout, debug, timeReadWrite)
               fout.close()
	       break
            except Exception, e:
               log.warning("Error writing file {0}: {1}, waiting for 30secs".format(outMergedFileFullPath,e))
               n_retries+=1
               time.sleep(30)

         if(n_retries == max_retries):
            log.error("Could not write file {0}!: {0}".format(outMergedFileFullPath))
            msg = "Could not write file {0}!: %s" % (outMergedFileFullPath)
            raise RuntimeError, msg

      else:
         log.error("BIG PROBLEM, ini file not found!: {0}".format(iniNameFullPath))
	 msg = "BIG PROBLEM, ini file not found!: %s" % (iniNameFullPath)
	 raise RuntimeError, msg

   filenames = [inputDataFolder + "/" + inpSubFolder + "/" + word_in_list for word_in_list in files]

   if(float(debug) > 5): log.info("Will merge: {0}".format(filenames))

   if(infoEoLS[0] != 0):
      if (specialStreams == False and mergeType == "macro"):
         with open(outMergedFileFullPath, 'a') as fout:
            append_files(filenames, fout, debug, timeReadWrite)
         fout.close()
   
      elif (specialStreams == False):
	 n_retries=0
	 while n_retries < max_retries:
            try:
               with open(outMergedFileFullPath, 'w') as fout:
                  append_files(filenames, fout, debug, timeReadWrite)
               fout.close()
	       break
            except Exception, e:
               log.warning("Error writing file {0}: {1}, waiting for 30secs".format(outMergedFileFullPath,e))
               n_retries+=1
               time.sleep(30)

         if(n_retries == max_retries):
            log.error("Could not write file {0}!: {0}".format(outMergedFileFullPath))
            msg = "Could not write file {0}!: %s" % (outMergedFileFullPath)
            raise RuntimeError, msg
   
      elif (fileNameString[2] == "streamHLTRates" or fileNameString[2] == "streamL1Rates"):
         msg = "jsonMerger %s " % (outMergedFileFullPath)
         goodFiles = 0
         for nfile in range(0, len(filenames)):
            if (os.path.exists(filenames[nfile]) and (not os.path.isdir(filenames[nfile])) and os.path.getsize(filenames[nfile]) > 0):
               msg = msg + filenames[nfile] + " "
               goodFiles = goodFiles + 1
         if(float(debug) > 20): log.info("running {0}".format(msg))
         if(goodFiles > 0):
            os.system(msg)
         else:
            open(outMergedFileFullPath, 'w').close()

      else:
         if (mergeType == "macro"):
            msg = "fastHadd add -j 7 -o %s " % (outMergedFileFullPath)
         else:
            msg = "fastHadd add -o %s " % (outMergedFileFullPath)
         goodFiles = 0
         for nfile in range(0, len(filenames)):
            if (os.path.exists(filenames[nfile]) and (not os.path.isdir(filenames[nfile])) and os.path.getsize(filenames[nfile]) > 0):
               msg = msg + filenames[nfile] + " "
               goodFiles = goodFiles + 1
         if(float(debug) > 20): log.info("running {0}".format(msg))
         if(goodFiles > 0):
            os.system(msg)
            try:
                fileSize = os.path.getsize(outMergedFileFullPath)
            except:
                pass
         else:
            open(outMergedFileFullPath, 'w').close()

   # input events in that file, all input events, file name, output events in that files, number of merged files
   # only the first three are important
   theMergedJSONfile = open(outMergedJSONFullPath, 'w')
   theMergedJSONfile.write(json.dumps({'data': (infoEoLS[0], eventsO, errorCode, outMergedFile, fileSize, checkSum, infoEoLS[1], infoEoLS[2], infoEoLS[3], transferDest)}))
   theMergedJSONfile.close()
   #os.chmod(outMergedJSONFullPath, 0666)

   # remove already merged files, if wished
   if(doRemoveFiles == "True"):
      for nfile in range(0, len(files)):
         if(float(debug) >= 10): log.info("removing file: {0}".format(files[nfile]))
   	 inputFileToRemove = os.path.join(inputDataFolder, inpSubFolder, files[nfile])
         if (os.path.exists(inputFileToRemove) and (not os.path.isdir(inputFileToRemove))):
   	    os.remove(inputFileToRemove)
      for nfile in range(0, len(filesJSON)):
         if(float(debug) >= 10): log.info("removing filesJSON: {0}".format(filesJSON[nfile]))
   	 inputFileToRemove = filesJSON[nfile]
         if (os.path.exists(inputFileToRemove) and (not os.path.isdir(inputFileToRemove))):
   	    os.remove(inputFileToRemove)
      if mergeType == "mini":
         try:
            # Removing BoLS file, the last step
            BoLSFileName = fileNameString[0] + "_" + fileNameString[1] + "_" + fileNameString[2] + "_BoLS.jsn"
            BoLSFileNameFullPath = os.path.join(inputJsonFolder, BoLSFileName)
            if os.path.exists(BoLSFileNameFullPath):
	       os.remove(BoLSFileNameFullPath)
         except Exception, e:
            log.warning("Error deleting BoLS file {0}: {1}".format(BoLSFileNameFullPath,e))

   # Last thing to do is to move the data and json files to its final location "merged/runXXXXXX/stream/open/../."
   outMergedFileFullPathStable = os.path.join(outputMergedFolder, outSubFolder, outMergedFile)
   outMergedJSONFullPathStable = os.path.join(outputMergedFolder, outSubFolder, outMergedJSON)

   if (mergeType == "macro" and ("DQM" in fileNameString[2])):
      outMergedFileFullPathStable = os.path.join(outputDQMMergedFolder, outSubFolder, "open", outMergedFile)
      outMergedJSONFullPathStable = os.path.join(outputDQMMergedFolder, outSubFolder, "open", outMergedJSON)

   if (mergeType == "macro" and (("EcalCalibration" in fileNameString[2]) or ("EcalNFS" in fileNameString[2]))):
      outMergedFileFullPathStable = os.path.join(outputECALMergedFolder, outSubFolder, "open", outMergedFile)
      outMergedJSONFullPathStable = os.path.join(outputECALMergedFolder, outSubFolder, "open", outMergedJSON)

   checksum_status = True
   # checkSum checking
   if(doCheckSum == "True" and fileNameString[2] != "streamError" and specialStreams == False and infoEoLS[0] != 0 and fileSize < max_size_checksum):
      adler32c=1
      with open(outMergedFileFullPath, 'r') as fsrc:
         length=16*1024
         while 1:
            buf = fsrc.read(length)
            if not buf:
               break
            adler32c=zlib.adler32(buf,adler32c)

      adler32c = adler32c & 0xffffffff
      if(adler32c != checkSum):
         log.error("BIG PROBLEM, checkSum failed != outMergedFileFullPath: {0} --> {1}/{2}".format(outMergedFileFullPath,adler32c,checkSum))
         outMergedFileFullPathStable = os.path.join(outputMergedFolder, outSubFolder, "bad", outMergedFile)
         outMergedJSONFullPathStable = os.path.join(outputMergedFolder, outSubFolder, "bad", outMergedJSON)
         checksum_status = False

   if(checksum_status == True and infoEoLS[0] != 0):
      if(fileNameString[2] != "streamError" and specialStreams == False and fileSize != os.path.getsize(outMergedFileFullPath)):
         log.error("BIG PROBLEM, fileSize != outMergedFileFullPath: {0} --> {1}/{2}".format(outMergedFileFullPath,fileSize,os.path.getsize(outMergedFileFullPath)))
         outMergedFileFullPathStable = os.path.join(outputMergedFolder, outSubFolder, "bad", outMergedFile)
         outMergedJSONFullPathStable = os.path.join(outputMergedFolder, outSubFolder, "bad", outMergedJSON)
         checksum_status = False

      elif(mergeType == "macro" and fileSize > max_size):
         log.error("BIG PROBLEM, fileSize is too large!: {0} --> {1}".format(outMergedFileFullPath,fileSize))
         outMergedFileFullPathStable = os.path.join(outputMergedFolder, outSubFolder, "recovery", outMergedFile)
         outMergedJSONFullPathStable = os.path.join(outputMergedFolder, outSubFolder, "recovery", outMergedJSON)
         checksum_status = False

   if(infoEoLS[0] != 0):
      shutil.move(outMergedFileFullPath,outMergedFileFullPathStable)
   shutil.move(outMergedJSONFullPath,outMergedJSONFullPathStable)

   if (mergeType == "macro" and ("DQM" in fileNameString[2]) and checksum_status == True):
      outMergedFileFullPathStableFinal = os.path.join(outputDQMMergedFolder, outSubFolder, outMergedFile)
      outMergedJSONFullPathStableFinal = os.path.join(outputDQMMergedFolder, outSubFolder, outMergedJSON)
      if(infoEoLS[0] != 0):
         shutil.move(outMergedFileFullPathStable,outMergedFileFullPathStableFinal)
      shutil.move(outMergedJSONFullPathStable,outMergedJSONFullPathStableFinal)

   # monitor the merger by inserting record into elastic search database:
   if not (esServerUrl=='' or esIndexName==''):
      ls=fileNameString[1][2:]
      stream=fileNameString[2][6:]
      runnumber=fileNameString[0][3:]
      id=outMergedJSON.replace(".jsn","")
      mergeMonitorData = [ infoEoLS[0], eventsO, errorCode, outMergedFile, fileSize, infoEoLS[1], infoEoLS[2], time.time(), ls, stream, id]
      elasticMonitor(mergeMonitorData, runnumber, mergeType, esServerUrl, esIndexName, 5, debug)

   endMergingTime = time.time() 
   if(float(debug) > 5): log.info("Time for read/write({0}): {1:.3f}/{2:.3f}".format(outMergedJSONFullPath,timeReadWrite[0],timeReadWrite[1]))
   if(float(debug) > 0): log.info("Time for merging({0}): {1:.3f}".format(outMergedJSONFullPath,endMergingTime-initMergingTime))

 except Exception,e:
   log.error("mergeFilesA failed {0} - {1}".format(outMergedJSON,e))

"""
merging option C: merging unmerged files to same file for different BUs without locking the merged file 
"""
def mergeFilesC(inpSubFolder, outSubFolder, outputMergedFolder, outputSMMergedFolder, outputECALMergedFolder, doCheckSum, outMergedFile, outMergedJSON, inputDataFolder, infoEoLS, eventsO, files, checkSum, fileSize, filesJSON, errorCode, transferDest, mergeType, doRemoveFiles, outputEndName, esServerUrl, esIndexName, debug):
 try:
   if(float(debug) >= 10): log.info("mergeFiles: {0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}, {9}, {10}".format(outputMergedFolder, outputSMMergedFolder, outMergedFile, outMergedJSON, inputDataFolder, infoEoLS, eventsO, files, checkSum, fileSize, filesJSON, errorCode))

   # we will merge file at the BU level only!
   outMergedFileFullPath = os.path.join(outputSMMergedFolder, outSubFolder, "open", outMergedFile)
   outMergedJSONFullPath = os.path.join(outputMergedFolder,   outSubFolder, "open", outMergedJSON)
   if(float(debug) >= 10): log.info('outMergedFileFullPath: {0}'.format(outMergedFileFullPath))

   timeReadWrite = [0, 0]
   initMergingTime = time.time()
   if(float(debug) > 0): log.info("Start merge of {0}".format(outMergedJSONFullPath))

   if os.path.exists(outMergedJSONFullPath):
      os.remove(outMergedJSONFullPath)

   inputJsonFolder = os.path.dirname(filesJSON[0])
   fileNameString = filesJSON[0].replace(inputJsonFolder,"").replace("/","").split('_')

   lockName = fileNameString[0] + "_" + fileNameString[1] + "_" + fileNameString[2] + "_" + "StorageManager" + ".lock"
   lockNameFullPath = os.path.join(outputSMMergedFolder, outSubFolder, "open", lockName)

   iniName = fileNameString[0] + "_ls0000_" + fileNameString[2] + "_" + outputEndName + ".ini"
   if mergeType == "macro":
      iniName = "open/" + fileNameString[0] + "_ls0000_" + fileNameString[2] + "_" + "StorageManager" + ".ini"
   iniNameFullPath = os.path.join(outputSMMergedFolder, outSubFolder, iniName)
   if mergeType == "mini":
      maxSizeMergedFile = 50 * 1024 * 1024 * 1024
      if os.path.exists(iniNameFullPath):
         outLockedFileSize = 0
	 if(os.path.exists(lockNameFullPath)):
	    outLockedFileSize = os.path.getsize(lockNameFullPath)
         if(float(debug) > 5): log.info("Making lock file if needed({0}-{1}-{2}) {3}".format(os.path.exists(outMergedFileFullPath), outLockedFileSize, eventsO, outMergedJSONFullPath))
         if (not os.path.exists(outMergedFileFullPath)):
            time.sleep(random.random()*0.3)
         if (not os.path.exists(outMergedFileFullPath)):

            # file is generated, but do not fill it
            try:
               fd = os.open(outMergedFileFullPath, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
               fout = os.fdopen(fd, "w")
               fcntl.flock(fout, fcntl.LOCK_EX)
               fout.truncate(maxSizeMergedFile)
               fout.seek(0)
               #filenameIni = [iniNameFullPath]
               #append_files(filenameIni, fout, debug, timeReadWrite)
               if(float(debug) > 5): log.info("outMergedFile {0} being generated".format(outMergedFileFullPath))
               fcntl.flock(fout, fcntl.LOCK_UN)
               fout.close()
            except Exception,e:
               log.warning("cmsActualMergingFilesC dat file exists {0} - {1}".format(outMergedFileFullPath,e))

            checkSumIni=1
	    n_retries=0
	    while n_retries < max_retries:
               try:

                  checkSumIni=1
                  with open(iniNameFullPath, 'r') as fsrc:
                     length=16*1024
      	             while 1:
   	                buf = fsrc.read(length)
                  	if not buf:
            	           break
            	        checkSumIni=zlib.adler32(buf,checkSumIni)

	          checkSumIni = checkSumIni & 0xffffffff

	          break
               except Exception, e:
                  log.warning("Error writing file {0}: {1}, waiting for 30secs".format(outMergedFileFullPath,e))
                  n_retries+=1
                  time.sleep(30)

            if(n_retries == max_retries):
               log.error("Could not write file {0}!: {0}".format(outMergedFileFullPath))
               msg = "Could not write file {0}!: %s" % (outMergedFileFullPath)
               raise RuntimeError, msg

            if (not os.path.exists(lockNameFullPath)):
               try:
                  fd = os.open(lockNameFullPath, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
                  filelock = os.fdopen(fd, "w")
                  fcntl.flock(filelock, fcntl.LOCK_EX)

                  if(float(debug) > 5): log.info("lockFile {0} being generated".format(lockNameFullPath))
                  filelock.write("%s=%d:%d" %(socket.gethostname(),os.path.getsize(iniNameFullPath),checkSumIni))

                  filelock.flush()
                  #os.fdatasync(filelock)
                  #os.chmod(lockNameFullPath, 0666)
                  fcntl.flock(filelock, fcntl.LOCK_UN)
                  filelock.close()
               except Exception,e:
                  log.warning("cmsActualMergingFilesC lock file exists {0} - {1}".format(lockNameFullPath,e))
      else:
         log.error("BIG PROBLEM, ini file not found!: {0}".format(iniNameFullPath))
	 msg = "BIG PROBLEM, ini file not found!: %s" % (iniNameFullPath)
	 raise RuntimeError, msg

      filenames = [inputDataFolder + "/" + inpSubFolder + "/" + word_in_list for word_in_list in files]

      if(float(debug) > 20): log.info("Will merge: {0}".format(filenames))

      sum = 0
      for nFile in range(0,len(filenames)):
         if os.path.exists(filenames[nFile]) and os.path.isfile(filenames[nFile]):
   	    sum = sum + os.path.getsize(filenames[nFile])

      # no point to add information and merge files is there are no output events
      if(eventsO != 0):
	 if(float(debug) > 5): log.info("Waiting to lock file {0}".format(outMergedJSONFullPath))
	 nCount = 0
	 lockFileExist = os.path.exists(lockNameFullPath)
	 while ((lockFileExist == False) or (lockFileExist == True and os.path.getsize(lockNameFullPath) == 0)):
            nCount = nCount + 1
            if(nCount%60 == 1): log.info("Waiting for the file to unlock: {0}".format(lockNameFullPath))
            time.sleep(1)
	    lockFileExist = os.path.exists(lockNameFullPath)
	    if(nCount == 180):
	       log.info("Not possible to unlock file after 3 minutes!!!: {0}".format(lockNameFullPath))
               return

	 if(float(debug) > 5): log.info("Locking file {0}".format(outMergedJSONFullPath))
	 with open(lockNameFullPath, 'r+w') as filelock:
            fcntl.flock(filelock, fcntl.LOCK_EX)
            lockFullString = filelock.readline().split(',')
            ini = 0
            try:
               ini = int(lockFullString[len(lockFullString)-1].split(':')[0].split('=')[1])
            except Exception,e:
               log.warning("lockFullString1 problem({0}): {1} - {2}".format(lockNameFullPath,lockFullString,e))
               time.sleep(1)
               filelock.seek(0)
               lockFullString = filelock.readline().split(',')
               try:
                  ini = int(lockFullString[len(lockFullString)-1].split(':')[0].split('=')[1])
               except Exception,e:
                  log.error("lockFullString2 problem({0}): {1} - {2}".format(lockNameFullPath,lockFullString,e))

	    filelock.write(",%s=%d:%d" %(socket.gethostname(),ini+sum,checkSum))
            filelock.flush()
            if(float(debug) > 5): log.info("Writing in lock file ({0}): {1}".format(lockNameFullPath,(ini+sum)))
            #os.fdatasync(filelock)
            fcntl.flock(filelock, fcntl.LOCK_UN)
	 filelock.close()
	 if(float(debug) > 5): log.info("Unlocking file {0} - {1}/{2}".format(outMergedJSONFullPath,ini,sum))

	 nDataCount = 0
	 dataFileExist = os.path.exists(outMergedFileFullPath)
	 while ((dataFileExist == False) or (dataFileExist == True and os.path.getsize(outMergedFileFullPath) == 0)):
            nDataCount = nDataCount + 1
            if(nDataCount%60 == 1): log.info("Waiting for the dat file to unlock: {0}".format(outMergedFileFullPath))
            time.sleep(1)
	    dataFileExist = os.path.exists(outMergedFileFullPath)
	    if(nDataCount == 180):
	       log.info("Not possible to unlock dat file after 3 minutes!!!: {0}".format(outMergedFileFullPath))
               return

         if(float(debug) > 5): log.info("Time after unlocking, before appending jsn({0}): {1:.3f}".format(outMergedJSONFullPath, time.time()-initMergingTime))

	 n_retries=0
	 while n_retries < max_retries:
            try:
               with open(outMergedFileFullPath, 'r+w') as fout:
                  fout.seek(ini)
                  append_files(filenames, fout, debug, timeReadWrite)
	       fout.close()
	       break
            except Exception, e:
               log.warning("Error writing file {0}: {1}, waiting for 30secs".format(outMergedFileFullPath,e))
               n_retries+=1
               time.sleep(30)

         if(n_retries == max_retries):
            log.error("Could not write file {0}!: {0}".format(outMergedFileFullPath))
            msg = "Could not write file {0}!: %s" % (outMergedFileFullPath)
            raise RuntimeError, msg

	 if(float(debug) > 1): log.info("Actual merging of {0} happened".format(outMergedJSONFullPath))

   if(mergeType == "macro" and os.path.exists(iniNameFullPath)):
      if(infoEoLS[0] != 0):
	 n_retries=0
	 while n_retries < max_retries:
            try:
               with open(outMergedFileFullPath, 'r+w') as fout:
        	  fout.seek(0)
        	  filenameIni = [iniNameFullPath]
        	  append_files(filenameIni, fout, debug, timeReadWrite)
               fout.close()
               break
            except Exception, e:
               log.warning("Error writing file {0}: {1}, waiting for 30secs".format(outMergedFileFullPath,e))
               n_retries+=1
               time.sleep(30)

	 if(n_retries == max_retries):
            log.error("Could not write file {0}!: {0}".format(outMergedFileFullPath))
            msg = "Could not write file {0}!: %s" % (outMergedFileFullPath)
            raise RuntimeError, msg

      fileSize = fileSize + os.path.getsize(iniNameFullPath)
      if eventsO == 0:
         fileSize = os.path.getsize(iniNameFullPath)

   elif(mergeType == "macro"):
      log.error("BIG PROBLEM, iniNameFullPath {0} does not exist".format(iniNameFullPath))

   # remove already merged files, if wished
   if(doRemoveFiles == "True"):
      if mergeType == "mini":
         for nfile in range(0, len(files)):
            if(float(debug) >= 10): log.info("removing file: {0}".format(files[nfile]))
   	    inputFileToRemove = os.path.join(inputDataFolder, inpSubFolder, files[nfile])
            if (os.path.exists(inputFileToRemove) and (not os.path.isdir(inputFileToRemove))):
   	       os.remove(inputFileToRemove)
      for nfile in range(0, len(filesJSON)):
         if(float(debug) >= 10): log.info("removing filesJSON: {0}".format(filesJSON[nfile]))
   	 inputFileToRemove = filesJSON[nfile]
         if (os.path.exists(inputFileToRemove) and (not os.path.isdir(inputFileToRemove))):
   	    os.remove(inputFileToRemove)
      if mergeType == "mini":
         try:
            # Removing BoLS file, the last step
            BoLSFileName = fileNameString[0] + "_" + fileNameString[1] + "_" + fileNameString[2] + "_BoLS.jsn"
            BoLSFileNameFullPath = os.path.join(inputJsonFolder, BoLSFileName)
            if os.path.exists(BoLSFileNameFullPath):
	       os.remove(BoLSFileNameFullPath)
         except Exception, e:
            log.warning("Error deleting BoLS file {0}: {1}".format(BoLSFileNameFullPath,e))

   totalSize = 0
   # Last thing to do is to move the data and json files to its final location "merged/runXXXXXX/stream/open/../."
   if mergeType == "macro":

      if not os.path.exists(lockNameFullPath):
         msg = "lock file %s does not exist!\n" % (lockNameFullPath)
	 raise RuntimeError,msg

      with open(lockNameFullPath, 'r+w') as filelock:
         lockFullString = filelock.readline().split(',')
         totalSize = int(lockFullString[len(lockFullString)-1].split(':')[0].split('=')[1])
      filelock.close()

      with open(outMergedFileFullPath, 'r+w') as fout:
         fout.truncate(fileSize)
      fout.close()
      
      checkSumFailed = False

      if(fileNameString[2] != "streamError" and fileSize != totalSize):
         checkSumFailed = True
         log.error("BIG PROBLEM, fileSize != outMergedFileFullPath: {0} --> {1}/{2}".format(outMergedFileFullPath,fileSize,totalSize))
   	 outMergedFileFullPathStable = os.path.join(outputSMMergedFolder, outSubFolder, "bad", outMergedFile)

	 # also want to move the lock file to the bad area
   	 lockNameFullPathStable = os.path.join(outputSMMergedFolder, outSubFolder, "bad", lockName)
         shutil.move(lockNameFullPath,lockNameFullPathStable)

      else:
   	 outMergedFileFullPathStable = os.path.join(outputSMMergedFolder, outSubFolder, outMergedFile)
         if(fileNameString[2] != "streamError"):
	    # expected checksum
            with open(lockNameFullPath, 'r+w') as filelock:
               lockFullString = filelock.readline().split(',')
	    checkSum = int(lockFullString[0].split(':')[1])
	    for nf in range(1, len(lockFullString)):
               fileSizeAux = int(lockFullString[nf].split(':')[0].split('=')[1])-int(lockFullString[nf-1].split(':')[0].split('=')[1])
               checkSumAux = int(lockFullString[nf].split(':')[1])
	       checkSum = zlibextras.adler32_combine(checkSum,checkSumAux,fileSizeAux)
               checkSum = checkSum & 0xffffffff

         if(doCheckSum == "True" and fileNameString[2] != "streamError"):
            # observed checksum
            adler32c=1
            with open(outMergedFileFullPath, 'r') as fsrc:
               length=16*1024
               while 1:
                  buf = fsrc.read(length)
                  if not buf:
                     break
                  adler32c=zlib.adler32(buf,adler32c)

	    adler32c = adler32c & 0xffffffff

            if(adler32c != checkSum):
	       checkSumFailed = True
               log.error("BIG PROBLEM, checkSum failed != outMergedFileFullPath: {0} --> {1}/{2}".format(outMergedFileFullPath,adler32c,checkSum))
               outMergedFileFullPathStable = os.path.join(outputSMMergedFolder, outSubFolder, "bad", outMergedFile)

	       # also want to move the lock file to the bad area
               lockNameFullPathStable = os.path.join(outputSMMergedFolder, outSubFolder, "bad", lockName)
               shutil.move(lockNameFullPath,lockNameFullPathStable)

	 if(doRemoveFiles == "True" and checkSumFailed == False):
            if (os.path.exists(lockNameFullPath) and (not os.path.isdir(lockNameFullPath))):
               os.remove(lockNameFullPath)

      if ((("EcalCalibration" in fileNameString[2]) or ("EcalNFS" in fileNameString[2])) and checkSumFailed == False):
         outMergedFileFullPathStable = os.path.join(outputECALMergedFolder, outSubFolder, outMergedFile)

      if(checkSumFailed == False and fileSize > max_size):
         log.error("BIG PROBLEM, fileSize is too large!: {0} --> {1}".format(outMergedFileFullPath,fileSize))
         outMergedFileFullPathStable = os.path.join(outputSMMergedFolder, outSubFolder, "recovery", outMergedFile)

      if(float(debug) >= 10): log.info("outMergedFileFullPath/outMergedFileFullPathStable: {0}, {1}".format(outMergedFileFullPath, outMergedFileFullPathStable))
      try:
         shutil.move(outMergedFileFullPath,outMergedFileFullPathStable)
      except Exception,e:
         log.error("cmsActualMergingFilesC crashed, trying again: {0}, {1} - {2}".format(outMergedFileFullPath,outMergedFileFullPathStable,e))
         try:
            shutil.move(outMergedFileFullPath,outMergedFileFullPathStable)
         except Exception,e:
            log.error("cmsActualMergingFilesC crashed again: {0}, {1} - {2}".format(outMergedFileFullPath,outMergedFileFullPathStable,e))
            return

   # input events in that file, all input events, file name, output events in that files, number of merged files
   # only the first three are important
   theMergedJSONfile = open(outMergedJSONFullPath, 'w')
   theMergedJSONfile.write(json.dumps({'data': (infoEoLS[0], eventsO, errorCode, outMergedFile, fileSize, checkSum, infoEoLS[1], infoEoLS[2], infoEoLS[3], transferDest)}))
   theMergedJSONfile.close()
   #os.chmod(outMergedJSONFullPath, 0666)

   if(mergeType == "macro" and fileNameString[2] != "streamError"):
      if(fileSize != totalSize or checkSumFailed == True):
         outMergedJSONFullPathStable = os.path.join(outputSMMergedFolder, outSubFolder, "bad", outMergedJSON)
      elif(fileSize > max_size):
         outMergedJSONFullPathStable = os.path.join(outputSMMergedFolder, outSubFolder, "recovery", outMergedJSON)
      else:
         outMergedJSONFullPathStable = os.path.join(outputSMMergedFolder, outSubFolder, outMergedJSON)
   else:
      outMergedJSONFullPathStable = os.path.join(outputMergedFolder, outSubFolder, outMergedJSON)

   if (mergeType == "macro" and (("EcalCalibration" in fileNameString[2]) or ("EcalNFS" in fileNameString[2]))):
      outMergedJSONFullPathStable = os.path.join(outputECALMergedFolder, outSubFolder, outMergedJSON)

   if(float(debug) > 5): log.info("Time before move of jsn({0}): {1:.3f}".format(outMergedJSONFullPath,time.time()-initMergingTime))
   shutil.move(outMergedJSONFullPath,outMergedJSONFullPathStable)
   if(float(debug) > 5): log.info("Time after move of jsn({0}): {1:.3f}".format(outMergedJSONFullPath,time.time()-initMergingTime))

   # monitor the merger by inserting record into elastic search database:
   if not (esServerUrl=='' or esIndexName==''):
      ls=fileNameString[1][2:]
      stream=fileNameString[2][6:]
      runnumber=fileNameString[0][3:]
      id=outMergedJSON.replace(".jsn","")
      mergeMonitorData = [ infoEoLS[0], eventsO, errorCode, outMergedFile, fileSize, infoEoLS[1], infoEoLS[2], time.time(), ls, stream, id]
      elasticMonitor(mergeMonitorData, runnumber, mergeType, esServerUrl, esIndexName, 5, debug)

   endMergingTime = time.time() 
   if(float(debug) > 5): log.info("Time for read/write({0}): {1:.3f}/{2:.3f}".format(outMergedJSONFullPath,timeReadWrite[0],timeReadWrite[1]))
   if(float(debug) > 0): log.info("Time for merging({0}): {1:.3f}".format(outMergedJSONFullPath,endMergingTime-initMergingTime))

 except Exception,e:
   log.error("mergeFilesC failed {0} - {1}".format(outMergedJSON,e))

#______________________________________________________________________________
def append_files(ifnames, ofile, debug, theTimeReadWrite):
    '''
    Appends the contents of files given by a list of input file names `ifname'
    to the given output file object `ofile'. Returns None.
    '''
    for ifname in ifnames:
        if (os.path.exists(ifname) and (not os.path.isdir(ifname))):
            with open(ifname) as ifile:
                #shutil.copyfileobj(ifile, ofile)
                copyfileobj(ifile, ofile, debug, theTimeReadWrite)
            ifile.close()
# append_files

#______________________________________________________________________________
def copyfileobj(fsrc, fdst, theDebug, theTimeReadWrite, length=16*1024):
   """copy data from file-like object fsrc to file-like object fdst"""
   iniTimeRead = 0
   iniTimeWrite = 0
   while 1:

      if(theDebug > 1): iniTimeRead = time.time()
      buf = fsrc.read(length)
      if(theDebug > 1): theTimeReadWrite[0] = theTimeReadWrite[0] + time.time()-iniTimeRead

      if not buf:
         break

      if(theDebug > 1): iniTimeWrite = time.time()
      fdst.write(buf)
      if(theDebug > 1): theTimeReadWrite[1] = theTimeReadWrite[1] + time.time()-iniTimeWrite
# copyfileobj
