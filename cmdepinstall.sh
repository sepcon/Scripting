##########################################################################################################################################################
# * CAR MULTIMEDIA LOCAL TO SERVER
# * Simple thing to make life easier.
# * Trying to improve this script is appriciated - and not suppose that you must know shell script to do any improvements.
# * Let's learn how to use new languages to make you more intelligent
# *                                --------------------------------------------------------                                                    
# * [Usage]:
# * --> Run this script and follow the instructions printed out by the script. after that type cmlocal2server --help is the best way for usage
# * [ BRIEF ]: Using to interact with servers(target/lsim) using ssh, including:
# *        1. Copy files from local to server    
# *        2. Build and copy files from local to server
# *        3. Start a gdbserver session attach to running process
# *        4. Observe Asset Gerneration process, after AssetGen.cmd finished --> automatically pushes Asset.bin to server
# *        5. Binds file name(applications, so libs, asset.bin(s)...) specified in pkg_xxx.xml in nincg3/ai_xxx
# *        6. More info: please install this script in build environment then do the messages the script tells you
# *----------------------------------------------------------------------------------------------------------------------
# * [Version]:
# * 0.1 --> Initial features with support for product names completion
# * 0.2 --> Support start gdbserver attaching to running process that specified in pkg.xml files
# * 0.3 --> Support Observation for Asset Generation script to deploy Asset.bin file to server right after generationi process done!
# * 0.4 --> Using Python to index pkg.xml files instead of AWK for future funtions extending
# * 0.5 --> Collect the products specified with CUSTOMERPROJECT variable, this can be extended later by other variable liek architecture if needed
############################################################################################################################################################


#STARTDEPLOYSECTION <------ Do not permit to remove this line, search for it to know why

#!/bin/bash
## -- -- NOTE -- --
# CMDEP_N_ --> # name
# CMDEP_D_ --> # directory
# CMDEP_F_ --> # file
#------------------------------
## Error code definitions
 CMDEP_ERROR_OK=0
 CMDEP_ERROR_FILE_NOT_FOUND=1
 CMDEP_ERROR_CONNECTION_ERROR=2
 CMDEP_ERROR_REMOTE_COMMAND_ERROR=3
 CMDEP_ERROR_FILE_UNSUPPORTED=4
 CMDEP_ERROR_WRONG_ARGUMENT=5
