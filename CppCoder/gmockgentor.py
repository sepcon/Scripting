import os
import re
from codegentor import *
from data import *
from codewriter import *

gbWriteConsole = False

def _cmpByLineOrder(codeObj1, codeObj2):
        return codeObj1.location.line - codeObj2.location.line

class GmockCodeGentor(ICodeGentor):
    MOCK_METHOD = "MOCK_METHOD"
    MOCK_CONST_METHOD = "MOCK_CONST_METHOD"

    def __init__(self, projectData, outdir):
        assert (projectData == None or isinstance(projectData, Project))
        self.projectData = projectData
        self.outdir = outdir
        self._activeHeaderWriter = None
        self._activeMockHeaderWriter = None
        self._currentHeader = None

    def genCode(self):
        if self.projectData == None or not self.projectData.ready:
            raise Exception("Project data has not been ready yet")

        for header in self.projectData.headers.values():
            header.exposeTo(self)

    def onEnumExposed(self, e):
        assert (isinstance(e, Enum))
        # Write enum declaration:
        self._activeMockHeaderWriter.writeln("enum " + e.name + "\n{")
        for value in e.values:
            self._activeMockHeaderWriter.writeln("\t" + value.name + value.initializer + ",")
        self._activeMockHeaderWriter.writeln("}; // " + e.name + "\n")

    def onFunctionExposed(self, f):
        assert (isinstance(f, Function))

        if f.isStatic:
            return

        if f.name.startswith("~") or f.name.startswith("operator"):
            return

        if f.definition != None and f.definition.startswith("static"):
            return

        # type == "" means Constructor
        if f.isPureVirtual() or f.parent.kind == "struct" or f.type == "" :
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
            mockMethod = GmockCodeGentor.MOCK_CONST_METHOD
        else:
            mockMethod = GmockCodeGentor.MOCK_METHOD

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

        self._genCodeForCodeObjects(c.members, c.innerclasses)

        self._activeMockHeaderWriter.decreaseIndentLevel() # End layouting section
        self._activeMockHeaderWriter.writeln("};") # Close class

    def _pickOnesInCurrentHeader(self, codeObjectList):
        ret = []
        for cobj in codeObjectList:
            if cobj.location.file == self._currentHeader.location.file:
                ret.append(cobj)
        return ret

    def onNamespaceExposed(self, ns):
        assert (isinstance(ns, Namespace))
        curHeaderClasses = self._pickOnesInCurrentHeader(ns.innerclasses)
        curHeaderMembers = self._pickOnesInCurrentHeader(ns.members)

        if len(curHeaderClasses) == 0 and len(curHeaderMembers) == 0:
            return

        # Write namespace declaration
        self._activeMockHeaderWriter.writeln("namespace " + ns.compoundname.replace("::", " {\nnamespace ") + " {\n\n\n")  # open the namespace

        # forward declaration
        for cls in curHeaderClasses:
            self._activeMockHeaderWriter.writeln("class " + cls.name + ";")

        self._activeMockHeaderWriter.writeln(" ")

        self._genCodeForCodeObjects(curHeaderMembers, curHeaderClasses)

        self._activeMockHeaderWriter.writeln("}\t// namespace " + ns.compoundname.replace("::", "\n}\t// namespace ")) #Close the namespaces

    def onHeaderExposed(self, h):
        assert (isinstance(h, Header))
        self._currentHeader = h
        headerFilePath = os.path.join(self.outdir, os.path.basename(h.location.file))
        self._activeHeaderWriter = self._createWriter(headerFilePath)
        self._activeMockHeaderWriter = self._createWriter(headerFilePath.replace(".h", "_mock.h"))

        self._codeHeader(h)
        self._codeHeaderMock(h)

    def _codeHeader(self, header):
        self._activeHeaderWriter.writeln('#include "' + os.path.basename(self._activeMockHeaderWriter.name()) + '"')

    def _codeHeaderMock(self, header):
        assert(header.dataAvailable)
        # Write include guard
        self._activeMockHeaderWriter.writeln(
            "#ifndef {0}\n#define {0}\n".format(
            os.path.basename(self._activeMockHeaderWriter.name()).replace(os.sep, "_").replace(".", "_")
            ))

        # Write includes
        self._activeMockHeaderWriter.writeln(header.createIncludeSection())
        self._activeMockHeaderWriter.writeln("\n\n\n")
        orphanClasses = []
        for cls in header.innerclasses:
            if cls.isOrphan() : orphanClasses.append(cls)

        self._genCodeForCodeObjects(header.members, header.namespaces, orphanClasses)

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

    def _genCodeForCodeObjects(self, *listOfCodeObjectList):
        '''each code object should be written to file in the same order as origin header file'''
        totalList = []
        for codeObjectList in listOfCodeObjectList:
            totalList += codeObjectList

        # sort to make sure the order is correct
        totalList.sort(key= lambda obj: obj.location.line)
        for cobj in totalList:
            cobj.exposeTo(self)

