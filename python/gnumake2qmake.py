##########################################################################################################################
# * @Author: cgo1hc
# * GNUMAKE TO QMAKE
# * Used to convert other build configurations to qmake that can be used in qt-creator
##########################################################################################################################
import os
import sys
import re
import argparse
import StringIO
import xml.etree.ElementTree as ET
from collections import OrderedDict

# Qmake constants
QMAKE_FILE_TEMPLATE_APP = 'TEMPLATE = app\nCONFIG += console \nCONFIG -= app_bundle \nCONFIG -= qt\n\n\n'
QMAKE_FILE_TEMPLATE_SUBDIRS = 'TEMPLATE = subdirs\nCONFIG += console \nCONFIG -= app_bundle \nCONFIG -= qt\n\n\n'
QMAKE_INCLUDEPATH_KEYWORD = "INCLUDEPATH += \\\n"
QMAKE_MACROS_DEFINE_KEYWORD = "DEFINES += \\\n"
QMAKE_CXXFLAGS = "QMAKE_CXXFLAGS = "
QMAKE_CFLAGS = "QMAKE_CFLAGS = "
QMAKE_CC = "QMAKE_CC = "
QMAKE_CXX = "QMAKE_CXX = "
QMAKE_DEBUGGER = "# QMAKE_DEBUGGER = "
QMAKE_SOURCE_KEYWORD = "SOURCES += \\\n"
QMAKE_LINE_BREAKS = "\n\n"


class FSUtill:
    @staticmethod
    def baseName(dir):
        dir = dir.strip(os.sep)
        idx = dir.rfind(os.sep)
        if idx == -1:
            return dir.strip()
        else:
            return dir[idx + 1:].strip()

    @staticmethod
    def getFilesByType(dir, type):
        fileList = os.listdir(dir)
        foundList = []
        for file in fileList:
            if file.endswith(type):
                foundList.append(os.path.join(dir, file))
        return foundList

class Logger:
    __enableVerbose = False
    @staticmethod
    def initialize(enableVerbose):
        Logger.__enableVerbose = enableVerbose

    @staticmethod
    def info(message, indentLevel = 0):
        tabs = ""
        i = 0
        while i < indentLevel:
            i += 1
            tabs += '\t'
        print tabs + message

    @staticmethod
    def verbose(message, indentLevel = 0):
        if Logger.__enableVerbose:
            Logger.info(message, indentLevel)

    @staticmethod
    def error(message):
        sys.stderr.writelines(message)


class ContenWriter:
    CONSOLE_DEVICE=1
    FILE_DEVICE=2
    __impl = None

    @staticmethod
    def redirect(to):
        if to == ContenWriter.CONSOLE_DEVICE:
            ContenWriter.__impl = ContenWriter.__ConsoleWriter()
        else:
            ContenWriter.__impl = ContenWriter.__FileWriter()

    @staticmethod
    def write(dir, name, content):
        if ContenWriter.__impl == None:
            Logger.info("Warning: output direction is not specified, then write to file")
            ContenWriter.__impl = ContenWriter.__FileWriter
        ContenWriter.__impl.write(dir, name, content)


    class __ConsoleWriter:
        def write(self, dir, name, content):
            name = os.path.join(dir, name + ".pro")
            Logger.verbose("START: =============== " + name + " =================")
            Logger.verbose(content)
            Logger.verbose("END: ===============" + name + ".pro=================")

    class __FileWriter:
        def write(self, dir, name, content):
            if not os.path.exists(dir):
                os.makedirs(dir)
            filepath = os.path.join(dir, name)
            f = open(filepath, 'w')
            f.write(content)
            f.close()
            Logger.verbose("write to " + filepath + " finished")

class GnumakeProjectChooser:
    def __init__(self):
        self.__variantList = [ 'inf4cv', 'aivi', 'rnaivi', 'rnaivi2', 'aivi_tts', 'rivie']
        self._selectedBuildMode = self.__toGnumakeMode(Project.Instance().args.mode)

    # buildable when dir contains gnumake file
    def buildable(self, dir):
        self.__complainNullProject()
        if len(FSUtill.getFilesByType(dir, ".gnumake")) > 0:
            return True;
        else:
            Logger.verbose("--> Not a buildable directory: " + dir)
            return False;

    # Choose this dir when the dir satisfies variant and mode
    def choose(self, dir):
        return self.__shouldParse(dir)

    def __shouldParse(self, dir):
        self.__complainNullProject()
        should = True
        if not dir.endswith(self._selectedBuildMode):
            should = False
        elif dir.rfind(Project.Instance().args.variant) == -1:
            for v in self.__variantList:
                if v in dir:
                    should = False;
                    break;
        else:
            should = True
            # matches = 0
            # for v in self.__variantList:
            #     if v in dir:
            #         matches += 1
            #         if matches > 1:
            #             should = False
            #             break

        return should

    def __toGnumakeMode(self, mode):
        if mode == "release":
            return "_r"
        else:
            return "_d"

    def __complainNullProject(self):
        if Project.Instance() == None:
            raise Exception("This chooser is not being tied to any project, please set one")

