TODO:
* Stress tests

TODONE:
* Remount lustre with -o flock on server02 - talk to Maria and Kees
  (busy because of a root process)
* Add other hosts
* Scale up

RESULTS
  * v0.11
    LUMI_LENGTH_MEAN=8, LUMI_LENGTH_SIGMA=4, ls=50, NumberOfFilesPerLS = 10
    Average throughput: 1960 GB / 412 s = 4.76 GB/s
    (2.38 GB/s stream A, 2.38 GB/s others)
  * v1.00, LUMI_LENGTH_MEAN=7, NumberOfFilesPerLS = 14
    Average throughput: 1913 GB / 358 s = 5.34 GB/s
    (2.67 GB/s stream A, 2.67 GB/s others)
  * v1.01, LUMI_LENGTH_MEAN=6.5
    Average throughput: 1913 GB / 336 s = 5.69 GB/s
    (2.85 GB/s stream A, 2.85 GB/s others)
  * v1.02, LUMI_LENGTH_MEAN=6, LUMI_LENGTH_SIGMA=3
    Average throughput: 1911 GB / 315 s = 6.07 GB/s
    (3.03 GB/s stream A, 3.03 GB/s others)
  * v1.03, LUMI_LENGTH_MEAN=5.5
    Average throughput: 1910 GB / 381 s = 5.01 GB/s
    (2.51 GB/s stream A, 2.51 GB/s others)
  * v1.04, LUMI_LENGTH_MEAN=6
    Average throughput: 1914 GB / 312 s = 6.13 GB/s
    (3.07 GB/s stream A, 3.07 GB/s others)
  * v1.05, iosize = 4*1024*1024
    Average throughput: 1914 GB / 314 s = 6.10 GB/s
    (3.05 GB/s stream A, 3.05 GB/s others)
  * v1.06, iosize = 16 * 1024 (default), randomized production
    Average throughput: 1910 GB / 311 s = 6.14 GB/s
    (3.07 GB/s stream A, 3.07 GB/s others)
  * v1.07, LUMI_LENGTH_MEAN=5.9
    Average throughput: 1914 GB / 308 s = 6.21 GB/s
    (3.11 GB/s stream A, 3.11 GB/s others)
  * v1.08, INPUT_BASE=/ramdisk/data
    Average throughput: 1908 GB / 308 s = 6.19 GB/s
    (3.10 GB/s stream A, 3.10 GB/s others)
  * v1.09, # nodes = 6 LUMI_LENGTH_MEAN=5.0571
    Average throughput: 1637 GB / 320 s = 5.12 GB/s 
    (2.56 GB/s stream A, 2.56 GB/s others)
  * v1.10, # nodes = 5 (server{03,07,08,16,17}) LUMI_LENGTH_MEAN=4.2143
    Average throughput: 1360 GB / 226 s = 6.02 GB/s
    (3.01 GB/s stream A, 3.01 GB/s others)
  * v1.11
    Total / closed / opened files: 500 / 493 (98 %) / 7 (2 %)
    Average throughput: 1364 GB / 261 s = 5.23 GB/s
    (2.61 GB/s stream A, 2.61 GB/s others)
  * v1.12
    Average throughput: 1365 GB / 275 s = 4.96 GB/s
    (2.48 GB/s stream A, 2.48 GB/s others)
  * v1.13, # nodes = 5 (server{06,07,08,16,17}, use 6 instead of 3)
    Total / closed / opened files: 500 / 493 (98 %) / 7 (2 %)
    Average throughput: 1363 GB / 237 s = 5.75 GB/s
    (2.88 GB/s stream A, 2.88 GB/s others)
  * v1.14
    Total / closed / opened files: 500 / 495 (99 %) / 5 (1 %)
    Average throughput: 1360 GB / 254 s = 5.35 GB/s
    (2.68 GB/s stream A, 2.68 GB/s others)
  * v1.15
    Total / closed / opened files: 500 / 491 (98 %) / 9 (2 %)
    Average throughput: 1361 GB / 251 s = 5.42 GB/s
    (2.71 GB/s stream A, 2.71 GB/s others)
  * v1.16, 3 clients (server{06,07,08}), ls = "100", LUMI_LENGTH_MEAN=2.5285
    Total / closed / opened files: 1000 / 361 (36 %) / 639 (64 %)
    Average throughput: 1411 GB / 408 s = 3.45 GB/s
    (3.14 GB/s stream A, 3.14 GB/s others)
  * v1.17
    Total / closed / opened files: 1000 / 770 (77 %) / 230 (23 %)
    Average throughput: 1450 GB / 468 s = 3.10 GB/s (1.55 GB/s stream A, 1.55 GB/s others)
  * v1.18
    Total / closed / opened files: 1000 / 319 (31 %) / 681 (69 %)
    Max theoretical throughput: 1641 GB / 253 s = 6.49 GB/s
    Average throughput: 1450 GB / 511 s = 2.84 GB/s (1.42 GB/s stream A, 1.42 GB/s others)
  * v1.19 Reproduce the best result, use all 7 nodes, NumberOfFilesPerLS = 14,
    ls="50", LUMI_LENGTH_MEAN=5.9
    Total / closed / opened files: 500 / 498 (99 %) / 2 (1 %)
    Max expected throughput: 1914 GB / 295 s = 6.49 GB/s
    Average throughput: 1914 GB / 322 s = 5.94 GB/s
    There have seemed to be a couple of seconds of very low activity at the end,
    which could have lowered the average significantly.
  * v1.20 One more repeat of the best setting so far
    Total / closed / opened files: 500 / 497 (99 %) / 3 (1 %)
    Max expected throughput: 1914 GB / 295 s = 6.49 GB/s
    Average throughput: 1913 GB / 321 s = 5.96 GB/s
  * v1.21 remove server02 and server03 (being worked on)
    Total / closed / opened files: 500 / 499 (99 %) / 1 (1 %)
    Max expected throughput: 1367 GB / 295 s = 4.63 GB/s
    Average throughput: 1366 GB / 318 s = 4.30 GB/s

  * v2.0 ls="2", added new machine server20
  
  * v2.3 added 3 new machines (server2{1,2,3})

  * v2.4 added 2 more machines (server2{4,5})
    Total / closed / opened files: 20 / 20 (100%) / 0 (0%)
    Max expected throughput: 98 GB / 12 s = 8.34 GB/s
    Average throughput: 99 GB / 52 s = 1.90 GB/s

  * v2.5 ls="50" NumberOfFilesPerLS=11
    Total / closed / opened files: 500 / 494 (98%) / 6 (2%)
    Average throughput: 1929 GB / 335 s = 5.76 GB/s

  * v2.6 LUMI_LENGTH_SIGMA=3.0
    Total / closed / opened files: 500 / 497 (99%) / 3 (1%)
    Max expected throughput: 1934 GB / 295 s = 6.55 GB/s
    Average throughput: 1931 GB / 334 s = 5.78 GB/s

  * v2.7
    Repeat the previous measurement with no change to see how reproducible
    it is.
    Total / closed / opened files: 500 / 496 (99%) / 4 (1%)
    Max expected throughput: 1934 GB / 295 s = 6.55 GB/s
    Average throughput: 1933 GB / 335 s = 5.77 GB/s

  * v2.8 LUMI_LENGTH_MEAN=5
    Total / closed / opened files: 500 / 491 (98%) / 9 (2%)
    Max expected throughput: 1934 GB / 250 s = 7.73 GB/s
    Average throughput: 1928 GB / 394 s = 4.89 GB/s

  * v2.9 LUMI_LENGTH_MEAN=6
    Total / closed / opened files: 500 / 493 (98%) / 7 (2%)
    Max expected throughput: 1934 GB / 250 s = 7.73 GB/s
    Average throughput: 1930 GB / 343 s = 5.63 GB/s

  * v2.10 same as previous to check reproducibility (?)
    Total / closed / opened files: 500 / 493 (98%) / 7 (2%)
    LUMI_LENGTH_MEAN = 5.9
