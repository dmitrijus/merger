source tools.sh
source env.sh
VERBOSE=${1:-0}
RUN=200

#BANDWIDTH_IN_GB=64512
BANDWIDTH_IN_GB=$(du -sk $OUTPUT_BASE/mergerMacro/run${RUN} -B 1G |\
    awk '{print $1}')
START=$(grep "writing ls 0" $LOGS_BASE/prod*run${RUN}*.log |\
            sed 's/^.*log://' | sort | head -1 | awk '{printf $1}')
END=$(tail -n100 $LOGS_BASE/merge*run${RUN}*.out |\
            grep Time | sort | tail -n1 |\
            awk -F, '{print $1}')
if [[ "$VERBOSE" == 1 ]]; then
    echo "Volume (GB): $(quote "$BANDWIDTH_IN_GB")"
    echo "Start (hh:mm:ss): $(quote "$START")"
    echo "End (hh:mm:ss): $(quote "$END")"
fi

./throughput.py $BANDWIDTH_IN_GB $START $END
