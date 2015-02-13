#!/usr/bin/env python
# -*- coding: utf-8 -*-

from configobj import ConfigObj
from makeFiles import createFiles

import os, sys
from optparse import OptionParser
import multiprocessing
import time,datetime
import random
import math
import json

start_time = datetime.datetime.now()

#______________________________________________________________________________
def main():
    parser = make_option_parser()

    options, args = parser.parse_args()

    if len(args) != 0:
        parser.error("You specified an invalid option - please use -h to review the allowed options")
    
    if (options.configFile == None):
        parser.error('Please specify the configuration file using the -c/--config option')

    theBUId = 10
    if (options.BUId != None):
       theBUId = options.BUId

    theTotalBUs = 1
    if (options.totalBUs != None):
       theTotalBUs = options.totalBUs

    thePath = ""
    if (options.Path != None):
       thePath = options.Path

    theInputPath = "dummy"
    if (options.inputPath != None):
       theInputPath = options.inputPath

    if not os.path.exists(theInputPath):
       msg = "BIG PROBLEM, file does not exists!: %s" % str(theInputPath)
       raise RuntimeError, msg

    lumi_length_mean = 1.
    if (options.lumi_length_mean != None):
       lumi_length_mean = float(options.lumi_length_mean)
    
    lumi_length_sigma = 0.001
    if (options.lumi_length_sigma != None):
       lumi_length_sigma = float(options.lumi_length_sigma)

    params = configureStreams(options.configFile)
    filesNb = int(params['Streams']['number'])
    lumiSections = int(params['Streams']['ls'])
    runNumber = int(params['Streams']['runnumber'])

    contentInputFile = []
    for i in range(filesNb):
        sizePerFile = int(params['Streams']['size' + str(i)])
        fileName = "inputFile_" + str(int(sizePerFile)) + "MB.dat"
        fullFileName = os.path.join(theInputPath, fileName)
        if not os.path.exists(fullFileName):
           msg = "BIG PROBLEM, file does not exists!: %s" % str(fullFileName)
           raise RuntimeError, msg

        #contentInputFile.append(fullFileName)
        with open(fullFileName, 'r') as theInputfile:
           contentInputFile.append(theInputfile.read())
        theInputfile.close()

    init(options, params)
    
    theNumberOfFilesPerLS = 10
    theNInput = 1000
    theNOutput = 10

    for ls in range(lumiSections):
       processs = []

       create_ls_files(options, params, ls, theNumberOfFilesPerLS, theNInput)

       now = datetime.datetime.now()

       print now.strftime("%H:%M:%S"), ": writing ls(%d)" % (ls)

       for i in range(filesNb):
          # Produce files every lumi_length_mean seconds with random flutuation
          sleep_time = seconds_to_sleep(5, lumi_length_mean, lumi_length_sigma)
          streamName =  params['Streams']['name' + str(i)]
          process = multiprocessing.Process(
              target = launch_file_making,
              args = [streamName, contentInputFile[i], ls, runNumber, theBUId,
                      thePath, theTotalBUs, sleep_time, 
		      theNumberOfFilesPerLS, theNInput, theNOutput]
              )
          process.start()

       print now.strftime("%H:%M:%S"), ": finished LS", ls, ", exiting..."
       time.sleep(lumi_length_mean)
    now = datetime.datetime.now()
    print now.strftime("%H:%M:%S"), ": finished, exiting..."
## main
    
#______________________________________________________________________________
def make_option_parser():
    parser = OptionParser(usage="usage: %prog [-h|--help] -c|--config config -b|--bu BUId | -p|--path Path | -i|--inputPath inputPath")

    parser.add_option("-c", "--config",
                      action="store", dest="configFile",
                      help="Configuration file storing the info related to the simulated streams of data. Absolute path is needed")

    parser.add_option("-b", "--bu",
                      action="store", dest="BUId",
                      help="BU number")

    parser.add_option("-p", "--path",
                      action="store", dest="Path",
                      help="Path to make")

    parser.add_option("-i", "--inputPath",
                      action="store", dest="inputPath",
                      help="Input path")

    parser.add_option("-m", "--lumi-length-mean",
                      action="store", dest="lumi_length_mean",
                      help="Mean length of lumi sections in seconds as a float")

    parser.add_option("-s", "--lumi-length-sigma",
                      action="store", dest="lumi_length_sigma",
                      help="Standard deviation of lumi section length " +
                           "distribution as a float")

    parser.add_option("-a", "--number_of_bus",
                      action="store", dest="totalBUs",
                      help="Number of BUs")

    return parser
## make_option_parser