#############################################################################################################################
# /\/\/\/\/\/\/\/\/\/\/\/\/\/\/\Recursively parsing big project with multi submodules /\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\#
#############################################################################################################################
class ProjectChooserFactory:
    @staticmethod
    def create(type):
        if type == "gnumake":
            return GnumakeProjectChooser()
        else:
            # TBD: With other build system, who will implement?
            return GnumakeProjectChooser()

class ParserFactory:
    @staticmethod
    def create(type):
        if type == "gnumake":
            return GnumakeParser()
        else:
            return None

class CodeGenerator:
    @staticmethod
    def create(type):
        if type == "qmake":
            return QmakeGenerator()
        else:
            return  None

    def genTarget(self):
        raise Exception("The function has not been overriden by derived class yet")


class ProjectArguments:
    def __init__(self):
        self.gnumakepath = "T:\\views\\AI_SDS_18.0V17_GEN\\ai_sds\\generated\\build\\gen3armmake\\sds"  # \\asf_cmake\\asf_cmake_a_d"Z:\\views\\nincg3_GEN\\ai_projects\\generated\\build\\gen3armmake\\apphmi_asf_applications\\apphmi_sds-cgi3-rnaivi_out_d" #
        self.outdir = "C:\\Users\\cgo1hc\\Desktop\\qmakeprojects"
        self.variant = "aivi"
        self.mode = "debug"
        self.verbose = False
        self.outDevice = ContenWriter.FILE_DEVICE
        self.debugscript = False
        if os.name != "nt":
            self.parseArgs()

    def __setOutDevice(self, type):
        if type == "file":
            self.outDevice = ContenWriter.FILE_DEVICE
        else:
            self.outDevice = ContenWriter.CONSOLE_DEVICE

    def parseArgs(self):
        argParser = argparse.ArgumentParser( 'python gnumake2qmake.py -o path/to/qmake-projects --variant=VARIANT path/to/dir/contains/gnumake-projects',
                                             description='\n\n\tSimply conversion from makefile to qmake file for investigating source code with qtcreator')
        argParser.add_argument('gnumakepath', help='path to directory that contains gnumake projects')
        argParser.add_argument('-o', '--outdir', default='.', help='directory for storing qmake file output')
        argParser.add_argument('-t', '--variant', help='project variant: rnaivi | rnaivi2 | aivi_tts | rivie')
        argParser.add_argument('-v', "--verbose", help='print all message as details', action='store_true')
        argParser.add_argument('-m', "--mode", default='release', help='release | debug')
        argParser.add_argument('-d', "--outdevice", default='file', help='write output to file or console, default is write to file. i.e: -o console|file')
        argParser.add_argument('-b', "--debug", help='print parsed tree structure, using this option only for debugging the script', action='store_true')
        args = argParser.parse_args()
        self.gnumakepath = args.gnumakepath
        self.outdir = args.outdir
        self.variant = args.variant
        self.verbose = args.verbose
        self.__setOutDevice(args.outdevice)
        self.debugscript = args.debug
        self.mode = args.mode

    def reformShellCommand(self):
        vbReplacement = ""
        dbReplacement = ""
        odReplacement = "file"
        if self.verbose == True:
            vbReplacement = "-v"
        if self.debugscript == True:
            dbReplacement = "-db"
        if self.outDevice == ContenWriter.FILE_DEVICE:
            odReplacement = "file"
        else:
            odReplacement = "console"

        return 'python {0} -o {1} -t {2} -m {3} -d {4} {5} {6} {7}'. \
            format(os.path.abspath(sys.argv[0]), os.path.abspath(self.outdir), self.variant, self.mode,
                   odReplacement, os.path.abspath(self.gnumakepath),
                   dbReplacement, vbReplacement)

