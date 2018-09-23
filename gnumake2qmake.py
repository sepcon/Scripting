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

    @staticmethod
    def setDirection(to):
        if to == ContenWriter.CONSOLE_DEVICE:
            ContenWriter.__impl = ContenWriter.ConsoleWriter()
        else:
            ContenWriter.__impl = ContenWriter.FileWriter()

    @staticmethod
    def write(dir, name, content):
        if ContenWriter.__impl == None:
            Logger.info("Warning: output direction is not specified, then write to file")
            ContenWriter.__impl = ContenWriter.FileWriter
        ContenWriter.__impl.write(dir, name, content)

    # The private implementers
    __impl = None
    class ConsoleWriter:
        def write(self, dir, name, content):
            name = dir + os.sep + name + ".pro"
            Logger.verbose("START: =============== " + name + " =================")
            Logger.verbose(content)
            Logger.verbose("END: ===============" + name + ".pro=================")

    class FileWriter:
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
        self.project = None
        self.variantList = [ 'inf4cv', 'aivi', 'rnaivi', 'rnaivi2', 'aivi_tts', 'rivie']

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
        mode = self.__toGnumakeMode(self.project.args.mode)
        if not dir.endswith(mode):
            should = False
        elif dir.rfind(self.project.args.variant) == -1:
            for v in self.variantList:
                if v in dir:
                    should = False;
                    break;
        else:
            should = True
            # matches = 0
            # for v in self.variantList:
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
        if self.project == None:
            raise Exception("This chooser is not being tied to any project, please set one")

#############################################################################################################################
# /\/\/\/\/\/\/\/\/\/\/\/\/\/\/\Recursively parsing big project with multi submodules /\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\#
#############################################################################################################################
class ProjectChooserFactory:
    @staticmethod
    def createChooser(type):
        if type == "gnumake":
            return GnumakeProjectChooser()
        else:
            # With other build system, who will implement?
            return GnumakeProjectChooser()

class ProjectArguments:
    def __init__(self):
        print(sys.argv)
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
        argParser = argparse.ArgumentParser( 'python gnumake2qmake.py -o path/to/qmake-projects -vr variant path/to/dir/contains/gnumake-projects', description='\n\n\tSimply conversion from makefile to qmake file for investigating source code with qtcreator')
        argParser.add_argument('gnumakepath', help='path to directory that contains gnumake projects')
        argParser.add_argument('-o', '--outdir', default='.', help='directory for storing qmake file output')
        argParser.add_argument('-t', '--variant', default='aivi', help='project variant: rnaivi | rnaivi2 | aivi_tts | rivie')
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
    def __init__(self, projectType):
        self.args = ProjectArguments()
        Logger.initialize(self.args.verbose)
        ContenWriter.setDirection(to=self.args.outDevice)
        self.chooser = ProjectChooserFactory.createChooser(projectType)
        self.chooser.project = self

    def genQmake(self):
        treeNode = self.__formPrjTree(self.args.gnumakepath)
        if self.args.debugscript == True:
            treeNode.dumpTreeData()
        else:
            projectName = treeNode.genQmake()
            if projectName.strip() != "":
                self.__genRefreshCommand()
                Logger.info("Root Project " + projectName + " has been created!")
            else:
                Logger.info("This directory does not contain any things match with the input arguments")
                Logger.info("Nothing to do with: " + self.args.gnumakepath)

    def __formPrjTree(self, currentWorkingDir, parentNode=None):
        treeNode = None
        if self.chooser.buildable(currentWorkingDir):
            treeNode = BuildNode(self, currentWorkingDir, parentNode)
        else:
            filesInPath = os.listdir(currentWorkingDir)
            if len(filesInPath) > 0:
                subdirs = []
                for file in filesInPath:
                    absFile = os.path.join(currentWorkingDir, file)
                    if os.path.isdir(absFile):
                        subdirs.append(absFile)
                if len(subdirs) > 0:
                    treeNode = DirNode(self, currentWorkingDir, parentNode)
                    for subdir in subdirs:
                        subTree = self.__formPrjTree(subdir, treeNode)
                        if subTree != None and subTree.usable():
                            treeNode.addChild(subTree)
        return treeNode

    def __genRefreshCommand(self):
        ContenWriter.write(self.args.outdir, "refresh.sh", self.args.reformShellCommand())
        refreshPath = os.path.join(self.args.outdir, "refresh.sh")
        os.chmod(refreshPath, 0755)

