import xml.etree.ElementTree as ET
import os
import re
import sys
import glob
import subprocess
import shutil

gbWriteConsole = False
MOCK_METHOD="MOCK_METHOD"
MOCK_CONST_METHOD="MOCK_CONST_METHOD"

class CppCodeWriter:
    @staticmethod
    def new(kind, filepath):
        if kind == "file":
            return FileWriter(filepath)
        else:
            return ConsoleWriter(filepath)

    def __init__(self): self._indentLevel = 0
    def name(self): raise Exception("{0} function name has not been implemented yet".format(self))
    def _toDevice(self, formated): raise Exception("{0} function _toDevice has not been implemented yet".format(self))

    def  increaseIndentLevel(self):
        self._indentLevel += 1
    def decreaseIndentLevel(self):
        self._indentLevel -= 1

    def setIndentLevel(self, level):
        self._indentLevel = level

    def _calcIndent(self):
        return "".join(["\t" for i in range(self._indentLevel)])

    def writeln(self, string = ""):
        self._toDevice("\n")
        if self._indentLevel != 0:
            indent = self._calcIndent()
            string = indent + string.replace("\n", "\n" + indent)

        self._toDevice(string)

class ConsoleWriter(CppCodeWriter):
    def __init__(self, filePath):
        CppCodeWriter.__init__(self)
        self._name = filePath

    def name(self):
        return self._name
    def _toDevice(self, formated):
        if formated == "\n":
            return
        print(formated)

class FileWriter(CppCodeWriter):
    def __init__(self, filePath):
        CppCodeWriter.__init__(self)
        self._writer = open(filePath, "w")
    def _toDevice(self, formated):
        # if not isinstance(lines, basestring):
        #     print("WARNING: Write value {0} to {1}".format(lines, self._writer.name))
        self._writer.write(formated)
    def name(self):
        return self._writer.name

    def __del__(self):
        self._writer.close()


class XMLElem:
    @staticmethod
    def findText(elem, tag):
        t = elem.find(tag)
        if t != None and t.text != None:
            return t.text
        else:
            return ""

    @staticmethod
    def getText(elem, propName):
        prop = elem.get(propName)
        if prop != None:
            return prop
        else:
            return ""

    @staticmethod
    def findTagProp(elem, tagName, propName):
        tag = elem.find(tagName)
        if tag != None:
            prop = tag.get(propName)
            if prop != None:
                return prop
        return ""

## Visitor patterns ?? not really that
## Design approach:
## 1. Data: Collect Discoverable Data from xml database and don't need to care about how to convert it to code
##    Discoverable Data must provide functionality to expose its data to CodeGenerator via exposeTo(codeGentor CodeGenerator)
##    follows the Visitor pattern
###   IDiscoverable:
##      `-- exposeTo(codeGentor)
###
##    Header: (.h file) --> CompoundType
##         --- Members (Global functions, enums, variable)
##         `-- Namespaces
##          `- Classes
##    Namespace: --> CompoundType
##         --- Members (functions, enums, variables)
##         `-- Sub-namespaces
##          `- Inner-classes
##    Classe: --> CompoundType
##         --- Members (functions, enums, variables)
##         `-- Inner-classes
##    Member: --> MemberType
##         ---  name
##         `--  kind ( "enum", "function", "variable" ... )
##          `-- scope - visibility
##           `- parent - which CompoundType object it belongs to (class/namespace/header)
##
## 2. CodeGenerator: can provide many kinds of CodeGenerator, with the input is Discoverable Data
##     Must provide below interfaces:
###    ICodeGentor
##      `-- onFunctionExposed(function DiscoverableData)
##      `-- onVariableExposed(varialbe DiscoverableData)
##      `-- onClassExposed(class DiscoverableData)
##      `-- onNamespaceExposed(namespace DiscoverableData)
##      `-- onHeaderExposed(header DiscoverableData)
##      `-- onEnumExposed(enum DiscoverableData)