class Project:
    __instance = None
    @staticmethod
    def Instance():
        if Project.__instance == None:
            raise Exception("Please invoke Project.Init(srcType, destType) first")
        else:
            return Project.__instance

    @staticmethod
    def Init():
        Project.__instance = Project()
        # TBD: srcType and destType must be specified vi commandline arguments when you want to extend the script to parse from other kinds of workspace and generate other kinds of workspace
        # like cmake or build database ...
        srcType = "gnumake"
        destType = "qmake"
        Logger.initialize(Project.__instance.args.verbose)
        ContenWriter.redirect(to=Project.__instance.args.outDevice)
        Project.__instance.chooser = ProjectChooserFactory.create(srcType)
        Project.__instance.generator = CodeGenerator.create(destType)
        Project.__instance.parser = ParserFactory.create(srcType)
        return Project.__instance

    def __init__(self):
        if(Project.__instance != None):
            raise Exception("Cannot create multiple instance of Project class, please use Project.instance")
        self.args = ProjectArguments()



    def genTarget(self):
        treeNode = self.__formPrjTree(self.args.gnumakepath)
        if self.args.debugscript == True:
            treeNode.dumpTreeData()
        else:
            self.parser.setNode(treeNode).parse()
            projectName = self.generator.setNode(treeNode).genTarget() # projectName will be the root project in case of multiple sub-projects
            if projectName.strip() != "":
                self.__generateUtilsScripts()
                Logger.info("Root Project " + projectName + " has been created!")
            else:
                Logger.info("This directory does not contain any things match with the input arguments")
                Logger.info("Nothing to do with: " + self.args.gnumakepath)

    def __formPrjTree(self, currentWorkingDir, parentNode=None):
        treeNode = None
        if self.chooser.buildable(currentWorkingDir):
            treeNode = BuildNode(currentWorkingDir, parentNode)
        else:
            filesInPath = os.listdir(currentWorkingDir)
            if len(filesInPath) > 0:
                subdirs = []
                for file in filesInPath:
                    absFile = os.path.join(currentWorkingDir, file)
                    if os.path.isdir(absFile):
                        subdirs.append(absFile)
                if len(subdirs) > 0:
                    treeNode = DirNode(currentWorkingDir, parentNode)
                    for subdir in subdirs:
                        subTree = self.__formPrjTree(subdir, treeNode)
                        if subTree != None and subTree.usable():
                            treeNode.addChild(subTree)
        return treeNode

    def __generateUtilsScripts(self):
        self.__generateRefreshScript()

    def __generateRefreshScript(self):
        script="refresh.sh"
        Logger.info("Write script for sync between source project vs target project: " + script)
        ContenWriter.write(self.args.outdir, script, self.args.reformShellCommand())
        refreshPath = os.path.join(self.args.outdir, script)
        os.chmod(refreshPath, 0755)


class DirNode:
    def __init__(self, dir=".", parentNode = None):
        self.childList = []
        self.dir = os.path.abspath(dir)
        self.parentNode = parentNode
        if parentNode != None:
            self.outdir = os.path.join(parentNode.outdir, self.getNodeName())
        else:
            self.outdir = Project.Instance().args.outdir
        self.level = self.__calculateLevel()

    def info(self, message):
        Logger.info(message, self.level)

    def verbose(self, info):
        Logger.verbose(info, self.level)

    def dumpTreeData(self):
        if self.hasChild():
            self.info(self.getNodeName() + " ---> D")
            for child in self.childList:
                if child != None:
                    child.dumpTreeData()
            self.info(self.getNodeName() + " <--- D")
        else:
            self.info(self.getNodeName() + " -- B")

    def createOutDir(self):
        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)

    def getNodeName(self):
        return FSUtill.baseName(self.dir)

    def hasChild(self):
        return len(self.childList) > 0

    def addChild(self, node):
        self.childList.append(node)

    def removeChild(self, node):
        try:
            self.childList.remove(node)
        except ValueError:
            self.info("There no child node: " + node)

    def __calculateLevel(self):
        # i = 0
        # parent = self.parentNode
        # while parent != None:
        #     i = i + 1
        #     parent = parent.parentNode
        # return i
        if self.parentNode == None:
            return 0
        else:
            return self.parentNode.level + 1

    def usable(self):
        return self.hasChild()

class BuildNode(DirNode):
    def __init__(self, dir=".", parentNode=None):
        DirNode.__init__(self, dir, parentNode)
        self.includePaths = ""
        self.defines = ""
        self.cflags = ""
        self.cxxflags = ""
        self.cppFiles = ""
        self.cc = ""
        self.cxx = ""
        self.dbger = ""
        self.parsed = False

    def usable(self):
        return True