#-----------------------------
## Global variable definitions
 CMDEP_V_TOOL_FOR_INDEXING=python
 CMDEP_N_BRANCH_IDENTIFIER=${_SWROOT//\//_}
 CMDEP_D_INSTALLATION_DIR=~/.local/bin
 CMDEP_D_DATA_DIR=~/.local/dat/cmdep
 CMDEP_F_JUST4LAUGH=${CMDEP_D_DATA_DIR}/just4laugh
 CMDEP_F_CMLOCAL2SERVER_SCRIPT=$CMDEP_D_INSTALLATION_DIR/cmlocal2server.sh
 CMDEP_F_PYTHON_INDEXER_SCRIPT=${CMDEP_D_DATA_DIR}/pythonindexer.py
 CMDEP_F_DEPLOY_INFORMATION_FILE=$CMDEP_D_DATA_DIR/l2s${CMDEP_N_BRANCH_IDENTIFIER}_DeployInfomation.dat
 CMDEP_F_PRODUCT_LIST_FILE=$CMDEP_D_DATA_DIR/l2s${CMDEP_N_BRANCH_IDENTIFIER}_ProductList.dat
 CMDEP_F_LAST_MODES_FILE=$CMDEP_D_DATA_DIR/l2s${CMDEP_N_BRANCH_IDENTIFIER}_LastModes.dat
 CMDEP_F_CUSTOM_DEPLOY_INFO_FILE=$CMDEP_D_DATA_DIR/l2s${CMDEP_N_BRANCH_IDENTIFIER}_CustomPkgFiles.dat
 CMDEP_F_DEFAULT_PKG_LIST_FILE=$CMDEP_D_DATA_DIR/l2s_DefaultPkgFiles.dat
 CMDEP_F_SETTINGS_FILE=$CMDEP_D_DATA_DIR/l2s_serversSettings.dat
 CMDEP_F_SUPPORTED_TYPES_FILE=$CMDEP_D_DATA_DIR/l2s_supportedTypes.dat
 CMDEP_F_RUNNING_OBSERVATION_PROCESS=~/.local/dat/running_proc
 CMDEP_F_GDB_INSTALLATION_SCRIPT=${_SWNAVIROOT}/tools/prj_dbg/gdbserver_copy2target.sh
 CMDEP_D_DEBUGGER_ROOT_DIR=${_SWBUILDROOT}/generated/debugger
 CMDEP_N_GDBINIT=gdbinit
 CMDEP_N_RFS=';' #field separator --> dest=path/to/dest;source=dest/to/source --> useful for calling eval in bash, we can get both variables dest and source
 [[ -e $CMDEP_F_SUPPORTED_TYPES_FILE ]] && source $CMDEP_F_SUPPORTED_TYPES_FILE
#----------------------
## Printing variables
 CL_RED='\033[0;31m'
 CL_GREEN='\033[0;32m'
 CL_ORANGE='\033[0;33m'
 CL_PINK='\033[0;35m'
 CL_NONE='\033[0m' 
#----------------------
##TEMPORARY VALUES:
 CMDEP_V_COMP_PREVIOUS_COMPWORD=
 CMDEP_V_COMP_PREVIOUS_COMPREPLY=
## Function definitions
#

__just4Laugh()
{
    if [[ -e $CMDEP_F_JUST4LAUGH  ]]; then
      __redMsg "Con is very handsome, right"
      __msg "if you don't feel that, please type: ConIsNotHandsome"
    fi
}

ConIsNotHandsome()
{
    rm $CMDEP_F_JUST4LAUGH 2>/dev/null
    __redMsg "Thanks for your response, but I really hate you!!! :@"
}

__DEBUG()
{
    [ "$CMDEPDEBUG" == "on" ] && eval "$@"
}

__msg()
{
    echo -e "$@"
}

__redMsg()
{
    __msg "${CL_RED}$@$CL_NONE"
}

__dbgMsg()
{
    __DEBUG __redMsg "$@"
}

__errorMsg()
{
    [[ -v CMDEP_V_ERROR_COUNT ]] && (( CMDEP_V_ERROR_COUNT++ ))
    echo -e "${CL_RED}ERROR: ${@}${CL_NONE}" >/dev/stderr
}

__warningMsg()
{
    echo -e "${CL_ORANGE}WARNING: ${@}${CL_NONE}" >/dev/stderr
}

# highlight the stderr message with red color, error message will be read from stderr
__stdErrorMsg() 
{
    local line
    while read line; do
        echo -e "${CL_PINK}${line}$CL_NONE" >/dev/stderr
    done
}

__separatedRegion()
{
    [[ $CMDEPDEBUG == "on" ]] && return #Don't use this in debug mode that leads to lots of messy things in screen by below FOR-LOOP
    local cols=`tput cols`
    local length=0
    for param in $@; do
        (( length += ${#param} ))
    done
    numItems=0
    if [[ $length -gt 0 ]]; then (( numItems = cols / length )); fi
    for (( i = 0; i < numItems; ++i)); do printf "$@"; done
    printf '\n'
}

__ignErrRun()
{
    __DEBUG "[[ -z '$@' ]] && __msg __ignErrRun: empty arguments "
    eval "$@" 2>/dev/null
    return $?
}

__silientRun()
{
    __DEBUG "[[ -z '$@' ]] && __msg __silientRun: empty arguments"
    eval "$@" 2&>/dev/null
    return $?
}


## cmdep namespace
__cmdepStartErrorCounting()
{
    export CMDEP_V_ERROR_COUNT=0
}

__cmdepReportErrorCount() 
{
    [[ -v CMDEP_V_ERROR_COUNT && $CMDEP_V_ERROR_COUNT -gt 0 ]] &&  [[ $@ == *"--verbose"* ]] && __msg "INFO:\tNumber of errors $CMDEP_V_ERROR_COUNT"
    unset -v CMDEP_V_ERROR_COUNT
}

__cmdepExit()
{
    __cmdepReportErrorCount "$@"
    kill -SIGINT $$
}

__cmdepPrintBuildProductHelp()
{
    __msg "Others utilities: "
    __msg "    Several aliases are made to make build process more convinient: "
    __msg "    E.g: "
    __msg "        bldprd app<Tab><Tab> will get the completion for productList name (that specified in pkg...xml files)"
    __msg "        buildproduct app<Tab><Tab> can have completion for productList name also"
    __msg "    Details:"
     eval "$( awk ' !/^#|^[[:space:]]*$/ { print "alias bldprd" $1; print "alias bldprdsrc" $1; }' $CMDEP_F_SETTINGS_FILE )"
}
__cmdepPrintCommandsHelp() #option
{    
    __msg
    __msg "                                        CMLOCAL2SERVER                                                                "
    __msg "Copy/Revert list of binary files that specified in pkg_XXX_.xml files from local to server, or debug the application from remote serever"
    __msg "Make sure you are executing the command in build environment and execute the command '${CL_GREEN}source ~/.bashrc${CL_NONE}' to load the commands in case cmlocal2server command is not available after set_env.sh script is run"
    __msg
    __msg "    cmlocal2server [--mode=<debug|release>] [--server=<target|lsim>]  [--noreboot] [--build=<build|rebuild|noprecreate>]  PRODUCT1 PRODUCT2 ... PRODUCTN"
    __msg "        ---> : look up for AppXX name in configuration files and copy to server"
    __msg "    cmlocal2server --revert=[.backupExtension] [--noreboot] PRODUCT1 PRODUCT2 ... PRODUCTN" 
    __msg "        ---> : Revert products in list to backup version with .backupExtension(default = .ori)"
    __msg "    cmlocal2server [--observe=<path/to/generateAsset.cmd|off>] Asset.bin"
    __msg "        ---> : observe process of running script path/to/generateAsset.cmd to push Asset.bin to server. this is useful when you generate asset file on windows, Asset.bin is obligated"
    __msg "    cmlocal2server [--server=<target|lsim>] --debug application_XXX_out.out"
    __msg "        ---> : Debug the the binary on server, with run this script '${_SWNAVIROOT}/tools/prj_dbg/gdbserver_copy2target.sh' to install gdbserver if it's not been installed"
    __msg "    cmlocal2server --addconfig=PATH/TO/PACKAGE.XML"
    __msg "        ---> : Add configuration file, usually stored in ${_SWROOT}/ai_xxx/config/packages/"
    __msg "    cmlocal2server --newtype=fileExtension"
    __msg "        ---> : add new supported type of binaries e.g: 'reg, service...'"
    __msg "    cmlocal2server --uninstall "
    __msg "        ---> : remove all commands and indexed files"
    __msg "    cmlocal2server --changeSettings "
    __msg "        ---> : change the default values of modes and servers' address, a new instance of Vi editor will be launched for edit the file"
    __msg "    cmlocal2server [--server=<target|lsim>] --altsource=PATH/TO/LOCAL/BINARY --altdest=PATH/TO/SERVER/BINARY [--save]"
    __msg "        ---> : copy file from PATH/TO/LOCAL/BINARY to PATH/TO/SERVER/BINARY on [server] and use [--save] to remember these paths"
    __msg
    __msg
    __msg "Options details: "
    __msg "    PRODUCT1 PRODUCT2 PRODUCT3 ...: list of products want to copy to server, separated by space "
    __msg "    [--help]: Print the help, if specify --help=OPTION the comment for OPTION will be printed"
    __msg "    [--mode]: Build mode - posible value: <debug|release>"
    __msg "    [--server]: which server: <target|lsim>"
    __msg "    [--noreboot]: does not reboot the server after the job done"
    __msg "    [--revert=backupExtension]: revert the binary files/productList on server to original file with backupExtension, default is 'ori'"
    __msg "    [--reindex]: In case deploy information specified in pkg_xxx.xml is not specific(like apphmi_*.out), the indexing function will not be able to get correct app name to generate config. Then after build, you can reindex to get the correct app name"
    __msg "    [--addconfig]: add new ${_SWROOT}/ai_xxx/config/packages/pkg_xxx.xml for searching binaries"
    __msg "    [--uninstall]: remove all commands and indexed files"
    __msg "    [--build]: build binaries before copying to server <build|rebuild|noprecreate> - default = noprecreate"
    __msg "    [--altsource]: Give the path to file that you want to copy to server that it is not available in config file. Useful in case you want to test binary from other developers, this option must go with --altdest"
    __msg "    [--altdest]: Goes with --altsource to specify the path to file on server to copy alsource to"
    __msg "    [--save]: Goes with --altdest and --altsource to remember these 2 options that you can use for next times"
    __msg "    [--debug]: start gdbserver attaching to running App with default port is 2345, using different port with --port=PORTNUMBER"
    __msg "    [--port]: this option available only when --debug option is enable. specify the port of communication between gdb and gdbserver"
    __msg "    [--newtype]: add new types of files that want to be copied to server, current support types: '.so|.out|.bin'"
    __msg "    [--changeSettings]: option to enable changing the default values of modes and servers' address or adding new server information"
    __msg "    [--observe]: =off --> exit observation mode, =path/to/generateAsset.cmd --> observe the process of running path/to/generateAsset.cmd to push file to server"
    __msg
}


__cmdepErrorAndHelp() # $1-> help-option, ${@:2} -> message
{
    unset hlpopt
    [[ $1 != "#" ]] && local hlpopt="=$1"
    local message="${@:2}"
    __errorMsg "$message"
    __redMsg "Type: 'cmlocal2server --help=${hlpopt}' for usages"
    __cmdepExit
}
__cmdepHelp()
{
    local entry=$1
    if [[ -n $entry ]]; then
        __cmdepPrintCommandsHelp | grep "\-\-$entry" 2>/dev/null
        [[ $? == 1 ]] && __errorMsg "Unknown entry: $entry"
    else
        local help=`
        __cmdepPrintCommandsHelp
        __cmdepPrintBuildProductHelp`
        __msg "$help"| more
    fi
    __cmdepExit
}

__cmdepMakeEnvVarsAsStringLiteral()
{
    _SWNAVIROOT_O=$_SWNAVIROOT 
    _SWBUILDROOT_O=$_SWBUILDROOT 
    COMPILERENV_O=$COMPILERENV 
    MODE_O=$MODE 
    
    _SWNAVIROOT='${_SWNAVIROOT}'
    COMPILERENV='${COMPILERENV}' 
    MODE='${MODE}'
    _SWBUILDROOT='${_SWBUILDROOT}'
}
__cmdepUndoMakingEnvVarsAsStringLiteral()
{
    _SWNAVIROOT=$_SWNAVIROOT_O 
    COMPILERENV=$COMPILERENV_O 
    MODE=$MODE_O 
    _SWBUILDROOT=$_SWBUILDROOT_O
}

__cmdepAssertBuildEnv()
{
    if [ -z "${_SWBUILDROOT}" ]; then
        __cmdepErrorAndHelp "#" "make sure you are executing the command in build environment"
    fi
}

__cmdepWildcard2Regex() #inputString
{
    local regx=${@//\*/.\*}
    regx=${regx//../.}
    echo $regx
}

__cmdepRememberPkgFiles() # path/to/pkg.xml
{
    if [ -e $1 ]; then
        echo $1 >> $CMDEP_F_DEFAULT_PKG_LIST_FILE
    else
        __msg
        __cmdepErrorAndHelp "addconfig" "$newConfXml no such fil or directory"
    fi
}

# __cmdepAddNewSupportedType newtype
__cmdepAddNewSupportedType() # file_extension(i.e: out | bin | registry | service ...)
{
    if [[ $1 == "#" ]]; then
        __errorMsg "Please specify a type!"
    else
        CMDEP_V_SUPPORTED_TYPES="${CMDEP_V_SUPPORTED_TYPES}|\\.$1"
        echo "export CMDEP_V_SUPPORTED_TYPES=\"$CMDEP_V_SUPPORTED_TYPES\"" > $CMDEP_F_SUPPORTED_TYPES_FILE
        source $CMDEP_F_SUPPORTED_TYPES_FILE
        __msg "$1 was remembered as supported typed"
        __msg "Reindexing the configurations files"
        __cmdepIndexStoredPkgFiles --verbose
        __msg "DONE!!!"
    fi
}

__cmdepAddNewPkgFile() 
{
    export CMDEP_V_NOISY_INDEXING=1
    local newConfXml=$(realpath $1)
    __cmdepRememberPkgFiles $newConfXml
    __cmdepIndexPkgFiles $CMDEP_F_DEPLOY_INFORMATION_FILE $CMDEP_F_PRODUCT_LIST_FILE $newConfXml
    if [[ -e $CMDEP_F_CUSTOM_DEPLOY_INFO_FILE ]]; then 
          cat $CMDEP_F_CUSTOM_DEPLOY_INFO_FILE >> $CMDEP_F_DEPLOY_INFORMATION_FILE
          grep "[^/]*[$CMDEP_V_SUPPORTED_TYPES]$" $CMDEP_F_CUSTOM_DEPLOY_INFO_FILE -o >> $CMDEP_F_DEPLOY_INFORMATION_FILE
    fi
    
    unset -v CMDEP_V_NOISY_INDEXING
}

__cmdepGetExistingPkgFiles()
{
    local pkgFilesList=( $( __ignErrRun "cat $CMDEP_F_DEFAULT_PKG_LIST_FILE" ) )
    for f in ${pkgFilesList[@]}; do
        eval "realFile=$f"
        if [[ -e $realFile ]];
            then printf "$realFile "
        else
            __errorMsg "$f does not exist, please specify correct path by command: < cmlocal2server --addconfig=/path/to/pkg/file >"
        fi
    done
}

# collect the server's information from file CMDEP_F_SETTINGS_FILE
__cmdepGetServerInformation() #$1: ServerName(lsim|target|...)
{
     local server=$1
     if [[ -n $server ]] ; then
          local information=$( 
                awk -v server="$server" '
                     { 
                          if($1 == server){
                                print "serverName=" $1 ";serverIP=" $2 ";COMPILERENV=" $4 ";MODE=" $5
                                exit
                          }
                     }
                     ' $CMDEP_F_SETTINGS_FILE 
                )
     else
          local information=$(
                awk '
                     {
                          if(NF == 6 && $NF == "(*)") {
                                print "serverName=" $1 ";serverIP=" $2 ";COMPILERENV=" $4 ";MODE=" $5
                                exit
                          }
                     }
                     ' $CMDEP_F_SETTINGS_FILE
          )
     fi
     
     echo $information
}

__cmdepFormDeployInfoRecord()
{
    local SOURCE=$2 DEST=$1
    echo "dest=${DEST}${CMDEP_N_RFS}source=${SOURCE}"
}
__cmdepBuildProduct() # $1: buildmode $2: MODE $3: COMPILERENV productList
{
    local buildmode=""
    case $1 in
        build)
            buildmode="--buildmode=build"
            ;;
        rebuild)
            buildmode="--buildmode=rebuild"
            ;;
        noprecreate)
            buildmode="--buildmode=build --noprecreate --alldeps=none"
            ;;
        *)
            buildmode="--buildmode=build --noprecreate --alldeps=none"
            ;;
    esac
    shift
    local mode=$1
    shift
    local env=$1
    shift
    productList=`
        echo $@ | 
        awk '{
                gsub("[^[[:space:]]]*[\\\\._]bin", "")
                gsub("\\\\.out|\\\\.so|_stripped", "", $0); 
                for(i = 0; i < NF; ++i)
                {
                    if($i ~ /^lib.*$/)
                    {
                        $i = substr($i, 4)
                    }
                }
                printf($0 " ")
            }'
        `
    local buildCommnad="buildproduct --os=linux --env=$env --mode=$mode $buildmode --info --silent $productList "
    __msg "Excecute build command: "
    __msg "$buildCommnad"
    eval $buildCommnad
    return $?
}


__cmdepRemoteDebug() # 1.path/to/gdbinit 2.path/to/server/product 3.serverIP 4.port=2345
{
    local gdbinitPath=$1
    local product=$2
    local serverIP=$3
    local port=$4
    local remoteExec="ssh -t -t root@$serverIP"
    local debugCommand="
        pid=\$(pidof $product);
        if [[ -z \$pid ]]; then 
            echo -e \"${CL_RED}Error: the $product is not running, please reboot the server and try aggain${CL_NONE}\";
        else
            gdbserver :$port --attach \$pid;
        fi"
    if [[ $gdbinitPath != "#" && -e $gdbinitPath ]]; then 
        [[ -e ~/.${CMDEP_N_GDBINIT} ]] && mv ~/.${CMDEP_N_GDBINIT} ~/.${CMDEP_N_GDBINIT}.old 
        cp $gdbinitPath ~/.${CMDEP_N_GDBINIT}
    fi
    
    __msg "Debug information: "
    __msg "GDBINIT     :\t$gdbinitPath"
    __msg "APPLICATION:\t$product"
    __msg "SERVER      :\t$serverIP"
    __msg "PORT         :\t$port"
    
    $remoteExec "which gdbserver >/dev/null"
    local errorCode=$?
    if [[ $errorCode == 0 ]]; then
        $remoteExec $debugCommand
    elif [[ $errorCode != 255 ]]; then
        __msg "Install gdbserver to $serverIP"
        bash -c $CMDEP_F_GDB_INSTALLATION_SCRIPT
        if [[ $? == 0 ]]; then
            $remoteExec $debugCommand
        else
            __errorMsg "something wrong happened while install gdbserver to $serverIP"
        fi
    elif [[ $errorCode == 255 ]]; then
        __errorMsg "Please check your network connection to $serverIP"
    fi
}

#input: productname specified in cmlocal2server command
__cmdepGetMatchingDeployInfoRecords()
{
    productname=$1
    if [[ -n $productname ]]; then
        deployInfo=$(grep -i "$productname" "$CMDEP_F_DEPLOY_INFORMATION_FILE" 2>/dev/null )
        [[ -z $deployInfo ]] && deployInfo=$(grep -i $(__cmdepWildcard2Regex "$productname") "$CMDEP_F_DEPLOY_INFORMATION_FILE" 2>/dev/null )
        echo "$deployInfo"
    else 
        __dbgMsg "cant find $productname"
    fi
}         

__cmdepCreateAssetGenRunScript() #AssetGenScript.cmd.path
{
    # Generate Script for using to start file AssetGen.cmd on windows
    local assetGenScriptPath=$1
    ! [[ -e $assetGenScriptPath ]] && return $CMDEP_ERROR_FILE_NOT_FOUND
    local assetRunScriptPath=${assetGenScriptPath//'.cmd'/'.run.bat'}
    local assetGenScriptName=`basename $assetGenScriptPath`
    echo "
@echo off
echo Start the script: $assetGenScriptName
$assetGenScriptName && echo.  >> %0
echo Job done at: 
date /t && time /t 
    " > $assetRunScriptPath
    
    chmod a+x $assetRunScriptPath
    #return the script name as output
    echo $assetRunScriptPath 
}
__cmdepStopObservationMode() 
{ 
    ! [[ -e $CMDEP_F_RUNNING_OBSERVATION_PROCESS ]] && __msg "There's no observation daemon running!!!" && return $CMDEP_ERROR_FILE_NOT_FOUND
    
    local pid=`cat $CMDEP_F_RUNNING_OBSERVATION_PROCESS`
    if [[ -n $pid ]]; then 
        __ignErrRun kill -SIGTERM $pid
        while [[ -e /proc/$pid ]]; do
            sleep 0.5
        done
    else
        __msg "There's no observation daemon running!!!"
    fi
    
    rm $CMDEP_F_RUNNING_OBSERVATION_PROCESS 2>/dev/null
}

__cmdepStartObservationMode() #$1:observationfile $2:actionFunction
{
    ( #Start a sub-shell
        __cmdepStartObservationMode_prv_impl()
        {
            local observedFile=$1; [[ -z $observedFile ]] && return #for case of no input file
            local condition=$2
            local actionFunction=${@:3}
            local cmdGetTime="stat -c %Y"
            local timestampStart=`$cmdGetTime $observedFile 2>/dev/null`
            local timestampNow=
            local sigStop=0
            __dbgMsg $actionFunction
            # Notify that there is process running in backgound
            echo $BASHPID > $CMDEP_F_RUNNING_OBSERVATION_PROCESS 
            
            __cmdepStartObservationMode_prv_OnTerminated()
            {
                __ignErrRun rm $observedFile 
                __msg "Stopped observation on file $observedFile"
                exit
            }; trap __cmdepStartObservationMode_prv_OnTerminated SIGHUP SIGINT SIGTERM
            
            while true; do
                if [[ -e $observedFile ]]; then 
                    timestampNow=`$cmdGetTime $observedFile`
                    if [[ $timestampNow -gt $timestampStart ]]; then
                        timestampStart=$timestampNow
                        echo "Detected asset generation script has been done about 1 second ago!"
                        eval $condition && eval $actionFunction
                        
                    fi
                fi
                sleep 1
            done
        }
        __msg "Start Observation mode!!!"
        __msg "An observing daemon is running in the backgound, you can continue the shell with your current work"
        __msg "You can terminate this daemon by command: ${CL_GREEN}cmlocal2server --observe=off${CL_NONE}"
        __cmdepStartObservationMode_prv_impl $@ & #for detach the function from current terminal
    ) #end sub-shell
}

__cmdepObserveAssetBin() #observe productName
{
    local observe=$1
    local productName=(${@:2})
    
    if [[ $observe == "off" ]] ; then
        __cmdepStopObservationMode
    else
	  [[ -z ${productName[@]} ]] && __cmdepErrorAndHelp observe "Please specify the Asset file name (i.e: AppHmi_Master_Asset.bin)" 
        if [[ -n $productName ]]; then
            __cmdepCollectDeployInfo "false" ${productName[@]}
            local collectedDeployInfo=( ${retCDI_allDeployInfo[@]} )
            unset -v retCDI_allDeployInfo
            if [[ ${#collectedDeployInfo[@]} == 1 ]]; then
                __cmdepStopObservationMode
                local runScriptPath=`__cmdepCreateAssetGenRunScript $observe`
                if [[ $? == $CMDEP_ERROR_FILE_NOT_FOUND ]]; then
                    __errorMsg "file $observe does not exist"
                    return
                fi
                __warningMsg "Please remember to use `basename $runScriptPath` instead of `basename $observe` to generate asset"
                (
                    eval $collectedDeployInfo
                    local observedFile=${runScriptPath}
                    local condition="__cmdepIsNewFile"
                    local action="__cmdepDeploy $serverIP $COMPILERENV $MODE 'false' '$collectedDeployInfo'"
                    local assetLastModifiedTime=`stat -c %Y $source 2>/dev/null`
                    __cmdepIsNewFile() 
                    {
                        local modifiedTime=`stat -c %Y $source 2>/dev/null`
                        
                        __msg "Current Modified time: $modifiedTime"
                        __msg "Last Modified time: $assetLastModifiedTime"
                        
                        if [[ $modifiedTime -gt $assetLastModifiedTime ]]; then 
                            assetLastModifiedTime=$modifiedTime
                            __msg "File $source has recently been modified"
                            return 0
                        else 
                            __errorMsg "$runScriptPath finished with some errors occured!!"
                            return 1
                        fi
                    }
                    
                    __cmdepStartObservationMode $observedFile "$condition" "$action"
                )
                return 0 # For case of working
            fi
            __errorMsg "Cannot observe more than one file, please specify only one\nINFO:\tYou've just specified ${#collectedDeployInfo[@]} files: "
            __cmdepDisplayDeployInfo __redMsg "false" ${collectedDeployInfo[@]}
        else        
            __errorMsg "Please specify the Asset file name"
        fi
    fi
}


__clearAllGlobalVariables()
{
    unset -v MODE COMPILERENV altsource mode altdest server buildmode build addconfig noreboot revert save debug port newtype observe changeSettings revertBakExt
}


__cmdepl2sMain()
{
    __cmdepAssertBuildEnv
    __clearAllGlobalVariables # Making sure that all variables will be set below won't be available until they are really set
    __cmdepStartErrorCounting
    
    local productList=()
    local revertBakExt=.ori
    
    __cmdepl2sArgsCheck() #$1: arg
    {
        local arg=$1
        local argIsEmpty="[[ -z \$$arg ]]"
        if [[ -z $1 ]]; then
            __cmdepErrorAndHelp $1 "Please specify value for $1"
        fi
    }
    
    while [ "$1" != "" ]; do
        local arg=`echo $1 | cut -d= -f1`
        local value=`echo $1 | cut -d= -f2`
        [[ $value == $arg ]] && value=
        
        case $arg in
            -h | --help)
                __cmdepHelp $value
                ;;
            --altsource)
                local altsource=$value
                __cmdepl2sArgsCheck altsource
                ;;
            --altdest)
                local altdest=$value
                __cmdepl2sArgsCheck altdest
                ;;
            --mode)
                local mode=$value
                __cmdepl2sArgsCheck mode
                ;;
            --server)
                local server=$value
                __cmdepl2sArgsCheck server
                ;;
            --build)
                local buildmode=$value
                local build=1
                ;;
            --addconfig)
                local addconfig=$value
                __cmdepl2sArgsCheck addconfig
                __cmdepAddNewPkgFile $value
                __cmdepExit
                ;;
            --noreboot)
                local noreboot=true
                ;;
            --revert)
                local revert=true
                [[ -n $value ]] && revertBakExt=$value
                ;;
            --uninstall)
                __cmdepUninstall
                return
                ;;
            --reindex)
                __cmdepIndexStoredPkgFiles --verbose
                __cmdepExit
                ;;
            --save)
                local save=1
                ;;
            --debug)
                local debug=1
                ;;
            --port)
                local port=$value
                __cmdepl2sArgsCheck port
                ;;
            --newtype)
                local newtype=$value
                __cmdepl2sArgsCheck newtype
                ;;
            --observe)
                local observe=$value
                __cmdepl2sArgsCheck observe
                ;;
            --changeSettings)
                local changeSettings=1
                break
                ;;
            *)
                if [[ $arg == "-"* ]]; then
                    __cmdepErrorAndHelp "#" "Unknow argument $arg"
                    return
                fi;
                productList+=( "$arg" )
                ;;
        esac
        shift
    done