class ICodeGentor:
    def onFunctionExposed(self, f):raise Exception("{0}: function onFunctionExposed has not implemented yet".format(self))
    def onVariableExposed(self, v):raise Exception("{0}: function onVariableExposed has not implemented yet".format(self))
    def onClassExposed(self, c):raise Exception("{0}: function onClassExposed has not implemented yet".format(self))
    def onNamespaceExposed(self, ns):raise Exception("{0}: function onNamespaceExposed has not implemented yet".format(self))
    def onHeaderExposed(self, h):raise Exception("{0}: function onHeaderExposed has not implemented yet".format(self))
    def onEnumExposed(self, e):raise Exception("{0}: function onEnumExposed has not implemented yet".format(self))

class IDiscoverable:
    def exposeTo(self, codeGentor): raise Exception("{0}: Function has not implemented yet".format(self))


class GmockCodeGentor(ICodeGentor):

    def __init__(self, workspace):
        self.workspace = workspace
        self._activeHeaderWriter = None
        self._activeMockHeaderWriter = None
        self._currentHeader = None

    def onEnumExposed(self, e):
        # Write enum declaration:
        self._activeMockHeaderWriter.writeln("enum " + e.name + "\n{")
        for value in e.values:
            self._activeMockHeaderWriter.writeln("\t" + value.name + value.initializer + ",")
        self._activeMockHeaderWriter.writeln("}; // " + e.name + "\n")

    def onFunctionExposed(self, f):
        assert (isinstance(f, Function))

        if f.static:
            return

        if f.name.startswith("~") or f.name.startswith("operator"):
            return

        if f.definition != None and f.definition.startswith("static"):
            return

        # type == "" means Constructor
        if f.parent.kind == "struct" or f.type == "":
            funcBody = ";"
            if f.type == "":
                type = ""
            else:
                type = f.type + " "

            if re.match("\(.*\)\s*=", f.argsstring) == None:
                funcBody = "{}"
            self._activeMockHeaderWriter.writeln(type + f.name + f.argsstring + funcBody)
            return

        lastCloseBracket = f.argsstring.rfind(")")
        if f.argsstring[lastCloseBracket:].find("const") != -1:
            mockMethod = MOCK_CONST_METHOD
        else:
            mockMethod = MOCK_METHOD

        argsstring = f.argsstring[:lastCloseBracket + 1]

        self._activeMockHeaderWriter.writeln(
            "{0}{1}({2}, {3}{4});".format(mockMethod,
                                            f.paramCount(),
                                            f.name,
                                            f.type,
                                            argsstring))


    def onVariableExposed(self, v):
        assert (isinstance(v, Variable))
        self._activeMockHeaderWriter.writeln("{0} {1};".format(v.type, v.name))

    def onClassExposed(self, c):
        assert(isinstance(c, Class))
        classDecl = "\n"+ c.kind + " " + c.name + "\n{"

        if c.kind == "class":
            classDecl += "\npublic:"

        self._activeMockHeaderWriter.writeln(classDecl) # Open class

        self._activeMockHeaderWriter.increaseIndentLevel() # Start layouting section

        if len(c.members) > 0:
            for member in c.members: # Write enums/variables/methods
                member.exposeTo(self)
            self._activeMockHeaderWriter.writeln()
        if len(c.subclasses) > 0:
            for subCls in c.subclasses:
                subCls.exposeTo(self)
            self._activeMockHeaderWriter.writeln()

        self._activeMockHeaderWriter.decreaseIndentLevel() # End layouting section
        self._activeMockHeaderWriter.writeln("};") # Close class

    def onNamespaceExposed(self, ns):
        assert (isinstance(ns, Namespace))
        classes = ns.classes.intersection(self._currentHeader.classes)
        if len(classes) == 0:  # nothing to do with this kind of namespace
            return

        # Write namespace declaration
        self._activeMockHeaderWriter.writeln("namespace " + ns.compoundname.replace("::", " {\nnamespace ") + " {\n\n\n")  # open the namespace

        for member in ns.members: # Write enums if has
            if member.file == self._currentHeader.originFilePath:
                member.exposeTo(self)

        # forward declaration
        for cls in classes:
            self._activeMockHeaderWriter.writeln("class " + cls.name + ";")

        self._activeMockHeaderWriter.writeln(" ")


        for cls in classes:
            cls.exposeTo(self)

        self._activeMockHeaderWriter.writeln("}\t// namespace " + ns.compoundname.replace("::", "\n}\t// namespace ")) #Close the namespaces

    def onHeaderExposed(self, h):
        assert (isinstance(h, Header))
        self._currentHeader = h
        headerFilePath = "{0}/{1}".format(self.workspace.outdir, os.path.basename(h.originFilePath))
        self._activeHeaderWriter = self._createWriter(headerFilePath)
        self._activeMockHeaderWriter = self._createWriter(headerFilePath.replace(".h", "_mock.h"))

        self._codeHeader(h)
        self._codeHeaderMock(h)

    def _codeHeader(self, header):
        self._activeHeaderWriter.writeln('#include "' + os.path.basename(self._activeMockHeaderWriter.name()) + '"')

    def _codeHeaderMock(self, header):
        assert (header.parsed == True)

        # Write include guard
        self._activeMockHeaderWriter.writeln(
            "#ifndef {0}\n#define {0}\n".format(
            os.path.basename(self._activeMockHeaderWriter.name()).replace(os.sep, "_").replace(".", "_")
            ))

        # Write includes
        self._activeMockHeaderWriter.writeln(header.createIncludeSection())
        self._activeMockHeaderWriter.writeln("\n\n\n")

        for member in header.members: # Write enums if has
            member.exposeTo(self)

        # Write namespace and namespace's classes
        for ns in header.namespaces:
            ns.exposeTo(self)

        # Write classes that are not inner of any other class or namesace
        for cls in header.classes:
            if cls.isOrphan(): cls.exposeTo(self)

        # Write include guard close
        self._activeMockHeaderWriter.writeln("#endif\n")

    def _extractClassName(self, classPath):
        idx = classPath.rfind("::")
        if idx == -1:
            return ""
        else:
            return classPath[:idx]


    def _createWriter(self, path):
        print("Start writing to " + path)
        if gbWriteConsole == True:
            return CppCodeWriter.new("console", path)
        else:
            return CppCodeWriter.new("file", path)


