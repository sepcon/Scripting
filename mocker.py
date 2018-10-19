import xml.etree.ElementTree as ET
import os
import re
import sys

gbWriteConsole = False
gNoParamRegxPattern = re.compile("\(\s*\)")
MOCK_METHOD="MOCK_METHOD"
MOCK_CONST_METHOD="MOCK_CONST_METHOD"

class ConsoleWriter:
    def writeln(self, string = ""):
        print string

class FileWriter:
    def __init__(self, filePath):
        print "Open file " + filePath + " To write"
        self.writer = open(filePath, "w")
    def writeln(self, lines):
        if lines == "":
            return
        if not isinstance(lines, basestring):
            print "WARNING: Write value {0} to {1}".format(lines, self.writer.name)
        self.writer.write("\n{0}".format(lines))

    def __del__(self):
        self.writer.close()

class XMLElem:
    @staticmethod
    def getText(elem, tag):
        t = elem.find(tag)
        if t != None and t.text != None:
            return t.text
        else:
            return ""

class WorkspaceEventListener:
    def onWorkspaceParsingComplete(self): pass

class Mockable:
    def __init__(self): pass
    def asCpp(self): pass
    def asGmock(self): pass


class ClassMember:
    @staticmethod
    def new(xmlMemberdef):
        if xmlMemberdef.get("kind") == "variable":
            return VariableInfo(xmlMemberdef)
        elif xmlMemberdef.get("kind") == "function":
            return FunctionInfo(xmlMemberdef)
        else:
            return None

    def __init__(self, xmlMemberdef):
        self.name = xmlMemberdef.find("name").text
        self.type = XMLElem.getText(xmlMemberdef, "type")
        if self.type == "": self.type = "void"
        self.static = (xmlMemberdef.get("static") == "yes")
        self.scope = xmlMemberdef.get("prot")
        self.argsstring = XMLElem.getText(xmlMemberdef, "argsstring")
        self.definition = XMLElem.getText(xmlMemberdef, "definition")

class Function(Mockable, ClassMember):
    def __init__(self, xmlMemberdef):
        ClassMember.__init__(self, xmlMemberdef)
        self.explicit = (xmlMemberdef.get("explicit") == "yes")
        self.inline = (xmlMemberdef.get("explicit") == "yes")
        self.const = (xmlMemberdef.get("const") == "yes")
        self.virtualType = xmlMemberdef.get("virt")
        self.paramsList = self.collectParamsList(xmlMemberdef)

    def collectParamsList(self, xmlMemberdef):
        paramList = xmlMemberdef.findall("param")
        if paramList == None:
            return []
        else:
            return paramList

    def paramCount(self):
        return len(self.paramsList)

    def asCpp(self):
        if not self.static:
            return "\t" + self.type + " " + self.name + self.argsstring + "{}"
        else:
            return ""

    def asGmock(self):
        if self.static:
            return ""
        if self.name.startswith("~") or self.name.startswith("operator"):
            return ""

        if self.definition != None and self.definition != None and self.definition.startswith("static"):
            return ""

        mockMethod = ""
        lastCloseBracket = self.argsstring.rfind(")")
        if self.argsstring[lastCloseBracket:].find("const") != -1:
            mockMethod = MOCK_CONST_METHOD
        else:
            mockMethod = MOCK_METHOD

        argsstring = self.argsstring[:lastCloseBracket + 1]

        return "\t" + mockMethod + `self.paramCount()` + "(" + self.name + ", " + self.type + argsstring + ");"
    

class Variable(ClassMember, Mockable):
    def __init__(self, xmlMemberdef):
        Member.__init__(self, xmlMemberdef)

    def asGmock(self):
        return self.asCpp()

    def asCpp(self):
        return "\t{0} {1};".format(self.type, self.name)

class Referable:
    def __init__(self, refid, workspace):
        self.refid = refid
        self.workspace = workspace

    def getXMLDB(self):
        return self.workspace.getXMLDB(self.refid)

