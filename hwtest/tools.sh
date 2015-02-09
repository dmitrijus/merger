#______________________________________________________________________________
function node_name {
    ## Echo the name of the node given it's index
    echo server$1
} # node_name


#______________________________________________________________________________
function count_args {
    echo $@ | wc -w
} # count_args


#______________________________________________________________________________
function parse_machine_list {
    ## sed removes Bash/Python-style comments starting with `#'
    ## awk makes sure to ignore white space around the node name
    echo "$(sed 's/#.*$//' $1 | awk '{print $1}')"
} ## parse_machine_list


#______________________________________________________________________________
function echo_and_ssh {
    NODE=$1
    COMMAND="$2"
    LAUNCH_IN_THE_BACKGROUND=${3:-0}
    echo "+++ $NODE"
    ## Format the command for printing, add more line breaks.
    FORMATTED_COMMAND="$(echo $COMMAND |\
                         tr ';' '\n' |\
                         sed -e 's/ -/ \\\n    -/g' -e 's/ >/ \\\n    >/g' |\
                         sed -e 's/^/    /g')"
    if [[ $LAUNCH_IN_THE_BACKGROUND == "1" ]]; then
        echo "$FORMATTED_COMMAND &"
        ssh $NODE "$COMMAND" &
    else
        echo "$FORMATTED_COMMAND"
        ssh $NODE "$COMMAND"
    fi
}  ## echo_and_ssh


#______________________________________________________________________________
function echo_and_wassh {
    NODES="$1"
    COMMAND="$2"
    echo "$COMMAND"
    wassh "$NODES" "$COMMAND"
}  ## echo_and_wassh


#______________________________________________________________________________
function kill_mergers {
    EXIT_STATUS=0
    PROCESS_IDS=$(ps awwx |\
                  grep "dataFlowMergerInLine" |\
                  egrep -v "grep|bash" |\
                  awk '{print $1}')
    if [[ -z "$PROCESS_IDS" ]]; then
        echo "kill $PROCESS_IDS"
        kill $PROCESS_IDS
        EXIT_STATUS=$?
    fi
    return $EXIT_STATUS
}

#______________________________________________________________________________
function kill_producers {
    PROCESS_IDS=$(ps awwx |\
                  egrep "manageStreams.py" |\
                  egrep -v "grep|bash" |\
                  awk '{print $1}')
    if [[ -z "$PROCESS_IDS" ]]; then
        echo "kill $PROCESS_IDS"
        kill $PROCESS_IDS
        EXIT_STATUS=$?
    fi
    return $?
}

#-------------------------------------------------------------------------------
function wassh_list {
    FNAME=${1?all_nodes.txt}
    echo $(echo $(parse_machine_list $FNAME) | tr ' ' ',')
}

#-------------------------------------------------------------------------------
function quote {
    echo "\`"${@}"'"
} ## quote


#______________________________________________________________________________
function echo_and_wait {
    # jobs
    echo "+++ Waiting for all machines to finish ..."
    wait
}