class Member(IDiscoverable):
    @staticmethod
    def new(xmlMemberdef, parent):
        kind = xmlMemberdef.get("kind")
        if kind == "variable":
            member = Variable(xmlMemberdef, parent)
        elif kind == "function":
            member = Function(xmlMemberdef, parent)
        elif kind == "enum":
            return Enum(xmlMemberdef, parent)
        else:
            return None

        return member

    def __init__(self, xmlMemberdef, parent = None):
        self.parent = parent
        self.name = XMLElem.findText(xmlMemberdef, "name")
        self.static = (XMLElem.getText(xmlMemberdef, "static") == "yes")
        self.scope = XMLElem.getText(xmlMemberdef, "prot")
        self.file = XMLElem.findTagProp(xmlMemberdef, "location", "file")


class Enum(Member):
    class Value:
        def __init__(self, xmlElem):
            self.name = XMLElem.findText(xmlElem, "name")
            self.initializer = XMLElem.findText(xmlElem, "initializer")

    def __init__(self, xmlMemberdef, parent = None):
        Member.__init__(self, xmlMemberdef, parent)
        self.values = self._collectValues(xmlMemberdef)

    def exposeTo(self, codeGentor):
        codeGentor.onEnumExposed(self)

    def _collectValues(self, xmlMemberder):
        return [  Enum.Value(enumValueElem) for enumValueElem in xmlMemberder.iter("enumvalue")]


class HasTypeMember(Member):
    def __init__(self, xmlMemberdef, parent = None):
        Member.__init__(self, xmlMemberdef, parent)
        self.type = self._getType(xmlMemberdef)
        self.argsstring = XMLElem.findText(xmlMemberdef, "argsstring")
        self.definition = XMLElem.findText(xmlMemberdef, "definition")

    def _getType(self, xmlMemberdef):
        type = ""
        typeTag = xmlMemberdef.find("type")
        if typeTag != None:
            if typeTag.text == None:
                type = XMLElem.findText(typeTag, "ref")
            else:
                type = typeTag.text

        return type

