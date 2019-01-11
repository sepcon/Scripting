#!/bin/bash


export __cfe_vHelpString="
USAGES:
    configeditor -a  file1 file2 ... fileN
    configeditor -a  file1 file2 ... fileN1 -f VARIANT_NAME_FILTER filex1 filex2 filexN -f VARIANT_NAME_FILTER2...
    configeditor -r  old1 new1 old2 new2 ...
    configeditor -d  file1 file2 ... fileN
EXPLAINATION:
    -a: add file[s] to to xml config file
    -d: delete file[s] from xml config file
    -r: rename files by pairs of OLD_FILE NEW_FILE
    -f: variant Filter please consider 
"

__cfe_fncErrorHelp()
{
    echo $__cfe_vHelpString
    kill -INT $$
}

__cfe_fncConfigEditor() #
{
    local thisFolderName=`basename $(pwd) `
    local configFilePath=$(pwd)/${thisFolderName}.xml
    if ! [[ -f $configFilePath ]]; then
        echo "ERROR: $configFilePath does not exist
    Please invoke this command in the directory that contains xml config file"
        return -1
    fi
    
    [[ $@ = *"-h"* ]] && echo $__cfe_vHelpString && return 0

    python -c "$__cfe_vPythonConfigEditorScript" $configFilePath $@
    
}

__cfe_fncCOMPLINEContains() #$string
{
    if [[ $COMP_LINE == *"$1"* ]] ; then
        return 0
    else
        return -1
    fi
}

__cfe_fncComp()
{
    if [[ $COMP_LINE == *"-a"* || $COMP_LINE == *"-d"* || $COMP_LINE == *"-r"* ]]; then
        COMPREPLY=()
        return
    else
        local curw=${COMP_WORDS[COMP_CWORD]}
        COMPREPLY=( $(compgen -W "-a -d -r" -- $curw) )
        echo ${COMPREPLY[@]} > ~/Desktop/hello.txt
    fi
}

alias configeditor=__cfe_fncConfigEditor
complete -o default -F __cfe_fncComp configeditor 


__cfe_vPythonConfigEditorScript='
import xml.etree.ElementTree as ET
import os
import sys

DEFAULT_INDENT = "\n    "
helpString=os.environ["__cfe_vHelpString"]

class EFileNotFound:
    def __init__(self, filename):
        self.file = filename

class EFileAlreadyExist(Exception):
    def __init__(self, fileName):
        self.file = fileName


def matchedLengthFromBeginning(first, second):
    minSize = min(len(first), len(second))
    matchedLength = 0
    while matchedLength < minSize:
        if first[matchedLength] != second[matchedLength]:
            break
        else: matchedLength += 1
    return matchedLength


def findBestMatchedElem(parentElem, tagName, attribute, tobeComapredValue):
    best = None
    bestMatchedLength = 0
    for elem in parentElem.findall(tagName):
        matchedLength = matchedLengthFromBeginning(elem.get(attribute), tobeComapredValue)
        if matchedLength >= bestMatchedLength:
            bestMatchedLength = matchedLength
            best = elem
    return best

def isInSameDir(path1, path2):
    return os.path.dirname(path1) == os.path.dirname(path2)

def calIndentBasedOnGivenString(string):
    if string == None:
        return DEFAULT_INDENT
    else:
        indent = string[string.rfind("\n"):]
        if indent == "":
            return DEFAULT_INDENT
        else:
            return indent

def getIndentSpaceFromPreviousElem(prevElem):
    indent = DEFAULT_INDENT
    if prevElem != None:
        indent = calIndentBasedOnGivenString(prevElem.tail)
    return indent


def insertElem(parentElem, prevElem, newElem, newl = ""):
    if prevElem != None:
        indexPrev = list(parentElem).index(prevElem)
        if indexPrev > 0:
            indent = getIndentSpaceFromPreviousElem(list(parentElem)[indexPrev - 1])
        else:
            indent = calIndentBasedOnGivenString(parentElem.text)

        newElem.tail = prevElem.tail
        prevElem.tail = newl + indent
        parentElem.insert(indexPrev + 1, newElem)
    else:
        prevElem = list(parentElem)[-1]
        if(prevElem != None):
            insertElem(parentElem, prevElem, newElem, newl)
        else: #newElem will be the first child in this case
            indent = calIndentBasedOnGivenString(parentElem.text)
            parentElem.append(newElem)
            if parentElem.text != None or parentElem.text == "":
                parentElem.text = newl + indent

def addNewElem(componentElem, tagName = "file", interestAttrib = "name", attributes={}):
    bestMatchedElem = findBestMatchedElem(componentElem, tagName, interestAttrib, attributes.get(interestAttrib))
    if bestMatchedElem != None:
        if bestMatchedElem.get(interestAttrib) == attributes.get(interestAttrib):
            raise EFileAlreadyExist(attributes.get(interestAttrib)) #Should not add if file already exist

        newl = ""
        if not isInSameDir(bestMatchedElem.get(interestAttrib), attributes.get(interestAttrib)):
            newl = "\n"

    insertElem(componentElem, bestMatchedElem, ET.Element(tagName, attributes), newl)


def fs_AddNewFile(newFilePath):
    os.system("touch {0} && git add {0}".format(newFilePath))

def fs_DeleteFile(fileName):
    os.system("""
        if [[ -f {0} ]]; then 
            git rm {0} 2&>/dev/null
            if [[ $? != 0 ]]; then
                git reset HEAD {0} 2&>/dev/null
                rm {0}
            fi
        fi
        """.format(fileName))