#     collecting server information -- > START
    local serverInformation=$(__cmdepGetServerInformation $server)
    if [[ -z $serverInformation ]]; then
          __cmdepErrorAndHelp "changeSettings" "Could not find information of $server, Please specify the correct server name or "
    fi
    
    local serverName serverIP COMPILERENV MODE 
    eval $serverInformation
    [[ -n $mode ]]  && MODE=$mode
    
#     collecting server information < -- END

    if [[ -v changeSettings ]]; then
        vi $CMDEP_F_SETTINGS_FILE
        __msg "settings have been changed succesfully!!"
        source $CMDEP_F_CMLOCAL2SERVER_SCRIPT
    elif [[ -n $newtype ]]; then
        __cmdepAddNewSupportedType $newtype
    elif [[ -v altsource || -v altdest ]]; then
        eval "local altsource=$altsource" #make sure that the symbol '~' will be evaluated as home directory
        eval "local altdest=$altdest"
        [[ -z $altdest ]] && __cmdepErrorAndHelp "altdest" "please specify --altdest as corresponding directory of $altsource on $server"
        [[ -z $altsource ]] && __cmdepErrorAndHelp "altsource" "please specify --altsource as corresponding directory of $altdest on $server"
        ! [[ -f $altsource ]] && __cmdepErrorAndHelp "altsource" "$altsource --> is not a file"
        local altDeployInfo="$(__cmdepFormDeployInfoRecord $altdest $altsource)"
        local altLocalProductName=`basename $altsource`
        if [[ $save == 1 ]]; then
            echo $altDeployInfo >> $CMDEP_F_DEPLOY_INFORMATION_FILE
            echo $altLocalProductName >> $CMDEP_F_PRODUCT_LIST_FILE
            ! [[ -e $CMDEP_F_CUSTOM_DEPLOY_INFO_FILE ]] && touch $CMDEP_F_CUSTOM_DEPLOY_INFO_FILE
            echo "<file dest=\"$altdest\" source=\"$altsource\"/>" >> $CMDEP_F_CUSTOM_DEPLOY_INFO_FILE
            grepResult=$(grep "$CMDEP_F_CUSTOM_DEPLOY_INFO_FILE" $CMDEP_F_DEFAULT_PKG_LIST_FILE 2>/dev/null)
        fi
        __dbgMsg "Deploying $altDeployInfo"
        __cmdepDeploy $serverIP $COMPILERENV $MODE "false" "$altDeployInfo"
    elif [[ -v debug ]]; then
        local deployInfo=$(__cmdepGetMatchingDeployInfoRecords $productList)
        if [[ -z $deployInfo ]]; then
            __errorMsg "Not found any entry for $productList in configuration"
        else
            eval "$deployInfo"
            [[ -z $port ]] && port=2345
            local gdbInitPath=${CMDEP_D_DEBUGGER_ROOT_DIR}/${COMPILERENV}/${CMDEP_N_GDBINIT}
            __cmdepRemoteDebug ${gdbInitPath} $dest $serverIP $port
        fi
    elif [[ -n $observe ]]; then
        __cmdepObserveAssetBin $observe ${productList[@]}
    else
        #     execute build command before copy binary to server
        if [[  -v build ]]; then 
            local buildsuccess=false
            [[ -z $buildmode ]] && buildmode=noprecreate
            __cmdepBuildProduct $buildmode $MODE $COMPILERENV ${productList[@]}  && buildsuccess=true
        fi
        [[ ! -v revert ]] && local revert=false
        [[ ! -v build || $buildsuccess == true ]] &&  __cmdepDeploy $serverIP $COMPILERENV $MODE $revert "${productList[@]}"
    fi
    __cmdepExit --verbose
}