number of producers: 1
Max expected throughput: 215 GB / 295 s = 0.73 GB/s
    Average throughput: 1930 GB / 343 s = 5.63 GB/s
  * v1.0 
    Total / closed / opened files: 100 / 100 (100%) / 0 (0%)
    
    
  * v1.1 ls=50

    Total / closed / opened files: 500 / 500 (100%) / 0 (0%)
    LUMI_LENGTH_MEAN = 5.0
    number of producers: 7
    Max expected throughput: 219 GB / 50 s = 4.38 GB/s
    Average throughput: 1094 GB / 347 s = 3.15 GB/s

  * v1.2 ls=100 
    Total / closed / opened files: 646 / 99 (15%) / 547 (85%)
    LUMI_LENGTH_MEAN = 3.0
    number of producers: 7
    Max expected throughput: 219 GB / 30 s = 7.29 GB/s
    
  * v1.3 same as v1.2 to check for a crash, have .log and .out file for mergers
    Total / closed / opened files: 1000 / 1000 (100%) / 0 (0%)
    LUMI_LENGTH_MEAN = 3.0
    number of producers: 7
    Max expected throughput: 219 GB / 30 s = 7.29 GB/s
    Average throughput: 2188 GB / 544 s = 4.02 GB/s
  * v1.4 ls=50, limit number of processes spawned by the producer
    Total / closed / opened files: 500 / 486 (97%) / 14 (3%)
    LUMI_LENGTH_MEAN = 3.0
    number of producers: 7
    Max expected throughput: 219 GB / 30 s = 7.29 GB/s
    Volume (GB): `1089'
    Average throughput: 1089 GB / 290 s = 3.76 GB/s
  * v1.5 more lumis
    Total / closed / opened files: 1000 / 969 (96%) / 31 (4%)
    Max expected throughput: 1094 GB / 150 s = 7.29 GB/s
    Average throughput: 2179 GB / 390 s = 5.59 GB/s
  * v1.6  ls=5000
    Total / closed / opened files: 50000 / 1043 (2%) / 48957 (98%)
    Max expected throughput: 1094 GB / 150 s = 7.29 GB/s
    Average throughput: 64512 GB / 15164 s = 4.25 GB/s
    
  * v1.7 ls=10, updated merger code to use pool.join and have checksum switch
    (checksum is on by default), updated file sizes 
    to have more realistic BU inputs
    Total / closed / opened files: 100 / 100 (100%) / 0 (0%)
    Average throughput: 66 GB / 85 s = 0.78 GB/s

  * v1.8 ls=50 
    Total / closed / opened files: 499 / 499 (100%) / 0 (0%)
    Max expected throughput: 1094 GB / 150 s = 7.29 GB/s
    Average throughput: 329 GB / 428 s = 0.77 GB/s

  * v1.9 turned check summing off
    Total / closed / opened files: 500 / 500 (100%) / 0 (0%)
    Max expected throughput: 1094 GB / 150 s = 7.29 GB/s
    Average throughput: 329 GB / 154 s = 2.14 GB/s

  * v1.10 LS=1.5s
    Total / closed / opened files: 500 / 500 (100%) / 0 (0%)
    Max expected throughput: 1094 GB / 75 s = 14.58 GB/s
    Average throughput: 329 GB / 89 s = 3.70 GB/s

  * v1.11 LS=1s
    Total / closed / opened files: 500 / 500 (100%) / 0 (0%)
    Max expected throughput: 1094 GB / 50 s = 21.88 GB/s
    Average throughput: 329 GB / 84 s = 3.92 GB/s

  * v1.12 LS=0.75s
    Total / closed / opened files: 500 / 500 (100%) / 0 (0%)
    Max expected throughput: 1094 GB / 38 s = 29.17 GB/s
    Average throughput: 329 GB / 85 s = 3.87 GB/s

  * v1.13 #LS = 100
    Total / closed / opened files: 1000 / 1000 (100%) / 0 (0%)
    Max expected throughput: 1094 GB / 38 s = 29.17 GB/s
    Average throughput: 657 GB / 143 s = 4.59 GB/s

  * v1.14 #LS = 200
    Total / closed / opened files: 2000 / 2000 (100%) / 0 (0%)
    Max expected throughput: 1094 GB / 38 s = 29.17 GB/s
    Average throughput: 1313 GB / 270 s = 4.86 GB/s

  * v1.15 #LS = 500
    Total / closed / opened files: 5000 / 5000 (100%) / 0 (0%)
    Max expected throughput: 1094 GB / 38 s = 29.17 GB/s
    Average throughput: 3282 GB / 998 s = 3.29 GB/s

  * v1.16 max threads = 20
    Total / closed / opened files: 5000 / 5000 (100%) / 0 (0%)
    Max expected throughput: 1094 GB / 38 s = 29.17 GB/s
    Average throughput: 3282 GB / 1179 s = 2.78 GB/s

  * v1.17 #LS = 5000, max threads = 30
    Total / closed / opened files: 50000 / 50000 (100%) / 0 (0%)
    Max expected throughput: 1094 GB / 38 s = 29.17 GB/s
    Average throughput: 32814 GB / 20705 s = 1.58 GB/s

  * v2.0 First test with large setup

  * v2.1 First test with many BUs including merging

  * v2.2 Investigating the merged file size
    Average throughput: 64512 GB / 8 s = 8064.00 GB/s

  * v2.3 NumberOfFilesPerLS = 1, #BUs: 23

  * v2.4 Another merging test with 55 BUs
    All streams seem to have worked except for the stream A

  * v2.5 Dummy 
    
  * v2.6 Test with bu-c2f16-[31-43]-01
    
  * v2.7 Fixed clean up bug, parallelized clean up and producer launch, test
    with 3 BUs only

  * v2.8 Tried with 46 BUs

  * v2.9 Customizing work areas for different users
    Max expected throughput: 11 GB / 10 s = 1.12 GB/s
    Average throughput: 9 GB / 18 s = 0.50 GB/s

  * v2.10 Added more BUs
    Total / closed / opened files: 20 / 20 (100%) / 0 (0%)
    Max expected throughput: 38 GB / 10 s = 3.75 GB/s
    Average throughput: 29 GB / 10 s = 2.90 GB/s

  * v2.11 Refactored settings into env.sh
    Total / closed / opened files: 20 / 20 (100%) / 0 (0%)
    Max expected throughput: 28 GB / 10 s = 2.81 GB/s
    Average throughput: 29 GB / 9 s = 3.22 GB/s

