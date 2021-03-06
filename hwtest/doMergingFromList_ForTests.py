#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, time, sys, getopt, fcntl
import shutil
import json, ast
import glob
import multiprocessing
from multiprocessing.pool import ThreadPool
import threading
import datetime
import fileinput

# program to merge (cat) files given a list

"""
Do actual merging
"""
def mergeFiles(outMergedFile, inputDataFolder, files, inputJsonFile):
   #print "mergeFiles:", outMergedFile, inputDataFolder, files, inputJsonFile
    
   initMergingTime = time.time()
   now = datetime.datetime.now()
   print now.strftime("%H:%M:%S"), ": Start merge of ", inputJsonFile

   if(debug >= 20): print "List of files to be merged: ",files

   ifnames = [os.path.join(inputDataFolder,f) for f in files]
   outMergedFileFullPath = outMergedFile
   maxSizeMergedFile = 50 * 1024 * 1024 * 1024

   if option == 0:
      if os.path.exists(outMergedFile):
         os.remove(outMergedFile)
      with open(outMergedFileFullPath, 'w') as ofile:
         append_files(ifnames, ofile)
   
   elif option == 1:
      with open(outMergedFileFullPath, 'a') as ofile:
         fcntl.flock(ofile, fcntl.LOCK_EX)
         append_files(ifnames, ofile)
         fcntl.flock(ofile, fcntl.LOCK_UN)
   
   elif option == 2:
      lockNameFullPath = outMergedFileFullPath.replace(".raw",".lock")
      if nonexistent_or_zero_size(outMergedFileFullPath):
         with open(outMergedFileFullPath, 'w') as ofile:
            fcntl.flock(ofile, fcntl.LOCK_EX)
            ofile.truncate(maxSizeMergedFile)
            ofile.seek(0)
            os.chmod(outMergedFileFullPath, 0666)

            with open(lockNameFullPath, 'w') as filelock:
               fcntl.flock(filelock, fcntl.LOCK_EX)
               filelock.write("%d" %(0))
               filelock.flush()
               os.chmod(lockNameFullPath, 0666)
               fcntl.flock(filelock, fcntl.LOCK_UN)

            fcntl.flock(ofile, fcntl.LOCK_UN)

      sum = 0
      for nFile in range(0,len(ifnames)):
         sum = sum + os.path.getsize(ifnames[nFile])

      while not os.path.exists(lockNameFullPath):
         if(float(debug) >= 0): log.info("Waiting for the file to exists: {0}".format(lockNameFullPath))
         time.sleep(1)

      with open(lockNameFullPath, 'r+w') as filelock:
         fcntl.flock(filelock, fcntl.LOCK_EX)
         lockFullString = filelock.readline().split(',')
         ini = int(lockFullString[len(lockFullString)-1])
         filelock.write(",%d" % (ini+sum))
         filelock.flush()
         fcntl.flock(filelock, fcntl.LOCK_UN)

      with open(outMergedFileFullPath, 'r+w') as ofile:
         ofile.seek(ini)
         append_files(ifnames, ofile)
   

   if(debug >= 20): print "List of files to be merged: ",ifnames

   # files being deleted
   if doRemoveFiles == "True":
      map(os.remove, ifnames)

   endMergingTime = time.time()
   now = datetime.datetime.now()
   if(debug >= 0): print now.strftime("%H:%M:%S"), ": Time for merging(%s): %f" % (inputJsonFile,endMergingTime-initMergingTime)