class QmakeGenerator(CodeGenerator):
    def __init__(self):
        self.__rootNode = None

    def setNode(self, rootNode):
        self.__rootNode = rootNode
        return self

    def genTarget(self):
        assert(self.__rootNode)
        ret = QmakeGenerator.createGentor(self.__rootNode).genTarget()
        if ret:
            self.__genGuruScript()
        return ret

    def __genGuruScript(self):
        scriptName = "findProjectOf.sh"
        Logger.info("Generate script for finding projects that contain input filename: " + scriptName)
        command = """
            #!/bin/bash
            searchFile=$1
            [[ -z $searchFile ]] && echo 'Please specify a file name' && exit
            grep $searchFile -ril --include=*.pro {0}
        """.format(Project.Instance().args.outdir)
        ContenWriter.write(Project.Instance().args.outdir, scriptName, command)
        os.chmod(os.path.join(Project.Instance().args.outdir, scriptName), 0755)

    @staticmethod
    def createGentor(node):
        if isinstance(node, BuildNode):
            return QmakeGenerator.__BuildNodeGentor().setNode(node)
        else:
            return QmakeGenerator.__DirNodeGentor().setNode(node)

    class __DirNodeGentor:
        def __init__(self):
            self.__node = None

        def setNode(self, node):
            assert (isinstance(node, DirNode))
            self.__node = node
            return self

        def genTarget(self):
            prjName = ""
            self.__node.verbose("Start parsing: " + self.__node.getNodeName() + " ---> ")
            self.__node.createOutDir()
            if self.__node.hasChild():
                childPrjList = [] #The node which is able to generate target will be call prjNode
                for childNode in self.__node.childList:
                    if childNode == None:
                        continue
                    childPrjName = QmakeGenerator.createGentor(childNode).genTarget()
                    if childPrjName != "":
                        childPrjList.append(childNode)
                if len(childPrjList) > 0:
                    prjName = self.__node.getNodeName()
                    ContenWriter.write(self.__node.outdir, prjName + ".pro", self.createQmakeContent(childPrjList))

            self.__node.verbose("Parsing done: " + self.__node.getNodeName() + " <--- ")
            if prjName != "":
                self.__node.info("--> Project: " + prjName + " created")
            return prjName

        def createQmakeContent(self, childPrjList):
            mainContent = "SUBDIRS = "
            for child in childPrjList:
                mainContent += child.getNodeName() + " \\\n"
            return QMAKE_FILE_TEMPLATE_SUBDIRS + mainContent

    class __BuildNodeGentor:
        def __init__(self):
            self.__node = None

        def setNode(self, node):
            assert (isinstance(node, BuildNode))
            self.__node = node
            return self

        def genTarget(self):
            self.__node.verbose("PARSING START: " + self.__node.getNodeName())
            prjName = ""
            if not Project.Instance().chooser.choose(self.__node.dir):
                self.__node.verbose("don't parse " + self.__node.dir)
                prjName = ""
            else:
                self.__node.verbose("START: Parsing gnumake file...")
                qmakeContent = self.createQmakeContent()
                if qmakeContent != "":
                    prjName = self.__node.getNodeName()
                    ContenWriter.write(self.__node.outdir, prjName + ".pro", qmakeContent)
                else:
                    self.__node.info(self.__node.getNodeName() + " ----> EMPTY!!!")

            self.__node.verbose("PARSING DONE: " + self.__node.getNodeName())
            if prjName != "": self.__node.info(" --> Created sub project: " + prjName)

            return prjName

        @staticmethod
        def hasData(node):
            if not node.parsed:
                raise Exception(node.dir + " hasn't been parsed yet!")
            return node.defines != "" or node.cflags != "" or node.cxxflags != "" or node.cppFiles != "" or node.workingDir != ""

        def createQmakeContent(self):
            if self.hasData(self.__node):
                return QMAKE_FILE_TEMPLATE_APP + \
                       QMAKE_CC + self.__node.cc + QMAKE_LINE_BREAKS + \
                       QMAKE_CXX + self.__node.cxx + QMAKE_LINE_BREAKS + \
                       QMAKE_CFLAGS + self.__node.cflags + QMAKE_LINE_BREAKS + \
                       QMAKE_CXXFLAGS + self.__node.cxxflags + QMAKE_LINE_BREAKS + \
                       QMAKE_DEBUGGER + self.__node.dbger + QMAKE_LINE_BREAKS + \
                       QMAKE_MACROS_DEFINE_KEYWORD + self.__node.defines + QMAKE_LINE_BREAKS + \
                       QMAKE_INCLUDEPATH_KEYWORD + self.__node.includePaths + QMAKE_LINE_BREAKS + \
                       QMAKE_SOURCE_KEYWORD + self.__node.cppFiles
            else:
                return ""