class DirNode:
    def __init__(self, project, dir=".", parentNode = None):
        self.project = project
        self.childList = []
        self.dir = os.path.abspath(dir)
        self.parentNode = parentNode
        if parentNode != None:
            self.outdir = os.path.join(parentNode.outdir, self.getNodeName())
        else:
            self.outdir = project.args.outdir
        self.level = self.calculateLevel()

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

    def genQmake(self):
        prjName = ""
        self.verbose("Start parsing: " + self.getNodeName() + " ---> ")
        self.createOutDir()
        if self.hasChild():
            childPrjList = []
            for childNode in self.childList:
                if childNode == None:
                    continue
                childPrjName = childNode.genQmake()
                if childPrjName != "":
                    childPrjList.append(childNode)
            if len(childPrjList) > 0:
                prjName = self.getNodeName()
                ContenWriter.write(self.outdir, prjName + ".pro", self.createQmakeContent(childPrjList))
        self.verbose( "Parsing done: " + self.getNodeName() + " <--- ")
        if prjName != "":
            self.info("--> Project: " + prjName + " created")
        return prjName

    def createQmakeContent(self, childPrjList):
        mainContent = "SUBDIRS = "
        for child in childPrjList:
            mainContent += child.getNodeName() + " \\\n"
        return QMAKE_FILE_TEMPLATE_SUBDIRS + mainContent

    def createOutDir(self):
        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)

    def getNodeName(self):
        return FSUtill.baseName(self.dir)

    def usable(self):
        return self.hasChild()

    def hasChild(self):
        return len(self.childList) > 0

    def addChild(self, node):
        self.childList.append(node)

    def removeChild(self, node):
        try:
            self.childList.remove(node)
        except ValueError:
            self.info("There no child node: " + node)

    def calculateLevel(self):
        i = 0
        parent = self.parentNode
        while parent != None:
            i = i + 1
            parent = parent.parentNode
        return i


class BuildNode(DirNode):
    def __init__(self, project, dir=".", parentNode=None):
        DirNode.__init__(self, project, dir, parentNode)

    def usable(self):
        return True

    def genQmake(self):
        self.verbose("PARSING START: " + self.getNodeName())
        prjName = ""
        if not self.project.chooser.choose(self.dir):
            self.verbose("don't parse " + self.dir)
            prjName = ""
        else:
            parser = GnumakeParser(self)
            self.verbose("START: Parsing gnumake file...")
            parser.parse()
            qmakeContent = self.createQmakeContent(parser)
            if qmakeContent != "":
                prjName = self.getNodeName()
                ContenWriter.write(self.outdir, prjName + ".pro", qmakeContent)
            else:
                self.info(self.getNodeName() + " ----> EMPTY!!!")

        self.verbose( "PARSING DONE: " + self.getNodeName())
        if prjName != "":
            self.info(" --> Created sub project: " + prjName)
        return prjName

    def createQmakeContent(self, parser):
        if parser.hasData():
            return QMAKE_FILE_TEMPLATE_APP + \
                   QMAKE_CC + parser.cc + QMAKE_LINE_BREAKS + \
                   QMAKE_CXX + parser.cxx + QMAKE_LINE_BREAKS + \
                   QMAKE_CFLAGS + parser.cflags + QMAKE_LINE_BREAKS + \
                   QMAKE_CXXFLAGS + parser.cxxflags + QMAKE_LINE_BREAKS + \
                   QMAKE_DEBUGGER + parser.dbger + QMAKE_LINE_BREAKS + \
                   QMAKE_MACROS_DEFINE_KEYWORD + parser.defines + QMAKE_LINE_BREAKS + \
                   QMAKE_INCLUDEPATH_KEYWORD + parser.includePaths + QMAKE_LINE_BREAKS + \
                   QMAKE_SOURCE_KEYWORD + parser.cppFiles
        else:
            return ""