def fs_RenameFile(oldFilePath, newFilePath):
    os.system("""
        if [[ -f {0} ]]; then
            git mv {0} {1} 2&>/dev/null
            if [[ $? != 0 ]]; then
                git reset HEAD {0} 2&>/dev/null
                mv {0} {1}
                git add {1}
            fi
        fi
        """.format(oldFilePath, newFilePath))

def configEdit_AddNewFile(componentElem, newFilePath, filter = ""):
    interestAttrib = "name"
    tag = "file"
    attributes = {interestAttrib : newFilePath}
    if filter != "":
        attributes["variantfilter"] = filter
    addNewElem(componentElem, tag, interestAttrib, attributes)

    fs_AddNewFile(newFilePath)
    print("SUCCESFUL: Added file " + newFilePath)


def configEdit_RenameFile(componentElem, oldFilePath, newFilePath):
    willBeReAddedElem = None
    found = False
    for elem in componentElem.findall("file"):
        if elem.get("name") == oldFilePath:
            if isInSameDir(oldFilePath, newFilePath):
                elem.set("name", newFilePath)
            else:
                willBeReAddedElem = elem
            found = True
            break
    if not found:
        raise EFileNotFound(oldFilePath)

    if willBeReAddedElem != None:
        componentElem.remove(willBeReAddedElem)
        willBeReAddedElem.set("name", newFilePath)
        addNewElem(componentElem, interestAttrib="name", attributes=willBeReAddedElem.attrib)

    fs_RenameFile(oldFilePath, newFilePath)
    print("SUCCESFUL: Renamed file {0} to {1}".format(oldFilePath, newFilePath))


def configEdit_DeleteFile(componentElem, fileName):
    found = False
    for elem in componentElem.findall("file"):
        if elem.get("name") == fileName:
            componentElem.remove(elem)
            found = True
            break;
    if not found:
        raise EFileNotFound(fileName)

    fs_DeleteFile(fileName)
    print("SUCCESFUL: Deleted file " + fileName)

def separateFileListByFilter(argList = []):
    mapFileList = {} # {fileter: listFile}
    maxFilterIdx = len(argList) - 1
    startIdx = 0
    while True:
        try:
            filterFlagIdx = argList.index("-f", startIdx)
            if filterFlagIdx < maxFilterIdx:
                filters = argList[filterFlagIdx + 1]
                mapFileList[filters] = argList[startIdx : filterFlagIdx]
                startIdx = filterFlagIdx + 2
            else:
                break
        except ValueError:
            break
    if len(mapFileList) == 0:
        mapFileList[""] = argList
    return mapFileList

def configEdit_addNewFiles(componentElem, fileList = []):
    modified = False
    fileListFilterMap = separateFileListByFilter(fileList)
    for filter in fileListFilterMap:
        for f in fileListFilterMap[filter]:
            try:
                configEdit_AddNewFile(componentElem, f, filter)
                modified = True
            except EFileAlreadyExist as e:
                print("WARNING: File {0} already exists, then does not add it to config".format(e.file))
    return modified

def configEdit_DeleteFiles(componentElem, fileList = []):
    modified = False
    for f in fileList:
        try:
            configEdit_DeleteFile(componentElem, f)
            modified = True
        except EFileNotFound as e:
            print("WARNING: File {0} was not found in the config file".format(e.file))
    return modified

def configEdit_RenameFiles(componentElem, fileList = []):
    assert(len(fileList) % 2 == 0)
    i = 0
    modified = False
    while i < len(fileList):
        try:
            configEdit_RenameFile(componentElem, fileList[i], fileList[i + 1])
            modified = True
        except EFileNotFound as e:
            print("WARNING: File {0} was not found in the config file".format(e.file))
        except EFileAlreadyExist as e1:
            print("ERROR: File {0} seems to be declared multiple times in config file".format(e1.file))
        i += 2
    return modified


actions = ["-a", "-r", "-d"]
def exitHelp():
    print(helpString)
    exit(-1)
def makeSureArgsOK():
    args = sys.argv
    if len(args) < 3:
        print("Please specify enough arguments")
        exitHelp()
    if not os.path.exists(args[1]):
        print("The file {0} does not exist")
        exitHelp()
    if args[2] not in actions:
        print("Please specify correct action: ")
        actions
        exitHelp()
    if args[1] == "-r" and (len(args) < 4 or len(args) %2 == 0):
        print("with rename action must specify pair: <old,new> ... ")
        exitHelp()


if __name__ == "__main__":
    makeSureArgsOK()
    configFile = sys.argv[1]
    componentDeclarations = ET.parse(configFile).getroot()
    components = list(componentDeclarations)
    assert (len(components) == 1)
    componentElem = components[0]
    #TBD: Must provide checking for xml structures:
    actionFunc = None
    if sys.argv[2] == "-a":
        actionFunc = configEdit_addNewFiles
    elif sys.argv[2] == "-r":
        actionFunc = configEdit_RenameFiles
    elif sys.argv[2] == "-d":
        actionFunc = configEdit_DeleteFiles

    if actionFunc != None:
        if actionFunc(componentElem, sys.argv[3:]):
            print("Write config file")
            ET.ElementTree(componentDeclarations).write(configFile, encoding="utf-8", xml_declaration=True)

'