import os
import re
from copy import deepcopy
from codegentor import *
from data import *
from codewriter import *

gbWriteConsole = False

def _cmpByLineOrder(codeObj1, codeObj2):
        return codeObj1.location.line - codeObj2.location.line

class GmockCodeGentor(ICodeGentor):
    MOCK_METHOD = "MOCK_METHOD"
    MOCK_CONST_METHOD = "MOCK_CONST_METHOD"

    class _HeaderInfo:
        def __init__(self, header):
            self.setHeader(header)

        def setHeader(self, header):
            self._initializeClean()
            self.header = header

        def getGlobalMockClassName(self):
            if not hasattr(self, "_globalMockClassName"):
                self._globalMockClassName = self.header.name + "_global_mock"
            return self._globalMockClassName

        def getGlobalMockClassInstance(self):
            if not hasattr(self, "_globalMockClassInstance"):
                self._globalMockClassInstance = self.getGlobalMockClassName() + "_instance"
            return self._globalMockClassInstance


        def _initializeClean(self):
            if hasattr(self, "_globalMockClassName"): del self._globalMockClassName
            if hasattr(self, "_globalMockClassInstance"): del self._globalMockClassInstance
            self.nonClassFunctionList = []
            self.header = None



    def __init__(self, projectData, outdir):
        assert (projectData == None or isinstance(projectData, Project))
        self.projectData = projectData
        self.outdir = outdir
        self._curHeaderInfo = None
        self._activeCodeWriter = None


    def genCode(self):
        if self.projectData == None or not self.projectData.ready:
            raise Exception("Project data has not been ready yet")

        for header in self.projectData.headers.values():
            header.exposeTo(self)

    def onEnumExposed(self, e):
        assert (isinstance(e, Enum))
        # Write enum declaration:
        self._activeCodeWriter.writeln("enum " + e.name + "\n{")
        for value in e.values:
            self._activeCodeWriter.writeln("\t" + value.name + value.initializer + ",")
        self._activeCodeWriter.writeln("}; // " + e.name + "\n")

    def onFunctionExposed(self, f):
        assert (isinstance(f, Function))
        if isinstance(f.parent, Class):
            self._4f_createClassMethodMock(f)
        else:
            self._4f_createNonClassFunctionMock(f)


    def onVariableExposed(self, v):
        assert (isinstance(v, Variable))
        self._activeCodeWriter.writeln("{0} {1};".format(v.type, v.name))


    def onClassExposed(self, c):
        assert(isinstance(c, Class))
        classDecl = "\n"+ c.kind + " " + c.name + "\n{"

        if c.kind == "class":
            classDecl += "\npublic:"

        self._activeCodeWriter.writeln(classDecl) # Open class
        self._activeCodeWriter.increaseIndentLevel() # Start layouting section

        self._genCodeForCodeUnits(c.members, c.innerclasses)

        self._activeCodeWriter.decreaseIndentLevel() # End layouting section
        self._activeCodeWriter.writeln("};") # Close class


    def onNamespaceExposed(self, ns):
        assert (isinstance(ns, Namespace))
        curHeaderClasses = self._pickCodeUnitsInCurrentHeader(ns.innerclasses)
        curHeaderMembers = self._pickCodeUnitsInCurrentHeader(ns.members)

        if len(curHeaderClasses) == 0 and len(curHeaderMembers) == 0:
            return

        # Write namespace declaration
        self._activeCodeWriter.writeln("namespace " + ns.compoundname.replace("::", " {\nnamespace ") + " {\n")  # open the namespace

        # forward declaration
        for cls in curHeaderClasses:
            self._activeCodeWriter.writeln("class " + cls.name + ";")

        self._activeCodeWriter.writeln(" ")

        self._genCodeForCodeUnits(curHeaderMembers, curHeaderClasses)

        self._activeCodeWriter.writeln("}\t// namespace " + ns.compoundname.replace("::", "\n}\t// namespace ")) #Close the namespaces

    def onHeaderExposed(self, h):
        assert (isinstance(h, Header))
        self._curHeaderInfo = GmockCodeGentor._HeaderInfo(h)
        mockFilePath = os.path.join(self.outdir, os.path.basename(h.location.file))
        if h.refid != "":
            mockFilePath = mockFilePath.replace(".h", "_mock.h")
        self._activeCodeWriter = self._createWriter(mockFilePath)
        self._4h_genMockHeader()
        self._4h_genFakeHeader()
        self._4h_createGloblMockHeader()


    def _4h_genMockHeader(self):
        assert (self._curHeaderInfo.header.dataAvailable and self._activeCodeWriter != None)
        # Write include guard
        self._activeCodeWriter.writeln(
            "#ifndef {0}\n#define {0}\n".format(
                os.path.basename(self._activeCodeWriter.name()).replace(os.sep, "_").replace(".", "_")
            ))

        # Write includes
        if len(self._curHeaderInfo.header.includes) > 0:
            self._activeCodeWriter.writeln(self._curHeaderInfo.header.createIncludeSection())
            self._activeCodeWriter.writeln("\n")

        self._genCodeForCodeUnits(self._curHeaderInfo.header.members,
                                  self._curHeaderInfo.header.namespaces,
                                  [ cls for cls in self._curHeaderInfo.header.innerclasses if cls.isOrphan() ] #classes that are not in any namespace or other class
                                  )

        # Write include guard close
        self._activeCodeWriter.writeln("#endif\n")

    def _4h_genFakeHeader(self):
        if self._curHeaderInfo.header.refid != "":
            fakeWriter = self._createWriter(os.path.join(self.outdir, os.path.basename(self._curHeaderInfo.header.location.file) ) )
            if len(self._curHeaderInfo.nonClassFunctionList) > 0:
                fakeWriter.writeln('#include "{0}"'.format(self._curHeaderInfo.getGlobalMockClassName() + ".h"))
                fakeWriter.writeln('static {0} {1};'.format(self._curHeaderInfo.getGlobalMockClassName(), self._curHeaderInfo.getGlobalMockClassInstance())) #define a static global mock instance
            fakeWriter.writeln('#include "' + os.path.basename(self._activeCodeWriter.name()) + '"')


    def _4h_createGloblMockHeader(self):
        if len(self._curHeaderInfo.nonClassFunctionList) > 0:
            header = Header("") #refid must be empty for global mock header
            header.dataAvailable = True
            header.name = self._curHeaderInfo.getGlobalMockClassName()
            header.location = CodeUnit.Location(header.name + ".h")
            cls = Class()
            cls.dataAvailable = True
            cls.name = self._curHeaderInfo.getGlobalMockClassName()
            cls.compoundname = cls.name
            cls.kind = "class"
            cls.location = header.location
            for func in self._curHeaderInfo.nonClassFunctionList:
                newFunc = Function()
                newFunc.parent = cls
                newFunc.name = func.name
                newFunc.type = func.type
                newFunc.argsstring = func.argsstring
                newFunc.paramsList = func.paramsList
                newFunc.definition = func.definition
                newFunc.location = header.location
                cls.members.add(newFunc)
            header.innerclasses.add(cls)
            header.exposeTo(GmockCodeGentor(self.projectData, self.outdir))


    def _4c_ExtractClassName(self, classPath):
        idx = classPath.rfind("::")
        if idx == -1:
            return ""
        else:
            return classPath[:idx]

    def _4f_createMockMethodWithDefaultParam(self, func):
        '''With function has default parameter(s), we have to create a mock function with same name + extention mock:
        e.g: funcname: helloWorld --> helloWorld_mock
        and implement helloWorld as:
        type helloWorld(param=xxx) { hellWorld_mock(param); }
        than any assertion on helleWorld must be apply on helloWorld_mock
        '''
        assert (isinstance(func, Function))
        mockFuncName = func.name + "_mock"
        self._4f_createMockMethod(func, mockFuncName)
        self._4f_writeFuncCallsToOtherFunc(func, mockFuncName)

    def _4f_writeFuncCallsToOtherFunc(self, func, otherFuncCall):
        self._activeCodeWriter.writeln(
            "{0} {1} {2} {{ {3}({4}); }}".format(func.type, func.name, func.argsstring, otherFuncCall,
                                                 ", ".join([param.name for param in func.paramsList]))
        )

    def _4f_createMockMethod(self, func, altName = ""):
        assert (isinstance(func, Function))
        lastCloseBracket = func.argsstring.rfind(")")
        if func.argsstring[lastCloseBracket:].find("const") != -1:
            mockMethod = GmockCodeGentor.MOCK_CONST_METHOD
        else:
            mockMethod = GmockCodeGentor.MOCK_METHOD

        argsstring = ", ".join([ param.type + " " + param.name for param in func.paramsList ])
        if altName == "": altName = func.name
        self._activeCodeWriter.writeln(
            "{0}{1}({2}, {3} ({4}) );".format(mockMethod,
                                          func.paramCount(),
                                          altName,
                                          func.type,
                                          argsstring))
    
    def _4f_createClassMethodMock(self, func):
        if func.isStatic\
                or func.name.startswith("~") \
                or func.name.startswith("operator") \
                or (func.definition != None and func.definition.startswith("static")): #TBD: how to resolve static methods?? whats about singleton??
            return

        # type == "" means Constructor
        if func.isPureVirtual() or func.parent.kind == "struct" or func.type == "" :
            funcBody = ";"
            if func.type == "":
                type = ""
            else:
                type = func.type + " "

            if re.match("\(.*\)\s*=", func.argsstring) == None:
                funcBody = "{}"
            self._activeCodeWriter.writeln(type + func.name + func.argsstring + funcBody)

        else:
            if func.hasDefaultParam():
                self._4f_createMockMethodWithDefaultParam(func)
            else:
                self._4f_createMockMethod(func)

    def _4f_createNonClassFunctionMock(self, func):
        assert (isinstance(func, Function))
        self._curHeaderInfo.nonClassFunctionList.append(func)
        theCallToGlobalMockMethod = "{0}.{1}".format(self._curHeaderInfo.getGlobalMockClassInstance(), func.name)
        self._4f_writeFuncCallsToOtherFunc(func, theCallToGlobalMockMethod)


    def _pickCodeUnitsInCurrentHeader(self, codeUnitList):
        return [cobj for cobj in codeUnitList if cobj.location.file == self._curHeaderInfo.header.location.file]

    def _pickSpecificCodeUnits(self, codeUnitList, kind):
        return [ unit for unit in codeUnitList if unit.kind == kind ]


    def _genCodeForCodeUnits(self, *listOfCodeUnitList):
        '''each code object should be written to file in the same order as origin header file'''
        totalList = []
        for codeUnitList in listOfCodeUnitList:
            totalList += codeUnitList

        # sort to make sure the order is correct
        totalList.sort(key= lambda obj: obj.location.line)
        for cobj in totalList:
            cobj.exposeTo(self)

    def _createWriter(self, path):
        print("Start writing to " + path)
        if gbWriteConsole == True:
            return CppCodeWriter.new("console", path)
        else:
            return CppCodeWriter.new("file", path)