__cmdepDisplayDeployInfo() # printFunction isRevert depinfo ...
{
    local info i=1 
    local printFunction=$1
    local revert=$2
    local deployInfo=${@:3}
    [[ -z $printFunction || -z $revert || -z $deployInfo ]] && return 
    [[ -z $cmdepgvIndentChar ]] && cmdepgvIndentChar='\t'
    for info in ${deployInfo[@]}; do
        if [[ $revert == "true" ]]; then
            $printFunction "${cmdepgvIndentChar}$((i++)). `echo $info | cut -d $CMDEP_N_RFS -f1 | cut -d'=' -f2`"
        else
            $printFunction "${cmdepgvIndentChar}$((i++)). `echo $info | cut -d $CMDEP_N_RFS -f2 | cut -d'=' -f2`"
        fi
    done
    unset -v cmdepgvIndentChar
}

__cmdepCollectDeployInfo() # isRevert productName1 productName2 ...
{
    local revert=$1
    local productList=( ${@:2} )
    local productName_i
    retCDI_allDeployInfo=() # Don't make this local, this variable will be the return value of __cmdepCollectDeployInfo
    
    for productName_i in ${productList[@]}; do
        local deployInfo=$(__cmdepGetMatchingDeployInfoRecords $productName_i)
        if [[ $revert == "true" ]]; then 
            deployInfo=($(echo "$deployInfo" | cut -d ";" -f1 | sort | uniq 2>/dev/null))
        else
            deployInfo=( $(echo "$deployInfo") )
        fi
        if [[ -n $deployInfo ]]; then
            local choiceCount=${#deployInfo[@]}
            local choice=0
            if [[  "$choiceCount" -gt 1 ]]; then
                __warningMsg "There are more than one options mapping to $productName_i"
                __msg "Please select a source...."
                iChoice=1
                for deployInfoSub in ${deployInfo[@]}; do
                    eval ${deployInfoSub}
                    if [[ $revert == "true" ]]; then 
                        __msg  "\t$iChoice. $dest"
                    else
                        __msg  "\t$iChoice. $source"
                    fi
                    ((++iChoice))
                done # | grep -i "$productName_i" 2>/dev/null  #using grep to highlight the common part
                # last option is push all.
                __msg "\t$iChoice. All" && ((++choiceCount))
                __msg "Enter a number(press ctrl + C to quit!!): "
                while read choice; do
                    if [[ "$choice" -ge "1" && "$choice" -le "$choiceCount" ]]; then 
                        break;
                    else
                        __msg "Please enter a number from 1 to $choiceCount"
                    fi
                done
                
                if [[ "$choice" -ge "1" && "$choice" -lt "$choiceCount" ]]; then
                    retCDI_allDeployInfo+=( ${deployInfo[$((choice - 1))]} )
                    continue
                fi
            fi
            # this is for option "all" or for case of non-ambiguous
            retCDI_allDeployInfo+=( ${deployInfo[@]} )
            unset -v deployInfo
        else
            __cmdepErrorAndHelp "addconfig" "$productName_i is not known with current config files please specify new config with option [--addconfig] or [--altsource and --altdest]"
        fi
    done
}

__cmdepDeploy() #serverIP COMPILERENV MODE isRevert <DeployInfo|APP[...]>
{
    local serverIP=$1 COMPILERENV=$2 MODE=$3 revert=$4
    local productList=(${@:5})
    local binsCount=${#productList[@]}
    local serverAccount=root@$serverIP
    local cpCommand=scp
    local numOfPush=0
    local allDeployInfo
    __DEBUG set -x
    if ((binsCount == 0)); then
        local hlpopt="#" ; [[ $revert == "true" ]] && hlpopt="revert"
        __cmdepErrorAndHelp $hlpopt "Please specify the application name. i.e: apphmi_master-cgi3-rnaivi_out.out\n Please use <Tab><Tab> to get hint: i.e apphmi_<Tab><Tab>    !!"
    fi
    
    __cmdepDeploy_prv_RemoteExc() #remote commands
    {
        local rmActionType=$1
        local rmExc=echo
        
        if [[ $rmActionType == copy ]]; then 
            local rmFrom=$2
            local rmTo=$serverAccount:$3
            scp $rmFrom $rmTo 2> >(__stdErrorMsg)
        elif [[ $rmActionType == remote ]]; then
            ( local rmCmd=${@:2}
            ssh $serverAccount "$rmCmd" ) 2> >(__stdErrorMsg)
        fi
        
        local rmErrorCode=$? 
        [[ $rmErrorCode == 0 ]] && return 0
        
        if [[ $rmErrorCode == 255 ]]; then
            __errorMsg "Connection error"
            return $CMDEP_ERROR_CONNECTION_ERROR
        else
            __warningMsg "Remote command execution failed"
            return $CMDEP_ERROR_REMOTE_COMMAND_ERROR
        fi
    }
    __cmdepDeploy_prv_Impl()
    {
        local deployInfo=$1
        local localProductName=$2
        local localProductPath=""
        
        unset -v dest destdir source filter
        eval "$deployInfo"
        if [[ -z $source ]]; then
            __dbgMsg "Deploy information = $deployInfo"
            __dbgMsg "Source evaluated from deploy info: $source"
        fi
        if [[ $revert == "false" ]]; then
            localProductName=$(basename $source)
            [[ -z $source ]] && __dbgMsg "__cmdepDeploy_prv_Impl: source is empty"
            if [[ $source == *"_stripped_"* && -e $source ]]; then
                __dbgMsg "using $source as stripped binary"
            else
                __msg "Looking for stripped binary of $localProductName ... "
                if [[ $source == *"out.out" ]]; then
                    local sourceBasePath=${source%/*}
                    localProductPath="${sourceBasePath}/stripped/${localProductName%_out.out}_stripped_out.out"
                    ! [[ -f $localProductPath ]] && __warningMsg "$localProductPath: --> No such file or directory"
                elif [[ $source == *"so.so" ]]; then
                    local sourceBasePath=${source%/*}
                    localProductPath="${sourceBasePath}/stripped/${localProductName%_so.so}_stripped_so.so"
                    ! [[ -f $localProductPath ]] && __warningMsg "$localProductPath: --> No such file or directory"
                fi
            fi
            ! [[ -f $localProductPath ]] && localProductPath="$source"
            if [ -e $localProductPath ]; then 
                serverProductPath=$dest
                __msg 
                __msg "Deploying: \t$CL_GREEN $localProductName... $CL_NONE"
                __msg "SOURCE    : \t$localProductPath"
                __msg "DEST      : \t${serverIP}:$serverProductPath"
                __msg 
                
                # Make filesystem writable and backup old file here
                __cmdepDeploy_prv_RemoteExc remote "
                            echo 'CMLOCAL2SERVER: start working on server'
                            rwrfs ;
                            umount /etc/shadow 2>/dev/null
                            cp /etc/shadow_w_root /etc/shadow 2>/dev/null
                            touch /opt/bosch/disable_reset.txt; sync
                            exchnd_ctl --set-sig-config=ESC_RBCM_NORESTART
                            echo 'CMLOCAL2SERVER: already disabled reset'
                            export bkext=''
                            if [ -e ${serverProductPath}.ori ]; then
                                mv $serverProductPath ${serverProductPath}.bak 2>/dev/null && echo -e 'CMLOCAL2SERVER: ${CL_GREEN}RENAMED ${CL_NONE} $serverProductPath to ${serverProductPath}.bak'
                            else
                                mv $serverProductPath ${serverProductPath}.ori 2>/dev/null && echo -e 'CMLOCAL2SERVER: ${CL_GREEN}RENAMED ${CL_NONE} $serverProductPath to ${serverProductPath}.ori'
                            fi
                            "
                [[ $? == $CMDEP_ERROR_CONNECTION_ERROR ]] && return $CMDEP_ERROR_CONNECTION_ERROR
                # Copy file to server
                __cmdepDeploy_prv_RemoteExc copy $localProductPath $serverProductPath && ((numOfPush++)) && __msg "Pushing $localProductPath to $serverAccount \t\t\t--> DONE!\n"
                __cmdepDeploy_prv_RemoteExc remote "chmod a+x $serverProductPath"
                [[ $? == $CMDEP_ERROR_CONNECTION_ERROR ]] && return $CMDEP_ERROR_CONNECTION_ERROR
            else
                __errorMsg "$localProductPath: --> No such file or directory"
                return $CMDEP_ERROR_FILE_NOT_FOUND
            fi
        else
            # Revert binary on server
            serverProductPath=$dest
            __msg "--> Trying to revert $serverProductPath ... "
            __cmdepDeploy_prv_RemoteExc remote "rwrfs;
                        if [ -e ${serverProductPath}$revertBakExt ]; then 
                            rm $serverProductPath; mv ${serverProductPath}$revertBakExt $serverProductPath && echo -e 'CMLOCAL2SERVER: ${CL_GREEN}RENAMED ${CL_NONE} ${serverProductPath}$revertBakExt to $serverProductPath'
                        else
                            echo -e 'CMLOCAL2SERVER: $CL_ORANGE ${serverProductPath}$revertBakExt does not exist $CL_NONE' >/dev/stderr
                            exit $CMDEP_ERROR_REMOTE_COMMAND_ERROR
                        fi
                        " && ((numOfPush++)) && __msg "Revert $serverProductPath done!!!" 
            return $?
        fi
    }
    
__separatedRegion "="
    
# --> CASE 1: 
    # USER passes deployment infor instead of binaries name --> productList == deployinfo (dest=path/to/file/onserver;source=path/to/file/on/local)
    if [[ $binsCount == 1 ]]; then
        __dbgMsg "CASE 1: ${productList[@]}"
        unset -v dest source 
        local productName=`echo $productList | grep -oP 'dest=.+;source=.+'`
        if [[ -n $productName ]]; then
            allDeployInfo=$productName
        fi
    fi
    
# --> CASE 2:
    # USER passes binaries name instead apphmi_sds-cgi3-rnaivi | libapphmi_xxx
    if [[ -z ${allDeployInfo[@]} ]]; then
        __dbgMsg "CASE 2: ${productList[@]}"
        __cmdepCollectDeployInfo $revert ${productList[@]}
        allDeployInfo=( ${retCDI_allDeployInfo[@]} )
        __dbgMsg "${allDeployInfo[@]} --> ${retCDI_allDeployInfo[@]}"
        unset -v retCDI_allDeployInfo
    fi
    
    # after having correct deploy information then deploy them/it
    local strAction="deploy"; [[ $revert == "true" ]] && strAction="revert"
    
    if [[ ${#allDeployInfo[@]} -gt 0 ]]; then 
        __msg "INFORMATION: \t\t\tSERVER: $serverIP\tBUILDENV: $COMPILERENV\tMODE: $MODE"
        __msg "Preparing to $strAction bellow application(s) to $serverAccount:"
        local deployInfo_i it=0
        for deployInfo_i in ${allDeployInfo[@]};do
            eval $deployInfo_i
            local pathTodisplay=$source
            [[ $revert == "true" ]] && pathTodisplay=$dest
            __msg "\t$((++it)).File: $pathTodisplay "
        done
        unset -v dest source
        __msg "${strAction}ing start: "
        for deployInfo_i in ${allDeployInfo[@]}; do
            [[ -n $deployInfo_i ]] && __cmdepDeploy_prv_Impl $deployInfo_i; [[ $? == $CMDEP_ERROR_CONNECTION_ERROR ]] && break;
        done
    else
        __dbgMsg "${allDeployInfo[@]}"
    fi
    
    local msg=""
    if [[ $revert == "true" ]] ; then
        msg=" application(s) were/was reverted on"
    else
        msg=" application(s) were/was pushed on"
    fi
    
    if [ $numOfPush -gt 0 ]; then
        __cmdepDeploy_prv_RemoteExc remote "sync" && __msg "sync!!"
        if [[ "$noreboot" == "true" ]]; then 
            __warningMsg "No reboot!!!, you have to reboot server yourself to do further things"
        else
            __msg "Rebooting $serverIP ...."
            __cmdepDeploy_prv_RemoteExc remote "reboot" &
        fi
    fi
    
    __msg "Job finished at: `date`"
    __cmdepReportErrorCount
    __msg "INFO:\t$numOfPush $msg $serverAccount"

__separatedRegion "="
__DEBUG set +x
}

__cmdepIndexPkgFiles() #$1: deployInfoStorageFile $2: productListStorageFile $3...: pkgFiles
{
    case $CMDEP_V_TOOL_FOR_INDEXING in
    "awk")
        __cmdepIndexPkgFilesUsingAwk $@
        ;;
    "python")
        __cmdepIndexPkgFilesUsingPython $@
        ;;
    *)
        __errorMsg "Indexing facility is not specified please set CMDEP_V_TOOL_FOR_INDEXING = python|awk "
        ;;
     esac
}
__cmdepIndexPkgFilesUsingPython() #$1: deployInfoStorageFile $2: productListStorageFile $3...: pkgFiles
{
    local supportedTypes=${CMDEP_V_SUPPORTED_TYPES//\\/}
    local deployInfoStorageFile=$1
    local productListStorageFile=$2
    local pkgFiles=${@:2}
    python $CMDEP_F_PYTHON_INDEXER_SCRIPT $supportedTypes $deployInfoStorageFile $pkgFiles
}


#indexConfigFile config.xml dt.dat hint.dat
__cmdepIndexPkgFilesUsingAwk() #$1: deployInfoStorageFile $2: productListStorageFile $3...: pkgFiles
{
    [[ $# -lt 3 ]] && __errorMsg "AWK: parameters missing --> __cmdepIndexPkgFiles deployInfoStorageFile productListStorageFile pkgFilesList" && return
    local deployInfoStorageFile=$1
    local productListStorageFile=$2
    local pkgFiles=${@:2}
    touch $deployInfoStorageFile $productListStorageFile 
    awk -v OUTPUTFS=$CMDEP_N_RFS -v storedDeployInfoFile=$deployInfoStorageFile -v CMDEP_F_PRODUCT_LIST_FILE=$productListStorageFile \
    '
    function verboseMsg(msg)
    {
        if(verbose != 0)
        {
            print "[CMLOCAL2SERVER]-INFO: " msg
        }
    }
    function warn(msg)
    {
        print "[CMLOCAL2SERVER]-WARNING: " msg > "/dev/stderr"
    }
    function isSupportedType(filePath)
    {
        match(filePath, SUPPORTED_TYPES)
        
        if(RLENGTH != -1)
        {
            return 1
        }
        else
        {
            return 0;
        }
    }
    
    function extractValueOf(key)
    {
        found = 0;
        value = ""
        for(i = 1; i <= NF; ++i)
        {
            if(found && $i != "")
            {
                value = $i;
                break;
            }
            else if($i == key)
            {
                found = 1;
                continue;
            }
        }
        return value;
    }
    
    function getBaseName(path)
    {
        if(isSupportedType(path)) 
        {
            split(path, parts, "/")
            return parts[length(parts)]
        }
    }
    
    function getBaseNames(path, filter)
    {
        gsub("\\*", "\\.\\*", filter)
        cmd = "ls " path " 2>/dev/null | grep " filter " 2>/dev/null"
        idx = 1
        while ( ( cmd | getline result ) > 0 ) 
        {
            if(isSupportedType(result)) {
                basenames[idx++] = result
            } 
        } 
        close(cmd)
    }
    function dbgMsg(msg)
    {
        if(debugEnabled == 1)
        {
            print "AWK --> DBG: " msg
        }
    }
    function writeToFile(source, dest, productname)
    {
        foundProductsCount++
        gsub("//", "/", source)
        gsub("//", "/", dest)
        print "dest=" dest OUTPUTFS "source=" source >> storedDeployInfoFile
        print productname >> CMDEP_F_PRODUCT_LIST_FILE
        verboseMsg("Found: " productname)
    }
    function writeListOfBaseNames(source, realSource, dest, filter)
    {
        delete basenames
        getBaseNames(realSource, filter);
        if(length(basenames) > 0)
        {            
            for(idx in basenames)
            {
                productname = basenames[idx]
                if(productname =="") continue
                writeToFile(source "/" productname, dest "/" productname, productname)
            }
            return 1;
        }
        else
        {
            return 0;
        }
    }
    
    BEGIN{ 
        FS = "=| |\t|\""
        foundProductsCount = 0
        buildroot = ENVIRON["_SWBUILDROOT"]
        naviroot = ENVIRON["_SWNAVIROOT"]
        verbose = ENVIRON["CMDEP_V_NOISY_INDEXING"]
        debugEnabled = ENVIRON["CMDEPDEBUG"] == "on" ? 1 : 0
        SUPPORTED_TYPES = ENVIRON["CMDEP_V_SUPPORTED_TYPES"]
        acceptPattern1 = "(file|folder){1}.*dest.*=.*source.*=.*\""
        acceptPattern2 = "(file|folder){1}.*source.*=.*dest.*=.*\""
        ignorePattern1 = "<!--.*"
        verboseMsg("Start parsing input....")
        dbgMsg("Debug enabled")
    }
    
    {
        if( $0 ~ ignorePattern1 || ($0 !~ acceptPattern2 && $0 !~ acceptPattern1) ) 
        {
            if(debugEnabled)
            {
                if($0 ~ ignorePattern1)
                    dbgMsg($0)
            }
            next
        }
        
        source = extractValueOf("source");
        if(length(source) > 0)
        {
            if(isSupportedType(source) )
            {
                productname = getBaseName(source);
                dest = extractValueOf("dest");
                if(length(dest) > 0)
                {
                    if( !isSupportedType(dest) )
                    {
                        dest = dest "/" productname;
                    }
                }
                else
                {
                    destdir = extractValueOf("destdir");
                    if(length(destdir) > 0) { dest = destdir "/" productname; }
                }
                
                writeToFile(source, dest, productname)
            }
            else
            {
                filter = extractValueOf("filter")
                if(filter == "") next
                if(!isSupportedType(filter)) next
                
                realSource = source
                gsub("\\$\\{_SWNAVIROOT\\}", naviroot, realSource);
                gsub("\\$\\{_SWBUILDROOT\\}", buildroot, realSource);
                                
                dest = extractValueOf("dest");
                if(length(dest) <= 0)
                {
                    dest = extractValueOf("destdir");
                }
                
                
                if(writeListOfBaseNames(source, realSource, dest, filter) == 0)
                {
                    foundWhenTry = 0
                    if(index(realSource, "{COMPILERENV}") != 0)
                    {
                        realSource = source
                        # debug - arm
                        gsub("\\$\\{COMPILERENV\\}", "gen3armmake", realSource);
                        gsub("\\$\\{MODE\\}", "debug", realSource);
                        foundWhenTry += writeListOfBaseNames(source, realSource, dest, filter)
                        
                        # debug - x86
                        gsub("gen3armmake", "gen3x86make", realSource);
                        foundWhenTry += writeListOfBaseNames(source, realSource, dest, filter)
                        
                        # release - x86
                        gsub("debug", "release", realSource);
                        foundWhenTry += writeListOfBaseNames(source, realSource, dest, filter)
                        
                        # release - arm
                        gsub("gen3x86make", "gen3armmake", realSource);
                        foundWhenTry += writeListOfBaseNames(source, realSource, dest, filter)
                        
                    }
                    if(foundWhenTry == 0)
                    {
                        warn("unable to find things with: " $0) 
                    }
                }
            }
        }
    }
    
    END{
        verboseMsg("Parsing " FILENAME " done!")
        if(foundProductsCount == 0)
        {
            verboseMsg("No product found with " FILENAME)
        }
        else
        {
            verboseMsg(foundProductsCount " products were added to index")
        }
    }
    ' $pkgFiles #--> means list of pkg files
    
    cat $deployInfoStorageFile | sort | uniq > "$deployInfoStorageFile~"
    cat $productListStorageFile | sort | uniq > "$productListStorageFile~"
    mv $deployInfoStorageFile~ $deployInfoStorageFile
    mv $productListStorageFile~ $productListStorageFile 
}

__cmdepIndexStoredPkgFiles()
{
    [[ $1 == "--verbose" ]] && export CMDEP_V_NOISY_INDEXING=1
    
    if [[ ! -e $CMDEP_D_DATA_DIR ]]; then
        mkdir -p $CMDEP_D_DATA_DIR
    fi
    echo "" > $CMDEP_F_DEPLOY_INFORMATION_FILE
    echo "" > $CMDEP_F_PRODUCT_LIST_FILE
    local pkgFilesList=$(__cmdepGetExistingPkgFiles)
    [[ -n ${pkgFilesList[@]} ]] && __cmdepIndexPkgFiles $CMDEP_F_DEPLOY_INFORMATION_FILE $CMDEP_F_PRODUCT_LIST_FILE "${pkgFilesList[@]}"
    
    unset -v CMDEP_V_NOISY_INDEXING
}

__cmdepUninstall()
{
#1. has to be done first
    eval "$( awk ' !/^#|^[[:space:]]*$/ {  printf "unalias bldprd" $1 "; unalias bldprdsrc" $1 "; " } ' $CMDEP_F_SETTINGS_FILE )"
    unalias cmlocal2server
    complete -F _buildproduct buildproduct #rebind as default

    sed -i.bak "/####CMDEPCOMMANDS###$/d" ~/.bashrc
    
# 2. has tobe done secondly
    rm $CMDEP_D_DATA_DIR/l2s* $CMDEP_F_CMLOCAL2SERVER_SCRIPT 2>/dev/null
    rm $CMDEP_F_CMLOCAL2SERVER_SCRIPT
    
# 3. has to be done thirdly
    unset -v CMDEP_F_GDB_INSTALLATION_SCRIPT CMDEP_D_DEBUGGER_ROOT_DIR CMDEP_N_GDBINIT
    unset -v CMDEP_ERROR_FILE_NOT_FOUND CMDEP_ERROR_CONNECTION_ERROR CMDEP_ERROR_REMOTE_COMMAND_ERROR
    unset -v     cmdepDffAssetGenCompleteSignal CMDEP_N_RFS cmdepvarRunAssetGenScriptName
    unset -v  CMDEP_F_CMLOCAL2SERVER_SCRIPT CMDEP_F_CUSTOM_DEPLOY_INFO_FILE CMDEP_F_SETTINGS_FILE CMDEP_F_SUPPORTED_TYPES_FILE CMDEP_F_RUNNING_OBSERVATION_PROCESS  
    unset -v CMDEP_D_DATA_DIR CMDEP_D_INSTALLATION_DIR CMDEPDEBUG __updateself cmdepInsScriptName CMDEP_N_BRANCH_IDENTIFIER  
    unset -v CMDEP_F_DEPLOY_INFORMATION_FILE CMDEP_F_PRODUCT_LIST_FILE CMDEP_F_LAST_MODES_FILE CMDEP_F_DEFAULT_PKG_LIST_FILE CMDEP_V_SUPPORTED_TYPES CMDEP_V_TOOL_FOR_INDEXING
    unset -f __DEBUG __msg __redMsg __dbgMsg __errorMsg __warningMsg __stdErrorMsg __separatedRegion
    unset -f __cmdepExit __cmdepl2sMain __cmdepDeploy_prv_Impl __cmdepIndexPkgFiles __cmdepIndexPkgFilesUsingPython __cmdepIndexPkgFilesUsingAwk __cmdepIndexStoredPkgFiles __cmdepUninstall __cmdepCompleteProductName __cmdepStopObservationMode
    unset -f __cmdepHelp __cmdepErrorAndHelp __cmdepPrintCommandsHelp __cmdepCompleteBuildProductCmd __cmdepl2sMainComp __cmdepInstallHelp __cmdepStartObservationMode
    unset -f __cmdepMakeEnvVarsAsStringLiteral __cmdepUndoMakingEnvVarsAsStringLiteral __cmdepAssertBuildEnv __cmdepWildcard2Regex __cmdepRememberPkgFiles __cmdepAddNewPkgFile __cmdepGetExistingPkgFiles  __cmdepDeploy_prv_RemoteExc __cmdepGetServerInformation
    unset -f __installCommandsScript __cmdepAddNewSupportedType __cmdepRemoteDebug __cmdepDeploy __cmdepGetMatchingDeployInfoRecords __cmdepPrintBuildProductHelp  __cmdepBuildProduct __cmdepCreateBuildProductAliases 
    unset -f __cmdepCollectDeployInfo __cmdepCreateAssetGenRunScript __cmdepDisplayDeployInfo __cmdepFormDeployInfoRecord __cmdepObserveAssetBin __cmdepl2sArgsCheck __cmdepMapToPathOnServer __cmdepReportErrorCount __cmdepStartErrorCounting  
    
    
    clear
    echo "all commands and data files have completely uninstalled"
}

__cmdepCompleteProductName()
{
    local curw=${COMP_WORDS[COMP_CWORD]}
    productnames=`grep -P "^${curw}" "$CMDEP_F_PRODUCT_LIST_FILE" 2>/dev/null | cut -d. -f1 2>/dev/null`
    if [[ -z $productnames ]] ; then
        local inp=$(__cmdepWildcard2Regex $curw)
        productnames=`grep -P "^${inp}" "$CMDEP_F_PRODUCT_LIST_FILE" 2>/dev/null | cut -d. -f1 2>/dev/null`
    fi
    if [[ -z $productnames ]] ; then
        productnames=`grep -ioE "${curw}.*$" "$CMDEP_F_PRODUCT_LIST_FILE" 2>/dev/null | cut -d. -f1 2>/dev/null`
    fi
     COMPREPLY=(${productnames[@]})
}

__cmdepCompleteBuildProductCmd()
{
    COMPREPLY=()
    # Assume that we have _buildproduct after running set_env.sh script 
    _buildproduct 2>/dev/null 
    [[ -z ${COMPREPLY} ]] && __cmdepCompleteProductName
}
__cmdepMapToPathOnServer() #source 
{
    local sourcePath=$1
    local sourceName=`basename $sourcePath`
    sourceName=${sourceName/_stripped/}
    local deployInfo=($(grep -iP $sourceName $CMDEP_F_DEPLOY_INFORMATION_FILE ))
    local record
    for record in ${deployInfo[@]}; do
        eval $record
        [[ -n $dest ]] && echo $dest
    done
    unset -v source dest
}
__cmdepl2sMainComp() 
{
    __cmdepl2sMainComp_prv_Set_COMPREPLY()
    {
        COMPREPLY=( "$@" )
        CMDEP_V_COMP_PREVIOUS_COMPREPLY=( ${COMPREPLY[@]} )
    }
     
    
    local cur prev words cword
    local modes='release debug'
    local servers=$(awk ' !/^#|^[[:space:]]*$/ { print $1 } ' $CMDEP_F_SETTINGS_FILE )
    local buildmodes='rebuild build noprecreate'
    local observeactions="off $_SWROOT/ai_nissan_hmi/products/NINCG3/Apps/"
    local helps="altsource altdest mode server addconfig build noreboot revert reindex uninstall save debug port newtype changeSettings observe"
    local revertOpts=".ori .bak"
    local options=' 
        --help
        --altsource=
        --altdest=
        --mode= 
        --server=
        --addconfig=
        --build=
        --noreboot 
        --revert 
        --reindex
        --uninstall
        --save
        --debug
        --changeSettings
        --port=
        --newtype=
        --observe=
        '
    cur=${COMP_WORDS[COMP_CWORD]}
    prev=${COMP_WORDS[COMP_CWORD-1]}
    COMPREPLY=()
    
    #just print out previous completion
    [[ $COMP_TYPE == 63 ]]  && COMPREPLY=( ${CMDEP_V_COMP_PREVIOUS_COMPREPLY[@]}) && return
    
    if [[ $cur == "=" ]]; then
        cur=""
    fi

    if [[ $prev == "=" ]]; then
        prev=${COMP_WORDS[COMP_CWORD-2]}
    fi
     
    case $cur in
    --help | --revert)
        __cmdepl2sMainComp_prv_Set_COMPREPLY "${cur}="
        ;;
    esac
            
    case $prev in
    --help)
        __cmdepl2sMainComp_prv_Set_COMPREPLY $(compgen -W "$helps" -- "$cur")
         ;;
    --mode)
         __cmdepl2sMainComp_prv_Set_COMPREPLY $( compgen -W "$modes" -- "$cur" ) 
         ;;
    --server)
         __cmdepl2sMainComp_prv_Set_COMPREPLY $( compgen -W "$servers" -- "$cur" ) 
         ;;
    --addconfig)
        [[ ${COMP_WORDS[COMP_CWORD]}  == "=" ]] && __cmdepl2sMainComp_prv_Set_COMPREPLY "${_SWROOT}/" && compopt -o nospace
        ;;
    --build)
        __cmdepl2sMainComp_prv_Set_COMPREPLY $( compgen -W "$buildmodes" -- "$cur" ) 
        ;;
    --observe)
        __cmdepl2sMainComp_prv_Set_COMPREPLY $( compgen -W "$observeactions" -- "$cur" )  && compopt -o nospace
        ;;
    --altdest)
        __dbgMsg "altdest"
        if [[ $COMP_LINE == *"--altsource"* ]]; then
            local inputSource=`echo $COMP_LINE | grep -oP "altsource=[^[[:space:]]*" | cut -d= -f2`
            __dbgMsg $inputSource
            [[ -z $cur && -n $inputSource ]] && __cmdepl2sMainComp_prv_Set_COMPREPLY $(__cmdepMapToPathOnServer $inputSource)
        fi
        return
        ;;
    --altsource|--newtype|--changeSettings)
        return
        ;;
    --revert)
        __cmdepl2sMainComp_prv_Set_COMPREPLY $( compgen -W "$revertOpts" -- "$cur" ) 
         ;;
    *)
         ;;
    esac
    
    ! [[ -n $COMPREPLY ]] && __cmdepl2sMainComp_prv_Set_COMPREPLY $( compgen -W "$(cat $CMDEP_F_PRODUCT_LIST_FILE 2>/dev/null; echo ' ' $options)" -- "$cur" ) 
    
    case $COMPREPLY in
        *= | *'"' | "--help" | "--revert" )
            compopt -o nospace
            ;;
    esac
    
    [[ -n $COMPREPLY ]] && return
    
    if [[ -z $COMPREPLY ]]; then
#     __cmdepMakeEnvVarsAsStringLiteral
        local _SWNAVIROOT='${_SWNAVIROOT}' COMPILERENV='${COMPILERENV}'  MODE='${MODE}' _SWBUILDROOT='${_SWBUILDROOT}'
        local WILLREPLY=()
        unset -v dest source
        local IFS=$'\n'
        local grepResult=( $(grep -iE "$cur" $CMDEP_F_DEPLOY_INFORMATION_FILE 2>/dev/null ) )
        
        if [[ -z $grepResult ]]; then
            cur=`__cmdepWildcard2Regex "$cur"`
            grepResult=( $(grep -iE $cur $CMDEP_F_DEPLOY_INFORMATION_FILE 2>/dev/null ) ) #search for wildcard expression
        fi
        
        for rslt in ${grepResult[@]}; do
            eval "${rslt}"
            WILLREPLY+=( `echo $source | grep -ioE "${cur}.*$" 2>/dev/null ` )
            unset -v dest source
        done
        __cmdepl2sMainComp_prv_Set_COMPREPLY ${WILLREPLY[@]}
#     __cmdepUndoMakingEnvVarsAsStringLiteral
    fi
    
}

__cmdepCreateBuildProductAliases()
{
     echo Hello
}

#     Index the config files to get the hints for command completion
if [[ $0 == "bash" ]]; then
     __cmdepIndexStoredPkgFiles
     alias cmlocal2server=__cmdepl2sMain
     complete -o default -F __cmdepl2sMainComp cmlocal2server 
     eval "$( awk ' !/^#|^[[:space:]]*$/ {
                                print "alias bldprdsrc" $1 "=\"buildproduct --os=" $3 " --env=" $4 " --buildmode=build --mode=" $5 " --alldeps=none --noprecreate --info --silent\" "
                                print "alias bldprd" $1 "=\"buildproduct --os=" $3 " --env=" $4 " --buildmode=build --mode=" $5 " --info --silent\""
                                print "complete -F __cmdepCompleteBuildProductCmd bldprd" $1
                                print "complete -F __cmdepCompleteBuildProductCmd bldprdsrc" $1
                            } ' $CMDEP_F_SETTINGS_FILE
                )"

     if [[ "bash" == $0 ]]; then
     __msg "${CL_GREEN}cmlocal2server${CL_NONE} is available now!!!"
     __msg "Please type: ${CL_GREEN}cmlocal2server --help${CL_NONE} for usage"
     fi
fi
#ENDDEPLOYSECTION

##############################################################################################################
######################################INSTALL SCRIPT TO COMMANDLINE ##########################################
#_SWNAVIROOT  COMPILERENV MODE _SWBUILDROOT 

cmdepInsScriptName=$0
__cmdepInstallHelp()
{
    __msg
    __msg
    __msg "-----------Installing command to deploy productList/binary files to target or lsim server------------------------------------------------"
    __msg "-->    USAGE:"
    __msg "-H>    bash $cmdepInsScriptName [uninstall]"
    __msg "-E>"
    __msg "-L>    Please make sure you are executing the command in build environment with _SWNAVIROOT, _SWBUILDROOT variables available"
    __msg "-P>    [uninstall] --> specify this flag to uninstall the commands and remove all installed files "
    __msg "------------------------------------------------------------------------------------------------------------------------------------------"
    __msg
    __msg
    __cmdepExit
}

if [[ "$@" == *"--h"* ]]; then
    __cmdepInstallHelp
elif [[ $1 == "--uninstall" ]]; then
    __cmdepUninstall
elif [[ -z ${_SWBUILDROOT} ]]; then 
    __errorMsg "Please run this script in build environment"
    __cmdepInstallHelp
else

    __installCommandsScript() 
    {  
        echo > $CMDEP_F_CMLOCAL2SERVER_SCRIPT
        awk -v destPath=$CMDEP_F_CMLOCAL2SERVER_SCRIPT '{ 
                                            print $0 >> destPath;  
                                            if ( $0 ~/^#ENDDEPLOYSECTION/ )
                                                exit
                                        }' $cmdepInsScriptName
        return $?
    }
    fileModified="true"
    if [ -e $CMDEP_F_CMLOCAL2SERVER_SCRIPT ]
        then
        if [ $CMDEP_F_CMLOCAL2SERVER_SCRIPT -ot $cmdepInsScriptName ]
            then
            __installCommandsScript && __msg "$CMDEP_F_CMLOCAL2SERVER_SCRIPT updated to new version!!!"
        else
            fileModified="false"
        fi
    else
        if ! [ -d $CMDEP_D_INSTALLATION_DIR ]
            then 
            mkdir -p $CMDEP_D_INSTALLATION_DIR
        fi
        __installCommandsScript && __msg "successful installed cmlocal2server command"
    fi
    if ! grep "source $CMDEP_F_CMLOCAL2SERVER_SCRIPT" ~/.bashrc >> /dev/null; then
        echo "if [[ -n \${_SWBUILDROOT} ]]; then source $CMDEP_F_CMLOCAL2SERVER_SCRIPT; fi ####CMDEPCOMMANDS###" >> ~/.bashrc
        __msg "added source command to .bashrc"
    fi
    
# store pre-defined config files and index the files to get deployment info
    echo > $CMDEP_F_SUPPORTED_TYPES_FILE
    echo > $CMDEP_F_SETTINGS_FILE
    echo > $CMDEP_F_DEFAULT_PKG_LIST_FILE
    touch $CMDEP_F_JUST4LAUGH
    
# Supported types that cmlocal2server can parse from pkg.xml files to get deployment information
    echo 'export CMDEP_V_SUPPORTED_TYPES="\\.so|\\.bin|\\.out"' > $CMDEP_F_SUPPORTED_TYPES_FILE
    
# Predefined pkg files to collect the deployment information
    echo '
        ${_SWROOT}/ai_sds_adapter/adapter/config/packages/pkg_sds_adapter.xml
        ${_SWROOT}/ai_nissan_hmi/config/packages/pkg_nissan_hmi.xml
        ${_SWROOT}/ai_hmi_base/config/packages/pkg_hmicgi.xml' >> $CMDEP_F_DEFAULT_PKG_LIST_FILE
    

# IMPORTANT!!!!
# Below lines are being used to index the pkg.xml files to collect the deploy information of products
# It is python code, then the indentation must be absolutely correct with tabsize = 4. 
# Please configure your editor to make sure the tabsize is correct for python interpreter
# to be able to understand or copy the lines inside the single quotes to a python editor and edit it in case facing bug or want to improve 
   echo '
import sys
import os
import glob
import xml.etree.ElementTree as ET



class Replacement:
    def __init__(self, xmlTag, replaced, bylist = []):
        self.xmlTag = xmlTag
        self.replaced = replaced
        self.by = bylist
    def setBy(self, byList = []):
        self.by = []
        for by in byList:
            self.by.append(by.strip())

    def applyOn(self, wantToReplace):
        result = []
        for by in self.by:
            result.append(wantToReplace.replace(self.replaced, by))
        return result

gTestMode = False
gCollectedProductNamesSet = set()
gCollectedConfigRecordsSet = set()
gSupportedFileTypes = [ ".bin", ".so", ".out"]
gCMEnvironVariables = ["_SWNAVIROOT", "_SWBUILDROOT", "COMPILERENV", "MODE"]
gReplacementList = [ Replacement("Customerproject", "${CUSTOMERPROJECT}") ]

def applyAllReplacementOn(wantToReplace):
    result = []
    for replacement in gReplacementList:
        result.append(replacement.applyOn(wantToReplace))
    return result

def verboseMsg(msg):
    if os.environ.has_key("CMDEP_V_NOISY_INDEXING"):
        print("CMLOCAL2SERVER: " + msg)


def getObligatedSystemVariable(key):
    if os.environ.has_key(key):
        return os.environ[key]
    else:
        print(sys.stderr, "CMLOCAL2SERVER - WARNING: dont have variable " + key)
        exit("CMLOCAL2SERVER - WARNING: dont have variable " + key)


def evalPath(path):
    for var in gCMEnvironVariables:
        if os.environ.has_key(var): path = path.replace("${" + var + "}", os.environ.get(var))
    return path


def join(dir, basename):
    return os.path.join(dir, basename)

def achieveProductName(name):
    global gCollectedProductNamesSet
    if name not in gCollectedProductNamesSet:
        gCollectedProductNamesSet.add(name)
        verboseMsg("Found " + name)



def extractBaseName(path):
    return os.path.basename(path)


def formatConfigRecord(dest, source):
    return "dest=" + dest + ";" + "source=" + source


def filesMatch(dir, filter):
    ret = (glob.glob(os.path.join(dir, filter)))
    return ret


def isPathToSupportedType(path):
    for t in gSupportedFileTypes:
        if path.endswith(t):
            return True;
    return False


def tryCollectMatchingFilesWithFilter(source, filter):
    matchedFiles = filesMatch(source, filter)
    if len(matchedFiles) == 0:
        source = source.replace("${COMPILERENV}", "gen3armmake")
        source = source.replace("${MODE}", "debug")
        matchedFiles += filesMatch(source, filter)

        source = source.replace("gen3armmake", "gen3x86make")
        matchedFiles += filesMatch(source, filter)

        source = source.replace("debug", "release")
        matchedFiles += filesMatch(source, filter)

        source = source.replace("gen3x86make", "gen3armmake")
        matchedFiles += filesMatch(source, filter)
    if len(matchedFiles) == 0:
        verboseMsg("Dont found anything with folder " + source + " and filter = " + filter)
    return matchedFiles


def extractL2SDeploymentRecords(elem, replacementList = []):
    outrecords = []
    sourcelist = []
    source = elem.get("source")
    dest = elem.get("dest")
    if source == None: source = elem.get("sourcedir")
    if dest == None: dest = elem.get("destdir")
    if dest == None or source == None:
        return ""

    if isPathToSupportedType(source):
        sourcelist.append(source)
    else:
        filter = elem.get("filter")
        sourceDir = evalPath(source)
        if filter != None:
            listOfRealSourcePath = tryCollectMatchingFilesWithFilter(sourceDir,
                                                                     filter)  # filesMatch(sourceDir, filterList)
            for sourcePath in listOfRealSourcePath:
                if isPathToSupportedType(sourcePath):
                    sourcelist.append(join(source, extractBaseName(sourcePath)))
    if len(replacementList) > 0:
        tempSourceList = []
        for source in sourcelist:
            for replacement in replacementList:
                tempSourceList += replacement.applyOn(source)
        sourcelist = tempSourceList

    for source in sourcelist:
        basename = extractBaseName(source)
        achieveProductName(basename)
        if isPathToSupportedType(dest):
            record = formatConfigRecord(dest, source)
        elif isPathToSupportedType(source):
            record = formatConfigRecord(join(dest, basename), source)
        outrecords.append(record)

    return outrecords

def extractReplacements(pkg):
    listReplacement = []
    for replacement in gReplacementList:
        filter = pkg.find(replacement.xmlTag)
        if filter != None:
            replacement.setBy(filter.text.split(","))
            listReplacement.append(replacement)

    return listReplacement

def parsePkgFile(pkgFile):
    global gCollectedConfigRecordsSet
    verboseMsg("Start parsing file " + pkgFile)
    root = ET.parse(pkgFile).getroot()
    pkgs = root.findall("./pkg")
    for pkg in pkgs:
        replacements = extractReplacements(pkg)
        for elemFile in pkg.findall("./files/file"):
            records = extractL2SDeploymentRecords(elemFile, replacements)
            if len(records) > 0: gCollectedConfigRecordsSet.update(records)
        for elemFolder in pkg.findall("./folders/folder"):
            records = extractL2SDeploymentRecords(elemFolder, replacements)
            if len(records) > 0: gCollectedConfigRecordsSet.update(records)

    verboseMsg("Parsing " + pkgFile + " Done!")

def consoleWritelines(dataset):
    print ( "\n".join(dataset) )

def fileWritelines(filename, dataset):
    if len(dataset) > 0:
        outf = open(filename, "a")
        outf.write("\n")
        outf.write("\n".join(dataset))
        outf.close()

def writelines(filename, dataset):
    if gTestMode:
        consoleWritelines(dataset)
    else:
        fileWritelines(filename, dataset)

# parameters will be like this:
# python pkg2cmdepconfig.py path/to/config/file.xml supported_type1 supported_type2 .. supported_typeNl
if __name__ == "__main__":

    if gTestMode:
    # for testing and debugging purpose
        if os.name == "NT":
            pkgfiles = [ "Z:\\views\\nincg3\\ai_nissan_hmi\\config\\packages\\pkg_nissan_hmi.xml"]
        else:
            pkgfiles = [ "/data2/cgo1hc/samba/views/nincg3/ai_audio/components/packages/xml/pkg_procaudio.xml" ]

        configRecordsOutputFile = ""
        productNamesOutputFile = ""
    else:
        argc = len(sys.argv)
        if argc < 5:
            exit("Please specify enough arguments")

        gSupportedFileTypes = sys.argv[1].split("|")
        configRecordsOutputFile = sys.argv[2]
        productNamesOutputFile = sys.argv[3]
        pkgfiles = sys.argv[4:]

    for pkgfile in pkgfiles:
        parsePkgFile(pkgfile)

    writelines(configRecordsOutputFile, gCollectedConfigRecordsSet)
    writelines(productNamesOutputFile, gCollectedProductNamesSet)

    verboseMsg("Indexing pkg files done!!!")
    verboseMsg("Found {0} products".format(len(gCollectedProductNamesSet)))
    ' > $CMDEP_F_PYTHON_INDEXER_SCRIPT

# Generate setting file for default value that user can edit later
echo '
#  Layout the values by collumn and separate collumn by spaces, (*) means default server when the --server option is not provided and only one is allowed
#  ServerName(1)      ServerIP(2)         OperatingSystem(3)        CompileEnvironment(4)        DefaultMode(5)
    lsim                  172.17.0.11         linux                         gen3x86make                     debug 
    target                172.17.0.1          linux                         gen3armmake                     debug                 (*)
' > $CMDEP_F_SETTINGS_FILE

    echo "Installation done!"
    echo -e "Please type: ${CL_GREEN}source $CMDEP_F_CMLOCAL2SERVER_SCRIPT${CL_NONE} to use ${CL_GREEN}cmlocal2server${CL_NONE}"
    
fi
##############################################################################################################