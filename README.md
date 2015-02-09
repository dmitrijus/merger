# Merger Test Recipe
This describes how to run a simple test of the merger. It is currently setup
for a single machine only. For Python versioning reasons this is only confirmed to work on CMSSW_7_0_0 and up.

In order to test monitoring please edit config files and put in the details of the server URL and ES index:
dataFlowMergerMini.conf
dataFlowMergerMacro.conf

## Login

    ## Login to LXPLUS
    ##+ Tested on lxplus0097.cern.ch, dtmit14.cern.ch.
    ssh lxplus.cern.ch
    bash

## Configure

Create a new temporary folder. We will put everything related to the test in
this folder.

    TEST_BASE=$(mktemp -d -p /tmp/$(whoami))

Define other directories used in the test. These can be customized.

    ## Will contain the merger code
    MERGER_BASE=$TEST_BASE/merger
    ## Will contain the inputs for the generation of the unmerged data
    FROZEN_BASE=$TEST_BASE/data/frozen
    ## Will contain unmerged data used as mini-merger inputs
    UNMERGED_BASE=$TEST_BASE/data/input
    ## Will contain mini-merger outputs used as macro-merger outputs
    MERGED1_BASE=$TEST_BASE/data/mergeBU_TEST
    ## Will contain macro-merger output
    MERGED2_BASE=$TEST_BASE/data/mergeMacro_TEST

## Setup
Get the code from github.com. The https method should always work but you
may not have write access to the remote origin. You may need a Github account
with your ssh key uploaded for the ssh method to work.

    ## The https method
    git clone https://github.com/cmsdaq/merger $MERGER_BASE
    ## The ssh method
    # git clone git@github.com:cmsdaq/merger.git $MERGER_BASE

Update the config files.

    ## Update the mini-merger config
    cat > $MERGER_BASE/dataFlowMergerMini.conf <<END_OF_HERE_DOC
    [Input]
    dataPath = "$UNMERGED_BASE/unmergedDATA/run300"
    eolPath  = "$UNMERGED_BASE/unmergedMON"

    [Output]
    dataPath      = "$MERGED1_BASE"
    smPath        = "$MERGED2_BASE"
    dqmPath       = "$MERGED2_BASE"
    ecalPath      = "$MERGED2_BASE"

    [Misc]
    mergeType     = "mini"
    streamType    = "0"
    deleteFiles   = "True"
    debugLevel    = "1"
    logConfigFile = "$MERGER_BASE/logFormat.conf"
    mergeOption   = "optionC"
    esServerUrl   = ""
    esIndexName   = ""
    numberOfShards = "1"
    numberOfReplicas = "0"
    END_OF_HERE_DOC

    ## Update the macro-merger config
    cat > $MERGER_BASE/dataFlowMergerMacro.conf <<END_OF_HERE_DOC
    [Input]
    dataPath = "$MERGED1_BASE/run300"
    eolPath  = "$MERGED1_BASE"

    [Output]
    dataPath      = "$MERGED2_BASE"
    smPath        = "$MERGED2_BASE"
    dqmPath       = "$MERGED2_BASE"
    ecalPath      = "$MERGED2_BASE"

    [Misc]
    mergeType     = "macro"
    streamType    = "0"
    deleteFiles   = "True"
    debugLevel    = "1"
    logConfigFile = "$MERGER_BASE/logFormat.conf"
    mergeOption   = "optionC"
    esServerUrl   = ""
    esIndexName   = ""
    numberOfShards = "1"
    numberOfReplicas = "0"
    END_OF_HERE_DOC


Update the hard-coded paths of config and log files in the merger code
so that the code works in your custom location.
Some of the absolute paths to the config files may not be necessary if
you launch the scripts from the directory containing the code
but are useful so that you can launch the scripts from any location.

    OLD=/opt/merger/dataFlowMerger.conf
    NEW=$MERGER_BASE/dataFlowMergerMini.conf
    sed -i "s|$OLD|$NEW|" $MERGER_BASE/Logging.py

    OLD=/var/log/merger.log
    NEW=$MERGER_BASE/merger.log
    sed -i "s|$OLD|$NEW|" $MERGER_BASE/logFormat.conf

    OLD=dataFlowMergerMini.conf
    NEW=$MERGER_BASE/dataFlowMergerMini.conf
    sed -i "s|$OLD|$NEW|" $MERGER_BASE/dataFlowMiniMergerInLine

    OLD=dataFlowMergerMacro.conf
    NEW=$MERGER_BASE/dataFlowMergerMacro.conf
    sed -i "s|$OLD|$NEW|" $MERGER_BASE/dataFlowMacroMergerInLine

## Run

    ## Create the input files for the mini-merger input generation
    $MERGER_BASE/hwtest/makeInputFiles.py -p $FROZEN_BASE

    ## Generate the unmerged data used as mini-merger inputs. Creates directories
    ##+ $UNMERGED_BASE/unmergedDATA and $UNMERGED_BASE/unmergedMON.
    ##+ Mind the trailing "/" in `-p "$UNMERGED_BASE/"'.
    $MERGER_BASE/hwtest/manageStreams.py \
        --config $MERGER_BASE/hwtest/mergeConfigTest \
        --bu 30 \
        -i $FROZEN_BASE \
        -p "$UNMERGED_BASE/"

    ## Run the mini-merger
    ##+ Hit Ctrl-C to kill it after it finished merging all 15 files
    $MERGER_BASE/dataFlowMiniMergerInLine

    ## Run the macro-merger
    ##+ Hit Ctrl-C to kill it after it finished merging all 15 files
    $MERGER_BASE/dataFlowMacroMergerInLine

## Clean Up

    cd && rm -rf $TEST_BASE