class Class(Referable):
    def __init__(self, refid):
        Referable.__init__(self, refid, workspace)
        self.compoundname = ""
        self.name = ""
        self.subclasses = []
        self.members = []
        self.type = "class"
        self.parsed = False

    def genCode(self, fileWriter):
        assert(self.parsed)
        fileWriter.writeln("\n"+ self.type + " " + self.name + "\npublic:") # Open class
        for sub in self.subclasses:
            sub.writeData(fileWriter)

        if self.isSub:
            for member in self.members:
                fileWriter.writeln(member.reformOrigin())
        else:
            for member in self.members:
                fileWriter.writeln(member.genMock())

        fileWriter.writeln("\n};") # Close class

    def parse(self):
        self.parsed = True
        root = self.getXMLDB(self.refid)
        compounddef = root.find("compounddef")
        if compounddef == None:
            return False

        if compounddef.get("kind") == "class":
            self.type = "class"
        elif compounddef.get("kind") == "struct":
            self.type = "struct"
        else:
            return False

        compoundname = compounddef.find("compoundname")
        if compoundname != None:
            self.compoundname = compoundname.text
            self.name = self.compoundname.split("::")[-1]

        for sectiondef in compoundref.iter("sectiondef"):
            if sectiondef.get("kind") == "public-func" or sectiondef.get("kind") == "public-attrib":
                for memberdef in sectiondef.iter("memberdef"):
                    self.members.append(ClassMember.new(memberdef))

        self.collectAndParseSubClass(compounddef)

    def collectAndParseSubClass(self, compounddef):
        for innerclass in compounddef.iter("innerclass"):
            self.subclasses.append(self.workspace.addClass(innerclass.get("refid")))

        for subclass in self.subclasses:
            subclass.parse()

class Namespace(Referable):
    def __init__(self, refid, workspace):
        Referable.__init__(self, refid, workspace)
        self.classes = []
        self.compoundName = ""
        self.parsed = False

    def parse(self):
        self.parsed = True
        root = self.getXMLDB()
        compounddef = root.find("compounddef")
        if compounddef == None:
            return False

        self.compoundName = compounddef.find("compoundname").text
        for innerclass in compounddef.iter("innerclass"):
            self.classes.append(self.workspace.addClass(innerclass.get("refid")))

        return True

    def genNamespaceDeclaration(self, complexNamespace):
        if complexNamespace == "":
            return ""
        return "namespace " + complexNamespace.replace("::", " {\nnamespace ") + " {\n\n\n"

    def genNamespaceClose(self):
        if self.declaration == "":
            return self.declaration

        openCount = self.declaration.count("{")
        closeExpression = ""
        i = 0
        while i < openCount:
            closeExpression += "}\n"
            i += 1
        return closeExpression

    def writeData(self, fileWriter):
        if len(self.classNodeList) == 0: #nothing to do with this kind of namespace
            return
        fileWriter.writeln(self.declaration)  # open the namespace

        for classNode in self.classNodeList:
            classNode.parse()
        #forward declaration
        if len(self.classNodeList) > 1:
            for classNode in self.classNodeList:
                fileWriter.writeln("class " + classNode.name + ";")

        fileWriter.writeln(" ")
        for classNode in self.classNodeList:
            classNode.writeData(fileWriter)
        fileWriter.writeln(self.genNamespaceClose())

class Header(Referable, WorkspaceEventListener):
    def __init__(self, refid, workspace):
        Referable.__init__(self, refid, workspace)
        self.namespaces = []
        self.classes = []
        self.includes = []
        self.originFilePath = ""
        self.parsed = False

    def onWorkspaceParsingComplete(self):
        print ""

    def genCode(self):
        if not self.parsed:
            self.parse()

    def formMockFilePath(self):
        return self.formFakeHeaderFilePath().replace(".h", "_mock.h")

    def formFakeHeaderFilePath(self):
        return "{0}/{1}".format(self.outdir, os.path.basename(self.originFilePath))

    def writeHeader(self):
        assert(self.parsed)
        headerWriter = self.createWriter(self.formFakeHeaderFilePath())
        headerWriter.writeln('#include "' + os.path.basename(self.formMockFilePath()) + '"')

    def writeMockHeader(self):
        assert (self.parsed == True)
        headerWriter = self.createWriter(self.formMockFilePath())

        # Write include guard
        headerWriter.writeln(self.createIncludeGuard(self.formMockFilePath()))
        # Write includes
        headerWriter.writeln(self.includes)
        headerWriter.writeln("\n\n\n")

        # Write namespace and namespace's classes
        for namespaceNode in self.namespaces.values():
            namespaceNode.writeData(headerWriter)

        # Write include guard close
        headerWriter.writeln("#endif\n")


    def parse(self):
        self.parsed = True
        root = WorkSpace.getXMLDB(self.refid)
        compounddef = root.find("compounddef")
        if compounddef == None or compounddef.get("kind") != "file":
            return False

        self.originFilePath = compounddef.find("location").get("file")
        self.includes = compounddef.findall("includes")
        self.collectNamespaces(compounddef)
        self.collectClasses(compounddef)

        return True


    def collectNamespaces(self, compoundref):
        for innernamespace in compoundref.iter("innernamespace"):
            self.namespaces.append(self.workspace.addNamespace(innernamespace.get("refid")))

    def collectClasses(self, compoundref):
        for innerclass in compoundref.iter("innerclass"):
            self.classes.append(self.workspace.addClass(innerclass.get("refid")))


    def getBasePath(self, classPath):
        idx = classPath.rfind("::")
        if idx == -1:
            return ""
        else:
            return classPath[:idx]

    def createIncludeGuard(self, fileName):
        includeGuard = fileName.replace(os.sep, "_")
        includeGuard = includeGuard.replace(".", "_")
        return "#ifndef " + includeGuard + "\n#define " + includeGuard + "\n"

