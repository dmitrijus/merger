#!/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

_base_path = '/nfshome0/veverka/lib/python/merger'
_verbosity_level = 0

#_______________________________________________________________________________
def main():
    lumi_length_mean    = get_lumi_length_mean()
    number_of_producers = get_number_of_producers()
    number_of_files_per_ls = 12   # NumberOfFilesPerLS in makeFiles.py
    total_file_size_in_mb = 80.   # for all streams
    number_of_ls = 2              # ls in run100.cfg

    bandwidth_per_ls_in_gb = (number_of_producers *
                              number_of_files_per_ls *
                              total_file_size_in_mb) / 1024.

    print "Max expected throughput: %.0f GB / %.0f s = %.2f GB/s" % (
        bandwidth_per_ls_in_gb * number_of_ls,
        lumi_length_mean * number_of_ls,
        bandwidth_per_ls_in_gb / lumi_length_mean
        )
    return None
# main

#_______________________________________________________________________________
def get_lumi_length_mean():
    '''
    Returns the value of the LUMI_LENGTH_MEAN in launch.sh
    '''
    subdir = 'hwtest'
    basename = 'launch.sh'
    variabe_name = 'LUMI_LENGTH_MEAN'
    path = os.path.join(_base_path, subdir, basename)
    try:
        source = open(path)
        for line in source:
            if variabe_name in line:
                value = line.split('=')[1]
                break
    except:
        print "Unexpected error when opening `%s':" %path, sys.exc_info()[0]
        source.close()
        raise
    if _verbosity_level > 0:
        print variabe_name, '=', value.strip()
    return float(value)
# get_lumi_length_mean


#_______________________________________________________________________________
def get_number_of_producers():
    '''
    Returns the number of uncommented lines in listProducers.txt
    '''
    subdir = 'hwtest'
    basename = 'listProducers.txt'
    path = path = os.path.join(_base_path, subdir, basename)
    count = 0
    try:
        source = open(path)
        for line in source:
            if line.strip()[0] != '#':
                count += 1
    except:
        print "Unexpected error when opening `%s':" %path, sys.exc_info()[0]
        raise
        source.close()
    if _verbosity_level > 0:
        print 'number of producers:', count
    return count
# get_number_of_producers

#_______________________________________________________________________________
if __name__ == '__main__':
    main()