class Function(HasTypeMember):
    def __init__(self, xmlMemberdef, parent = None):
        HasTypeMember.__init__(self, xmlMemberdef, parent)
        self.explicit = (xmlMemberdef.get("explicit") == "yes")
        self.inline = (xmlMemberdef.get("explicit") == "yes")
        self.const = (xmlMemberdef.get("const") == "yes")
        self.virtualType = xmlMemberdef.get("virt")
        self.paramsList = self.collectParamsList(xmlMemberdef)

    def exposeTo(self, codeGentor):
        codeGentor.onFunctionExposed(self)

    def collectParamsList(self, xmlMemberdef):
        paramList = xmlMemberdef.findall("param")
        if paramList == None:
            return []
        else:
            return paramList

    def paramCount(self):
        return len(self.paramsList)
    

class Variable(HasTypeMember):
    def __init__(self, xmlMemberdef, cls = None):
        HasTypeMember.__init__(self, xmlMemberdef, cls)

    def exposeTo(self, codeGentor):
        codeGentor.onVariableExposed(self)

class CompoundType:
    @staticmethod
    def new(refid, kind, workspace):
        if kind == "file":
            workspace.addHeader(Header(refid, workspace))
        elif kind == "namespace":
            workspace.addNamespace(Namespace(refid, workspace))
        elif kind == "class" or kind == "struct":
            cls = Class(refid, workspace)
            cls.kind = kind
            workspace.addClass(cls)

    def __init__(self, refid, kind, workspace):
        self.refid = refid
        self.workspace = workspace
        self.kind = kind
        self.members = []


    def getXMLDB(self):
        return self.workspace.getXMLDB(self.refid)

    def collectMembers(self, xmlCompounddef):
        for sectiondef in xmlCompounddef.iter("sectiondef"):
            if self._hasMemberIn(sectiondef):
                for memberdef in sectiondef.iter("memberdef"):
                    newMem = Member.new(memberdef, self)
                    if newMem != None:
                        self.members.append(newMem)

    def _hasMemberIn(self, xmlSectiondef):
        sectiondefKind = xmlSectiondef.get("kind")
        return sectiondefKind == "public-func" \
                    or sectiondefKind == "public-attrib" \
                    or sectiondefKind == "public-type" \
                    or sectiondefKind == "enum"

class Class(CompoundType, IDiscoverable):
    def __init__(self, refid, workspace):
        CompoundType.__init__(self, refid, "class", workspace)
        self.compoundname = ""
        self.name = ""
        self.subclasses = []
        self.parsed = False
        self.enums = []

    def isOrphan(self):
        return self.compoundname == self.name

    def exposeTo(self, codeGentor):
        codeGentor.onClassExposed(self)

    def parse(self):
        if self.parsed:
            return True
        else:
            self.parsed = True

        root = self.getXMLDB()
        compounddef = root.find("compounddef")
        if compounddef == None:
            return False

        compoundname = compounddef.find("compoundname")
        if compoundname != None:
            self.compoundname = compoundname.text
            lastOf2Colon = self.compoundname.rfind(":")
            if lastOf2Colon == -1:
                self.name = self.compoundname
            else:
                self.name = self.compoundname[lastOf2Colon + 1:]

        self.collectMembers(compounddef) # it should be enums/variables/methods
        self.collectAndParseSubClass(compounddef)

    def collectAndParseSubClass(self, compounddef):
        for innerclass in compounddef.iter("innerclass"):
            self.subclasses.append(self.workspace.addClass(innerclass.get("refid")))

        for subclass in self.subclasses:
            subclass.parse()

class Namespace(CompoundType, IDiscoverable):
    def __init__(self, refid, workspace):
        CompoundType.__init__(self, refid, "namespace", workspace)
        self.classes = set()
        self.compoundname = ""
        self.parsed = False

    def exposeTo(self, codeGentor):
        codeGentor.onNamespaceExposed(self)

    def parse(self):
        self.parsed = True
        root = self.getXMLDB()
        compounddef = root.find("compounddef")
        if compounddef == None:
            return False

        self.collectMembers(compounddef) # it should be enums
        self.compoundname = compounddef.find("compoundname").text
        for innerclass in compounddef.iter("innerclass"):
            self.classes.add(self.workspace.addClass(innerclass.get("refid")))

        return True


