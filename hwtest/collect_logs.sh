#!/bin/bash
source tools.sh
NODES=$(parse_machine_list all_nodes.txt)
MASTER_BASE=/nfshome0/veverka/lib/python/merger
SLAVE_BASE=/hwtests/slave
OUTPUT_BASE=/nfshome0/veverka/daq/benchmark/logs
SUMMARY_FILE=README.txt

MAJOR_VERSION_NUMBER=2
MINOR_VERSION_NUMBER=0
NAME=logs_v${MAJOR_VERSION_NUMBER}.${MINOR_VERSION_NUMBER}
LOGS_BASE=/nfshome0/veverka/daq/benchmark/logs/$NAME
while [[ -d $LOGS_BASE ]]; do
    (( MINOR_VERSION_NUMBER++ ))
    NAME=logs_v${MAJOR_VERSION_NUMBER}.${MINOR_VERSION_NUMBER}
    LOGS_BASE=/nfshome0/veverka/daq/benchmark/logs/$NAME
done

#______________________________________________________________________________
mkdir $LOGS_BASE

## Copy code
rsync -aW --exclude='.git' $MASTER_BASE $LOGS_BASE
#rm -rf $(find $LOGS_BASE -type d -name '.git')

#______________________________________________________________________________
## Copy the logs from each node
for NODE in $NODES; do
    echo $NODE
    DESTINATION_DIR=$LOGS_BASE
    LOGS_MASK="\$(find $SLAVE_BASE -name '*.log')"
    COMMAND=$(cat <<EOF
        mkdir -p $DESTINATION_DIR; \
        cp $LOGS_MASK $DESTINATION_DIR;
EOF
    )
    echo_and_ssh $NODE "$COMMAND"
    OUT_MASK="\$(find $SLAVE_BASE -name '*.out')"
    COMMAND=$(cat <<EOF
        mkdir -p $DESTINATION_DIR; \
        cp $OUT_MASK $DESTINATION_DIR;
EOF
    )
    echo_and_ssh $NODE "$COMMAND"
done

#______________________________________________________________________________
# Make list of files in the relevant folders
pushd $OUTPUT_BASE
for DIR in merger*; do
    pushd $DIR
    for RUN in run*; do
        ls -ll $RUN >& $LOGS_BASE/${DIR}_${RUN}_list.dat &
        ls -ll $RUN/open >& $LOGS_BASE/${DIR}_${RUN}_open_list.dat &
    done
    popd
done

popd
## Wait for all the ls commands to finish
wait

## Start a summary entry
echo "  * v${MAJOR_VERSION_NUMBER}.${MINOR_VERSION_NUMBER} " >> $SUMMARY_FILE
vim $SUMMARY_FILE
## Check the integrity of the files
echo "    $(source check_integrity.sh)" | tee -a $SUMMARY_FILE
## Estimate the expected performance
echo "    $(./estimate_expected.py)" | tee -a $SUMMARY_FILE
## Estimate the actual performance
echo "    $(source throughput.sh)" | tee -a $SUMMARY_FILE

# git tag netapp$(echo $NAME | sed 's/logs//')
# git log | head -n 6 > /lustre/$NAME/README

