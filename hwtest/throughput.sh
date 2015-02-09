source tools.sh
RUN=100
OUTPUT_BASE=/mnt/cmsfs/benchmark

#BANDWIDTH_IN_GB=64512
BANDWIDTH_IN_GB=$(du -sk $OUTPUT_BASE/mergerMacro/run${RUN} -B 1G |\
    awk '{print $1}')
echo "Volume (GB): $(quote "$BANDWIDTH_IN_GB")"
START=$(grep "writing ls 0" $LOGS_BASE/prod*run${RUN}*.log |\
            sed 's/^.*log://' | sort | head -1 | awk '{printf $1}')
echo "Start (hh:mm:ss): $(quote "$START")"
END=$(tail -n100 $LOGS_BASE/merge*run${RUN}*.out |\
            grep Time | sort | tail -n1 |\
            awk -F, '{print $1}')
echo "End (hh:mm:ss): $(quote "$END")"
./throughput.py $BANDWIDTH_IN_GB $START $END
