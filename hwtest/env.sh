LIST_PRODUCERS=listProducers.txt
#LIST_MERGERS=listMergers.txt
LIST_MERGERS=$LIST_PRODUCERS
ALL_NODES=all_nodes.txt
USER=$(whoami)

LUMI_LENGTH_MEAN=5
LUMI_LENGTH_SIGMA=1.0

## Top-level directory for the test management and control
MASTER_BASE="$(dirname $PWD)" ## assumes you are in $MASTER_BASE/hwtest
## Top level directory for the producer and merger scripts used during the test
SLAVE_BASE=/hwtests/$USER/slave
## Folder for the producer inputs
#FROZEN_BASE=/home/cern/frozen # HDD
FROZEN_BASE=/fff/ramdisk/hwtest/frozen # RAM disk
## Top-level directory for the producer outputs / merger inputs
INPUT_BASE=/fff/output/hwtest/$USER/inputs # local HDD
## Top-level directory for the merger outputs
OUTPUT_BASE=/store/lustre/benchmark/$USER

RUN=200
OPTION=optionC
MACRO_MERGER_NODE=mrg-c2f12-25-01