#______________________________________________________________________________
def configureStreams(fileName):
    streamsConfigFile = fileName 

    try:
        if os.path.isfile(streamsConfigFile):
            config = ConfigObj(streamsConfigFile)
        else:
            print "Configuration file not found: {0}!".format(streamsConfigFile)
            sys.exit(1)
    except IOError, e:
        print "Unable to open configuration file: {0}!".format(streamsConfigFile)
        sys.exit(1)
    
    return config

#______________________________________________________________________________
def seconds_to_sleep(ls, lumi_length_mean=20, lumi_length_sigma=0.001):
    mean_offset = ls * lumi_length_mean
    random_offset = random.gauss(mean_offset, lumi_length_sigma)
    ret = max(0., mean_offset)
    return ret
## seconds_to_sleep

#______________________________________________________________________________
def total_seconds(tdelta):
    '''
    Returns the total number of seconds of a datetime.timedelta object.
    '''
    return 3600 * 24 * tdelta.days + tdelta.seconds + 1e-6 * tdelta.microseconds
## total_seconds

#______________________________________________________________________________
def launch_file_making(streamName, contentInputFile, lumiSections, runNumber,
                       theBUId, thePath, theTotalBUs, sleep_time, 
		       theNumberOfFilesPerLS, theNInput, theNOutput):
    time.sleep(sleep_time)
    createFiles(streamName, contentInputFile, lumiSections, runNumber,
                theBUId, thePath, theTotalBUs, 0.0, 999, -1,
                theNumberOfFilesPerLS, theNInput, theNOutput)

## launch_file_making


#______________________________________________________________________________
def init(options, params):
    create_data_dir(options, params)
    create_mon_dir(options, params)
    create_ini_files(options, params)
## init

#______________________________________________________________________________
def create_ini_files(options, params):
    path_to_make = options.Path
    if path_to_make == None:
       path_to_make = ""
    RUNNumber = int(params['Streams']['runnumber'])
    filesNb = int(params['Streams']['number'])
    theBUNumber = options.BUId
    ## loop over streams
    for i in range(filesNb):
        streamName =  params['Streams']['name' + str(i)]
        fileIntNameFullPath = "%sunmergedDATA/run%d/run%d_ls0000_%s_BU%s.ini" % (path_to_make,RUNNumber,RUNNumber,streamName,theBUNumber)
        with open(fileIntNameFullPath, 'w') as thefile:
           thefile.write('0' * 10)
           thefile.write("\n")
## create_ini_files

#______________________________________________________________________________
def create_ls_files(options, params, ls, numberOfFilesPerLS, nInput):
    path_to_make = options.Path
    if path_to_make == None:
       path_to_make = ""
    RUNNumber = int(params['Streams']['runnumber'])
    filesNb = int(params['Streams']['number'])
    theTotalBUs = 1
    if (options.totalBUs != None):
       theTotalBUs = options.totalBUs

    fileLSNameFullPath = "%sunmergedMON/run%d/run%d_ls%d_EoLS.jsn" % (path_to_make,RUNNumber,RUNNumber,ls)
    try:
       with open(fileLSNameFullPath, 'w') as theFileLSName:
    	  theFileLSName.write(json.dumps({'data': (nInput*int(numberOfFilesPerLS), int(numberOfFilesPerLS)*int(theTotalBUs), nInput*int(numberOfFilesPerLS)*int(theTotalBUs))}))
    except OSError, e:
       print "Looks like the file " + fileLSNameFullPath + " has just been created by someone else..."
## create_ls_files

#______________________________________________________________________________
def create_data_dir(options, params):
    path_to_make = options.Path
    if path_to_make == None:
       path_to_make = ""
    RUNNumber = int(params['Streams']['runnumber'])
    myDir = "%sunmergedDATA/run%d" % (path_to_make, RUNNumber)
    if not os.path.exists(myDir):
        try:
           os.makedirs(myDir)
        except OSError, e:
           print "Looks like the directory " + myDir + " has just been created by someone else..."
## create_data_dir

#______________________________________________________________________________
def create_mon_dir(options, params):
    path_to_make = options.Path
    if path_to_make == None:
       path_to_make = ""
    RUNNumber = int(params['Streams']['runnumber'])
    myDir = "%sunmergedMON/run%d" % (path_to_make, RUNNumber)
    if not os.path.exists(myDir):
        try:
           os.makedirs(myDir)
        except OSError, e:
           print "Looks like the directory " + myDir + " has just been created by someone else..."
## create_mon_dir


#______________________________________________________________________________
if __name__ == '__main__':
    main()