class Header(CompoundType):
    def __init__(self, refid, workspace):
        CompoundType.__init__(self, refid, "header", workspace)
        self.namespaces = []
        self.classes = set()
        self.includes = []
        self.originFilePath = ""
        self.parsed = False

    def exposeTo(self, codeGentor):
        codeGentor.onHeaderExposed(self)

    def parse(self):
        self.parsed = True
        root = self.getXMLDB()
        compounddef = root.find("compounddef")
        if compounddef == None or compounddef.get("kind") != "file":
            return False

        self.originFilePath = compounddef.find("location").get("file")
        self.includes = compounddef.findall("includes")

        self.collectMembers(compounddef) # it should be enums
        self.collectNamespaces(compounddef)
        self.collectClasses(compounddef)

        return True

    def hasNamespace(self, ns):
        return ns in self.namespaces

    def hasClass(self, cls):
        return cls in self.classes

    def collectNamespaces(self, compounddef):
        for innernamespace in compounddef.iter("innernamespace"):
            self.namespaces.append(self.workspace.addNamespace(innernamespace.get("refid")))

    def collectClasses(self, compounddef):
        for innerclass in compounddef.iter("innerclass"):
            self.classes.add(self.workspace.addClass(innerclass.get("refid")))

    def createIncludeSection(self):
        includeStr = ""
        for include in self.includes:
            if include.get("local") == "no":
                incOpen = '"'
                incClose = incOpen
            else:
                incOpen = "<"
                incClose = ">"
            includeStr += "\n#include {0}{1}{2}".format(incOpen, include.text, incClose)
        return includeStr

class WorkSpace:
    def __init__(self, input, outdir):
        self.input = input
        self.outdir = outdir
        self.workingDir = os.path.join(outdir, ".tmp-mock-workspace")
        self.headers = {}
        self.namespaces = {}
        self.classes = {}
        self.parsed = False

    def __del__(self):
        self.clean()

    def works(self):
        # self.createWorkspace()
        self.launchDoxygen()
        self.parseDoxygenOutput()
        self.genCode()
        self.clean()

    def createWorkspace(self):
        if not os.path.exists(self.outdir):
            print("{0} doesnot exist, create it".format(self.outdir))
            os.makedirs(self.outdir)
        if not os.path.exists(self.workingDir):
            os.makedirs(self.workingDir)

        if len(self.input) == 1:
            if os.path.isdir(self.input[0]):
                self.input[0] = os.path.join(self.input[0], "*.h")

        for input in self.input:
            name = os.path.basename(input)
            shutil.copyfile(input, os.path.join(self.workingDir, name))

        FileWriter(os.path.join(self.workingDir, "Doxyfile")).writeln("GENERATE_HTML=no\nGENERATE_LATEX=no\nGENERATE_XML=yes\nXML_PROGRAMLISTING=no\nFILE_PATTERNS=*.h\nXML_OUTPUT={0}/xml\nINPUT={0}".format(self.workingDir))

    def launchDoxygen(self):
        os.chdir(self.workingDir)
        self.runExternalCommand("doxygen",  "{0}/Doxyfile".format(self.workingDir))

    def runExternalCommand(self, command, argsStr, silient = True):
        process = subprocess.Popen([command, argsStr])
        ret = process.wait()
        if not silient and process.stdout != None:
            print(process.stdout.read())
        return ret

    def clean(self):
        print("Done!")
        # if self.workingDir != "":
        #     os.system("rm -rf " + self.workingDir + " 2>/dev/null")
        #     self.workingDir = ""

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
    checkEnviron()
    argParser = ArgParser()
    argParser.parse()
    WorkSpace(argParser.input, argParser.outdir).works()

    # wsp = WorkSpace(["/media/data/SETUP/COMMON-DATA/SOURCE_CODE/qt-creator/src/plugins/clangcodemodel/clangbackendreceiver.h"], "/home/sepcon/Desktop/doxygen")
    # wsp.works()