class WorkSpace:
    __instance = None
    @staticmethod
    def instance():
        if WorkSpace.__instance == None:
            raise Exception("Workspace hasn't been initialized yet")
        else:
            return WorkSpace.__instance
    @staticmethod
    def initialize(self, inputDir, outputDir, workingDir = ""):
        WorkSpace.__instance = WorkSpace(inputDir, outputDir, workingDir)
        return WorkSpace.__instance

    def __init__(self, inputDir, outputDir, workingDir = ""):
        if WorkSpace.__instance != None:
            raise Exception("Workspace is singleton and aready instanciated")
        else:
            WorkSpace.__instance = self

        self.inputDir = inputDir
        self.outputDir = outputDir
        self.workingDir = workingDir
        if workingDir == "": self.workingDir = self.outputDir
        self.headers = {}
        self.namespaces = {}
        self.classes = {}
        self.parsed = False

    def genCode(self):
        if not self.parsed:
            self.parsed()
        #TBD

    def parse(self):
        self.parsed = True
        #TBD

    def getXMLDB(self, refid):
        assert (self.workingDir != "")
        xmldataPath = os.path.join(self.workingDirm, refid + ".xml")
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


class Mocker:
    def __init__(self, inputFile = "", outdir = ""):
        self.inputFile = inputFile
        self.outdir = outdir
        self.workingDir = outdir + "/.tmp-mock-workspace"
        self.header = None

    def __del__(self):
        self.clean()

    def works(self):
        self.createWorkspace()
        self.launchDoxygen()
        self.parseDoxygenOutput()
        self.writeData()

    def createWorkspace(self):
        if not os.path.exists(self.outdir):
            print "{0} doesnot exist, create it".format(self.outdir)
            os.makedirs(self.outdir)
        if not os.path.exists(self.workingDir):
            os.makedirs(self.workingDir)

        if os.system("cp " + self.inputFile + " " + self.workingDir) != 0:
            print("Could not write to {0}".format(self.workingDir))
            exit(1)
        else:
            os.system('echo -e "GENERATE_HTML=no\nGENERATE_LATEX=no\nGENERATE_XML=yes\nXML_PROGRAMLISTING=no\nFILE_PATTERNS=*.h\nXML_OUTPUT={0}/xml" > {0}/Doxyfile'.format(self.workingDir))

    def launchDoxygen(self):
        os.system("cd {0} && doxygen {0}/Doxyfile 2&>/dev/null".format(self.workingDir))

    def parseDoxygenOutput(self):
        xmlParserWorkingDir = self.workingDir + "/xml/"
        filelist = os.listdir(xmlParserWorkingDir)
        xmlHeaderFilePath = ""
        for file in filelist:
            if file.endswith("_8h.xml"):
                xmlHeaderFilePath = os.path.join(xmlParserWorkingDir, file)

        self.header = Header(workingDir=xmlParserWorkingDir, headerXml=xmlHeaderFilePath, outdir=self.outdir)
        self.header.parse()

    def writeData(self):
        assert(self.header != None)
        self.header.writeData()

    def clean(self):
        print "Done!"
        if self.workingDir != "":
            os.system("rm -rf " + self.workingDir + " 2>/dev/null")
            self.workingDir = ""

class ArgParser:
    def __init__(self):
        self.outdir = ""
        self.headerList = []

    def parse(self):
        if len(sys.argv) < 3:
            errorHelp("Argument missing!!")
        self.outdir = sys.argv[-1]
        self.headerList = sys.argv[1:-1]
        self.__validateHeaderList()

    def __validateHeaderList(self):
        alterList = []
        for header in self.headerList:
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

        self.headerList = alterList

def errorHelp(msg):
    print "Error: " + msg
    print """Usage:
    python genmock.py   header1.h   header2.h   headerN.h   path/to/output/directory
    """
    exit(-1)

def checkEnviron():
    if os.system("which doxygen") != 0:
        errorHelp("cannot found doxygen in system, please install it!!")




if __name__ == "__main__":
    h = Referable()
    h.getXMLDB()
    # checkEnviron()
    # argParser = ArgParser()
    # argParser.parse()
    # for header in argParser.headerList:
    #     mocker = Mocker(header, argParser.outdir)
    #     mocker.works()
