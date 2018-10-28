import xml.etree.ElementTree as ET
import os
import re
import sys
import glob
import subprocess
import shutil

# from codegenerator.CodeGentor import *
from environ import *
from codewriter import *
from data import *
from xmlparser import *
from gmockgentor import *

class DataParser:
    def __init__(self, workingDir):
        self.workingDir = workingDir
        self.project = Project()

    def parse(self):
        if not self.project.ready:
            raise Exception("The data hasn't been ready yet")

class WorkSpace:
    def __init__(self, input, outdir, dataType="xml", codeGentorType = "gmocker"):
        self.input = input
        self.outdir = outdir
        self.workingDir = os.path.join(outdir, ".tmp-mock-workspace")
        self.dataType = dataType
        self.codeGentorType = codeGentorType
        self.parsed = False

    # def __del__(self):
    #     self._clean()

    def works(self):
        # self._createWorkspace()
        # self._launchDoxygen()
        self._genCode(self._parseDoxygenOutput())
        # self._clean()

    def _createWorkspace(self):
        if not os.path.exists(self.outdir):
            print("{0} doesnot exist, create it".format(self.outdir))
            os.makedirs(self.outdir)
        if not os.path.exists(self.workingDir):
            os.makedirs(self.workingDir)

        self._copyToWorkspace(self.input)

        FileWriter(os.path.join(self.workingDir, "Doxyfile")).writeln("GENERATE_HTML=no\nGENERATE_LATEX=no\nGENERATE_XML=yes\nXML_PROGRAMLISTING=no\nFILE_PATTERNS=*.h\nXML_OUTPUT={0}/xml\nINPUT={0}".format(self.workingDir))

    def _copyToWorkspace(self, input):
        if isinstance(input, list):
            for i in input:
                if os.path.isfile(i):
                    self._copyToWorkspace(i)
                elif os.path.isdir(i):
                    self._copyToWorkspace(os.listdir(i))
                else:
                    print("WARNING: {0} is not a file a directory".format(i))

        elif os.path.isdir(input):
            self._copyToWorkspace(os.listdir(input))
        elif os.path.isfile(input):
            name = os.path.basename(input)
            shutil.copyfile(input, os.path.join(self.workingDir, name))
        else:
            errorHelp(input + ": don't know type of this input")


    def _launchDoxygen(self):
        os.chdir(self.workingDir)
        self._runExternalCommand("doxygen",  os.path.join(self.workingDir, "Doxyfile"))

    def _parseDoxygenOutput(self):
        dataParser = XMLParser(os.path.join(self.workingDir, "xml"))
        return dataParser.parse()

    def _genCode(self, projectData):
        codeGentor = GmockCodeGentor(projectData, self.outdir)
        codeGentor.genCode()

    def _runExternalCommand(self, command, argsStr):
        process = subprocess.Popen([command, argsStr])
        ret = process.wait()
        return ret

    def _clean(self):
        if self.workingDir != "":
            os.system("rm -rf " + self.workingDir + " 2>/dev/null")
            self.input = ""
            self.outdir = ""
            self.workingDir = ""
            self.headers = {}
            self.namespaces = {}
            self.classes = {}
            self.parsed = False
            print("Workspace cleaned!")


class ArgParser:
    def __init__(self):
        self.outdir = ""
        self.input = []

    def parse(self):
        if len(sys.argv) < 3:
            errorHelp("Argument missing!!")
        self.outdir = os.path.abspath(sys.argv[-1])
        self.input = sys.argv[1:-1]
        for i in range(len(self.input)):
            self.input[i] = os.path.abspath(self.input[i])

    def __validateHeaderList(self):
        alterList = []
        for header in self.input:
            if not os.path.exists(header):
                basename = os.path.basename(header)
                if basename.find("*") == -1:
                    continue
                headerPattern = re.compile(basename)
                for file in os.listdir(os.path.dirname(header)):
                    if headerPattern.match(file):
                        alterList.append(file)
            else:
                alterList.append(header)

        self.input = alterList


if __name__ == "__main__":
    # checkEnviron()
    # argParser = ArgParser()
    # argParser.parse()
    # WorkSpace(argParser.input, argParser.outdir).works()

    wsp = WorkSpace(["/media/data/SETUP/COMMON-DATA/SOURCE_CODE/qt-creator/src/plugins/clangcodemodel/clangeditordocumentprocessor.h"], "/home/sepcon/Documents/doxygen")
    wsp.works()