class GnumakeParser:
    def __init__(self):
        self.__rootNode = None

    def setNode(self, node):
        self.__rootNode = node
        return self

    def parse(self):
        GnumakeParser.parseNode(self.__rootNode)

    @staticmethod
    def parseNode(node):
        node.parsed = True
        if isinstance(node, BuildNode):
            srclistFiles = FSUtill.getFilesByType(node.dir, ".srclist")
            gnumakeFiles = FSUtill.getFilesByType(node.dir, ".gnumake")
            for f in srclistFiles:
                GnumakeParser.__collectSourceFiles(node, f)
            for f in gnumakeFiles:
                GnumakeParser.__parsegnumake(node, f)

            node.cppFiles = GnumakeParser.__uniqueLinesInString(node.cppFiles)
            node.includePaths = GnumakeParser.__uniqueLinesInString(node.includePaths)
            node.defines = GnumakeParser.__uniqueLinesInString(node.defines).replace("VARIANT_S_FTR_ENABLE_TRC_GEN", "VARIANT_S_FTR_ENABLE_ETG_PRINTF")
        elif isinstance(node, DirNode) and node.hasChild():
                for childNode in node.childList:
                    GnumakeParser.parseNode(childNode)


    @staticmethod
    def __uniqueLinesInString(str):
        return "\n".join(list(OrderedDict.fromkeys(str.split("\n"))))

    @staticmethod
    def __collectSourceFiles(node, srcListFile):
        srcFileList = []
        noHeader = True
        f = open(srcListFile, 'r')
        lines = f.readlines(); f.close()
        for line in lines:
            srcFileList.append(line[:-1])
            if noHeader and line.endswith(".h"):
                noHeader = False

        # Collect header files
        if noHeader:
            folderSet = set()
            for line in srcFileList:
                folderSet.add(os.path.dirname(line))
            for folder in folderSet:
                if not os.path.exists(folder):
                    continue
                for file in os.listdir(folder):
                    if file.endswith(".h"):
                        srcFileList.append(os.path.join(folder, file))

        for file in srcFileList:
            node.cppFiles += file + " \\\n"

    @staticmethod
    def __parsegnumake(node, gnumakeFile):
        node.verbose("PARSING START: " + gnumakeFile)
        f = open(gnumakeFile, 'r')
        lines = f.readlines();
        f.close()

        # Get include paths
        node.includePaths = GnumakeParser.__getMatchedLine(r'^CPP_INCLUDES_.*:=', lines).replace("-I", " \\\n")
        # Get macros defines
        node.defines = GnumakeParser.__getMatchedLine(r'^CC_DEFINES.*:=', lines).replace("-D", " \\\n")
        # Get cflags
        node.cflags = GnumakeParser.__getMatchedLine(r'^C_OPTIONS_.*:=', lines)
        # Get cxxflags
        node.cxxflags = GnumakeParser.__getMatchedLine(r'^CPP_OPTIONS_.*:=', lines)
        # Get c compiler path
        node.cc = GnumakeParser.__getLastWord(GnumakeParser.__getMatchedLine(r'CC:=', lines))
        # Get c++ compiler path
        node.cxx = GnumakeParser.__getLastWord(GnumakeParser.__getMatchedLine(r'CPP:=', lines))
        # Get debugger path
        node.dbger = GnumakeParser.__getLastWord(GnumakeParser.__getMatchedLine(r'GDB:=', lines))

        node.verbose("PARSING DONE: " + gnumakeFile)


    @staticmethod
    def __getLastWord(line):
        if len(line) > 0:
            splited = line.split(" ")
            i = len(splited) - 1
            while i >= 0:
                word = splited[i].strip()
                if word != "":
                    return word
                i -= 1
        return ""

    @staticmethod
    def __getMatchedLine( searchPattern, lines):
        for line in lines:
            if re.search(searchPattern, line):
                return re.sub(searchPattern, "", line)
        return ""

# PROGRAM START
def program_start():
    Project.Init().genTarget()


if __name__ == '__main__':
    program_start()