"""
Do loops
"""
def doTheMerging():
   filesDict = dict()
   BUsDict   = dict()
   nThreadsMax = 30
   while 1:
      thePool = ThreadPool(nThreadsMax)
      #print paths_to_watch
      inputMonFolders = glob.glob(paths_to_watch)
      if(float(debug) > 20): print "***************NEW LOOP***************"
      if(float(debug) > 20): print inputMonFolders
      for nf in range(0, len(inputMonFolders)):
         inputDataFolder = inputMonFolders[nf].replace("MON","DATA")
         if(float(debug) > 20): print "folders MON/DATA: %s - %s" % (inputDataFolder,inputMonFolders[nf])
         before = dict ([(f, None) for f in os.listdir (inputMonFolders[nf])])
         #if(float(debug) > 0): time.sleep (1)
         #if(float(debug) > 0): print "Begin folder iteration"
         after = dict ([(f, None) for f in os.listdir (inputMonFolders[nf])])	  
         afterString = [f for f in after]
         added = [f for f in after if not f in before]
         if(float(debug) > 20): print afterString
         removed = [f for f in before if not f in after]
         if added: 
            if(float(debug) > 0): print "Added: ", ", ".join (added)
         if removed: 
            if(float(debug) > 0): print "Removed: ", ", ".join (removed)

	 processs = []
         for i in range(0, len(afterString)):
	    if ".jsn" not in afterString[i]: continue
	    if "MERGED" in afterString[i]: continue
	    if "TEMP" in afterString[i]: continue
	    if(float(debug) > 0): print "FILE:", afterString[i]
	    inputJsonFile = os.path.join(inputMonFolders[nf], afterString[i])
	    if(float(debug) > 0): print "inputJsonFile:",inputJsonFile
            settings_textI = open(inputJsonFile, "r").read()
            #settings = json.loads(settings_textI)
            settings = ast.literal_eval(settings_textI)

            inputNameString = afterString[i].split('.')
            key = (inputNameString[1],inputNameString[2],inputNameString[3])

            # for options == 1/2, only one BU will be used
            passBUCut = False
            if option == 0:
               passBUCut = True
	    else:
	       theCurrentBU = int(inputNameString[4].split('BU')[1])
	       if(float(debug) > 10): print "The current BU/bu: ",theCurrentBU,bu
	       if bu == theCurrentBU:
	          passBUCut = True

            if passBUCut == False: continue

	    # remove the file to avoid issues
	    if doRemoveFiles == "True":
	       os.remove(inputJsonFile)
            else:
	       inputJsonRenameFile = inputJsonFile.replace(".jsn","_TEMP.jsn")
               shutil.move(inputJsonFile,inputJsonRenameFile)

            if key in filesDict.keys():
               fileList = filesDict[key][0]
	       for nfile in range(0, len(settings['filelist'])):
	          fileList.append(settings['filelist'][nfile])
	       filesDict[key].remove(filesDict[key][0])
	       filesDict.update({key:[fileList]})

	       nBUs = BUsDict[key][0] + 1
	       BUsDict[key].remove(BUsDict[key][0])
	       BUsDict.update({key:[nBUs]})

	    else:
	       filesDict.update({key:[settings['filelist']]})
	       BUsDict.update({key:[1]})

	    # merged files if number of read BUs >= number of expected BUs
	    if int(BUsDict[key][0]) >= int(expectedBUs):
	       outMergedFile = str(settings['outputName'][0])
               if(float(debug) > 0): print "outMergedFile:", outMergedFile
               process = multiprocessing.Process(target = mergeFiles, args = [outMergedFile, inputDataFolder, filesDict[key][0], inputJsonFile])
               process.start()

               #process = threading.Thread   (target = mergeFiles,args = (outMergedFile, inputDataFolder, filesDict[key][0], inputJsonFile))
               #process.start()

	       #thePool.apply_async(mergeFiles, [outMergedFile, inputDataFolder, filesDict[key][0], inputJsonFile])

         before = after
      thePool.close()
      thePool.join()

"""
Do recovering JSON files
"""
def doTheRecovering(paths_to_watch):
   inputDataFolders = glob.glob(paths_to_watch)
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
         if "_TEMP.jsn" in afterString[i]:

            inputNameString = afterString[i].replace("_TEMP.jsn",".jsn").split('.')
            # for options == 1/2, only one BU will be used
            passBUCut = False
            if option == 0:
               passBUCut = True
	    else:
	       theCurrentBU = int(inputNameString[4].split('BU')[1])
	       if(float(debug) > 10): print "The current BU/bu: ",theCurrentBU,bu
	       if bu == theCurrentBU:
	          passBUCut = True

            if passBUCut == False: continue

            inputJsonFile = os.path.join(inputDataFolder, afterString[i])
            inputJsonRenameFile = inputJsonFile.replace("_TEMP.jsn",".jsn")
            shutil.move(inputJsonFile,inputJsonRenameFile)


#______________________________________________________________________________
def append_files(ifnames, ofile):
    '''
    Appends contents of files given by a list of input file names ifname
    to the given output file object ofile. Returns None.
    '''
    for ifname in ifnames:
        with open(ifname) as ifile:
            shutil.copyfileobj(ifile, ofile)
# append_files


#______________________________________________________________________________
def nonexistent_or_zero_size(filename):
    nonexistent = not os.path.exists(filename)
    zero_size = (os.path.exists(filename) and os.path.getsize(filename) == 0)
    return nonexistent or zero_size
# exists_and_has_zero_size


"""
Main
"""
valid = ['paths_to_watch=', 'debug=', 'help', 'expectedBUs=', 'option=', 'bu=', 'doRemoveFiles=']

usage =  "Usage: listdir.py --paths_to_watch=<paths_to_watch>\n"
usage += "                  --expectedBUs=<1>\n"
usage += "                  --doRemoveFiles=<True>\n"
usage += "                  --option=<0>\n"
usage += "                  --bu=<-1>\n"
usage += "                  --debug=<0>\n"

try:
   opts, args = getopt.getopt(sys.argv[1:], "", valid)
except getopt.GetoptError, ex:
   print usage
   print str(ex)
   sys.exit(1)

paths_to_watch = "unmerged"
debug          = 0
expectedBUs    = 1
doRemoveFiles  = "True"
option         = 0
bu             = -1

for opt, arg in opts:
   if opt == "--help":
      print usage
      sys.exit(1)
   if opt == "--paths_to_watch":
      paths_to_watch = str(arg)
   if opt == "--debug":
      debug = int(arg)
   if opt == "--expectedBUs":
      expectedBUs = int(arg)
   if opt == "--doRemoveFiles":
      doRemoveFiles = str(arg)
   if opt == "--option":
      option = int(arg)
   if opt == "--bu":
      bu = int(arg)

if option == 0:
   bu = -1
else:
   expectedBUs = 1

doTheRecovering(paths_to_watch)
doTheMerging()