class GnumakeParser:
    def __init__(self, node):
        self.node = node
        self.includePaths = ""
        self.defines = ""
        self.cflags = ""
        self.cxxflags = ""
        self.cppFiles = ""
        self.cc = ""
        self.cxx = ""
        self.dbger = ""
        self.workingDir = node.dir
        self.parsed = False

    def hasData(self):
        if not self.parsed:
            raise Exception(self.workingDir + " hasn't been parsed yet!")
        return self.defines != "" or self.cflags != "" or self.cxxflags != "" or self.cppFiles != "" or self.workingDir != ""

    def setWorkingDir(self, dir):
        self.workingDir = dir

    def parse(self):
        self.parsed = True
        srclistFiles = FSUtill.getFilesByType(self.workingDir, ".srclist")
        gnumakeFiles = FSUtill.getFilesByType(self.workingDir, ".gnumake")
        for f in srclistFiles:
            self.__collectSourceFiles(f)
        for f in gnumakeFiles:
            self.__parsegnumake(f)
        self.cppFiles = self.__uniqueLinesInString(self.cppFiles)
        self.includePaths = self.__uniqueLinesInString(self.includePaths)
        self.defines = self.__uniqueLinesInString(self.defines).replace("VARIANT_S_FTR_ENABLE_TRC_GEN", "VARIANT_S_FTR_ENABLE_ETG_PRINTF")


    def __uniqueLinesInString(self, str):
        return "\n".join(list(OrderedDict.fromkeys(str.split("\n"))))

    def __collectSourceFiles(self, srcListFile):
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
            self.cppFiles += file + " \\\n"

    def __parsegnumake(self, gnumakeFile):
        self.node.verbose("PARSING START: " + gnumakeFile)

        f = open(gnumakeFile, 'r')
        lines = f.readlines(); f.close()
        # Get include paths
        self.includePaths = self.__getMatchedLine(r'^CPP_INCLUDES_.*:=', lines).replace("-I", " \\\n")
        # Get macros defines
        self.defines = self.__getMatchedLine(r'^CC_DEFINES.*:=', lines).replace("-D", " \\\n")
        # Get cflags
        self.cflags = self.__getMatchedLine(r'^C_OPTIONS_.*:=', lines)
        # Get cxxflags
        self.cxxflags = self.__getMatchedLine(r'^CPP_OPTIONS_.*:=', lines)
        # Get compilers and GDB paths
        self.__extractCompilersAndDebugger(lines)

        self.node.verbose("PARSING DONE: " + gnumakeFile)

    def __extractCompilersAndDebugger(self, lines):
        self.cc = self.__getLastWord(self.__getMatchedLine(r'CC:=', lines))
        self.cxx = self.__getLastWord(self.__getMatchedLine(r'CPP:=', lines))
        self.dbger = self.__getLastWord(self.__getMatchedLine(r'GDB:=', lines))

    def __getLastWord(self, line):
        if len(line) > 0:
            splited = line.split(" ")
            i = len(splited) - 1
            while i >= 0:
                word = splited[i].strip()
                if word != "":
                    return word
                i -= 1
        return ""

    def __getMatchedLine(self, searchPattern, lines):
        for line in lines:
            if re.search(searchPattern, line):
                return re.sub(searchPattern, "", line)
        return ""

# PROGRAM START
def main():
    project = Project("gnumake")
    project.genQmake()


if __name__ == '__main__':
    main()
