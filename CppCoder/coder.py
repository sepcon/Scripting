import xml.etree.ElementTree as ET
import os
import re
import sys
import glob
import subprocess
import shutil

# from codegenerator.CodeGentor import *
from writer.CodeWriter import *
from codedata.data import *
from codegenerator.GMockGentor import *
gbWriteConsole = False

class WorkSpace:
    def __init__(self, input, outdir):
        self.input = input
        self.outdir = outdir
        self.workingDir = os.path.join(outdir, ".tmp-mock-workspace")
        self.headers = {}
        self.namespaces = {}
        self.classes = {}
        self.parsed = False

    # def __del__(self):
    #     self.clean()

    def works(self):
        # self.createWorkspace()
        # self.launchDoxygen()
        self.parseDoxygenOutput()
        self.genCode()
        # self.clean()

    def createWorkspace(self):
        if not os.path.exists(self.outdir):
            print("{0} doesnot exist, create it".format(self.outdir))
            os.makedirs(self.outdir)
        if not os.path.exists(self.workingDir):
            os.makedirs(self.workingDir)

        self._copyToWorkspace(input)

        FileWriter(os.path.join(self.workingDir, "Doxyfile")).writeln("GENERATE_HTML=no\nGENERATE_LATEX=no\nGENERATE_XML=yes\nXML_PROGRAMLISTING=no\nFILE_PATTERNS=*.h\nXML_OUTPUT={0}/xml\nINPUT={0}".format(self.workingDir))

    def _copyToWorkspace(self, input):
        for input in self.input:
            if os.path.isfile(input):
                name = os.path.basename(input)
                shutil.copyfile(input, os.path.join(self.workingDir, name))
            elif os.path.isdir(input):
                for file in os.listdir(input):
                    self._copyToWorkspace(file)
            else:
                errorHelp(input + " is not a file a directory")

    def launchDoxygen(self):
        os.chdir(self.workingDir)
        self.runExternalCommand("doxygen",  os.path.join(self.workingDir, "Doxyfile"))

    def runExternalCommand(self, command, argsStr):
        process = subprocess.Popen([command, argsStr])
        ret = process.wait()
        return ret

    def clean(self):
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


    def genCode(self):
        codeGentor = GmockCodeGentor(self)
        for header in self.headers.values():
            header.exposeTo(codeGentor)

    def parseDoxygenOutput(self):
        self.parsed = True
        indexxmlRoot = self.getXMLDB(os.path.join(self.workingDir, "xml/index.xml"))
        for compound in indexxmlRoot.iter("compound"):
            kind = compound.get("kind")
            refid = compound.get("refid")
            if kind == "file":
                self.addHeader(refid)
            elif kind == "namespace":
                self.addNamespace(refid)
            elif kind == "class" or kind == "struct":
                cls = self.addClass(refid)
                cls.kind = kind

        self.parseCompound(self.headers)
        self.parseCompound(self.namespaces)
        self.parseCompound(self.classes)

    def parseCompound(self, compoundMap):
        for cp in compoundMap.values():
            cp.parse()

    def getXMLDB(self, refid): #refid or real path to file
        assert (self.workingDir != "")
        if refid.endswith(".xml"):
            xmldataPath = refid
        else:
            xmldataPath = os.path.join(self.workingDir, "xml/{0}.xml".format(refid))

        if not os.path.isfile(xmldataPath):
            errorHelp("{0} does not exist".format(xmldataPath))

        xmltree = ET.parse(xmldataPath)
        if xmltree == None:
            errorHelp("Error while parsing file " + xmldataPath)

        return xmltree.getroot()

    def addHeader(self, refid):
        hd = self.headers.get(refid)
        if hd == None:
            hd = Header(refid, self)
            self.headers[refid] = hd
        return hd

    def addNamespace(self, refid):
        ns = self.namespaces.get(refid)
        if ns == None:
            ns = Namespace(refid, self)
            self.namespaces[refid] = ns
        return ns

    def addClass(self, refid):
        cls = self.classes.get(refid)
        if cls == None:
            cls = Class(refid, self)
            self.classes[refid] = cls
        return cls


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

def errorHelp(msg):
    print("Error: " + msg)
    print("""Usage:
    python genmock.py   header1.h   header2.h   headerN.h   path/to/output/directory
    OR
    python genmock.py   *.h     path/to/output/directory
    """)
    exit(-1)

def checkEnviron():
    if os.system("which doxygen") != 0:
        errorHelp("cannot found doxygen in system, please install it!!")


if __name__ == "__main__":
    # checkEnviron()
    # argParser = ArgParser()
    # argParser.parse()
    # WorkSpace(argParser.input, argParser.outdir).works()

    wsp = WorkSpace(["/home/cgo1hc/Desktop/mock/hello.h"], "/home/cgo1hc/Desktop/mock1/")
    wsp.works()
