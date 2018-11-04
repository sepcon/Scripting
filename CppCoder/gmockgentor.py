import os
import re
from codegentor import *
from data import *
from codewriter import *

gbWriteConsole = False

class CodeGenConditioner:
    '''
    This class provides base interfaces for checking that header, namespace, class, function should be mocked or not
    the condition depends on the type of project you're working on, the type of input and what are you expecting to have
    '''
    #Kinds of contitioner:
    TYPE_MockAll = 0
    TYPE_Asf = 1
    TYPE_NormalMock = 2
    TYPE_None = 3

    # which actions?
    ACT_KeepOrigin = 0        # Do nothing    e.g: '          '
    ACT_GenMock = 1           # Write as mock e.g: MOCK_METHOD0(func, void())
    ACT_DefineEmpty = 2       # Write empty definition e.g: void function() {}
    ACT_Ignore = 3

    @staticmethod
    def new(type):
        if type == CodeGenConditioner.TYPE_NormalMock: return NormalMockConditioner()
        elif type == CodeGenConditioner.TYPE_Asf: return AsfMockConditioner()
        else: return CodeGenConditioner()

    def __init__(self): self.projectData = None
    def doWhatWithHeader(self, h): return CodeGenConditioner.ACT_Ignore
    def doWhatWitClass(self, cls):return CodeGenConditioner.ACT_Ignore
    def doWhatWithNamespace(self, ns): return CodeGenConditioner.ACT_Ignore
    def doWhatWithFunction(self, f): return CodeGenConditioner.ACT_Ignore

class GmockCodeGentor(ICodeGentor):
    MOCK_METHOD = "MOCK_METHOD"
    MOCK_CONST_METHOD = "MOCK_CONST_METHOD"
    class _HeaderInfo:
        '''
        Provide the information of current working header
        '''
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
    def __init__(self, projectData, outdir, conditionerType = CodeGenConditioner.TYPE_NormalMock):
        assert (projectData == None or isinstance(projectData, Project))
        self.projectData = projectData
        self.outdir = outdir
        self._curHeaderInfo = None
        self._activeCodeWriter = None
        self.__initializeConditioner(conditionerType)

    def __initializeConditioner(self, type):
        self.conditioner = CodeGenConditioner.new(type);
        self.conditioner.projectData = self.projectData

    def genCode(self):
        if self.projectData == None or not self.projectData.ready:
            raise Exception("Project data has not been ready yet")

        for header in self.projectData.headers.values():
            header.exposeTo(self)

    def onTypeDefExposed(self, t):
        self._activeCodeWriter.writeln("typedef {0} {1};".format(t.type, t.name))

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
            self.__4f_createClassMethodMock(f)
        else:
            self.__4f_createNonClassFunctionMock(f)

    def onVariableExposed(self, v):
        assert (isinstance(v, Variable))
        self._activeCodeWriter.writeln("{0} {1};".format(v.type, v.name))

    def onClassExposed(self, c):
        assert (isinstance(c, Class))

        classDecl = "\n" + c.kind + " " + c.name + self.__4c_formInheritExpression(c) + "\n{"

        if c.kind == "class":
            classDecl += "\npublic:"

        self._activeCodeWriter.writeln(classDecl)  # Open class
        self._activeCodeWriter.increaseIndentLevel()  # Start layouting section

        self.__genCodeForCodeUnits(c.members(), c.innerclasses)

        self._activeCodeWriter.decreaseIndentLevel()  # End layouting section
        self._activeCodeWriter.writeln("};")  # Close class

    def onNamespaceExposed(self, ns):
        assert (isinstance(ns, Namespace))
        innerclasses = self.__pickCodeUnitsInCurrentHeader(ns.innerclasses)
        enums = self.__pickCodeUnitsInCurrentHeader(ns.enums)
        typedefs = self.__pickCodeUnitsInCurrentHeader(ns.typedefs)
        functions = self.__pickCodeUnitsInCurrentHeader(ns.functions)
        variables = self.__pickCodeUnitsInCurrentHeader(ns.variables)

        if len(innerclasses) == 0 and len(enums) == 0 and len(functions) == 0 and len(variables) == 0 :
            return

        # Write namespace declaration
        self._activeCodeWriter.writeln(
            "namespace " + ns.compoundname.replace("::", " {\nnamespace ") + " {\n")  # open the namespace

        # forward declaration
        for cls in innerclasses:
            self._activeCodeWriter.writeln("class " + cls.name + ";")

        self._activeCodeWriter.writeln(" ")

        # self.__genCodeForCodeUnits(curHeaderMembers, curHeaderClasses)
        self.__genCodeForCompoundNonClassTypeMembers(enums, typedefs, innerclasses, functions)

        self._activeCodeWriter.writeln(
            "}\t// namespace " + ns.compoundname.replace("::", "\n}\t// namespace "))  # Close the namespaces

    def onHeaderExposed(self, h):
        assert (isinstance(h, Header))
        self._curHeaderInfo = GmockCodeGentor._HeaderInfo(h)
        mockFilePath = os.path.join(self.outdir, os.path.basename(h.location.file))
        if h.refid != "":
            mockFilePath = mockFilePath.replace(".h", "_mock.h")
        self._activeCodeWriter = self.__createWriter(mockFilePath)
        self.__4h_genMockHeader()
        self.__4h_genFakeHeader()
        # self.__4h_createGloblMockHeader()

    def __4h_genMockHeader(self):
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

        self.__genCodeForCodeUnits(self._curHeaderInfo.header.members(),
                                  self._curHeaderInfo.header.namespaces,
                                  [cls for cls in self._curHeaderInfo.header.innerclasses if cls.isOrphan()]
                                  # classes that are not in any namespace or other class
                                  )

        # Write include guard close
        self._activeCodeWriter.writeln("\n#endif\n")

    def __4h_genFakeHeader(self):
        if self._curHeaderInfo.header.refid != "":
            fakeWriter = self.__createWriter(
                os.path.join(self.outdir, os.path.basename(self._curHeaderInfo.header.location.file)))
            if len(self._curHeaderInfo.nonClassFunctionList) > 0:
                fakeWriter.writeln('#include "{0}"'.format(self._curHeaderInfo.getGlobalMockClassName() + ".h"))
                fakeWriter.writeln('static {0} {1};'.format(self._curHeaderInfo.getGlobalMockClassName(),
                                                            self._curHeaderInfo.getGlobalMockClassInstance()))  # define a static global mock instance
            fakeWriter.writeln('#include "' + os.path.basename(self._activeCodeWriter.name()) + '"')

    def __4h_createGloblMockHeader(self):
        if len(self._curHeaderInfo.nonClassFunctionList) > 0:
            header = Header("")  # refid must be empty for global mock header
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
                newFunc.name = func.name
                newFunc.type = func.type
                newFunc.isStatic = False
                newFunc.argsstring = func.argsstring
                newFunc.paramsList = func.paramsList
                newFunc.definition = func.definition
                newFunc.location = header.location
                newFunc.setParent(cls)
            header.innerclasses.append(cls)
            header.exposeTo(GmockCodeGentor(self.projectData, self.outdir)) #Create new header for writing mock for global functions

    def __4c_formInheritExpression(self, c):
        assert (isinstance(c, Class))
        if not c.hasBase():
            return ""
        iExprList = []
        for ii in c.inheritInfo:
            if ii.isVirtual :
                iExprList.append("{0} {1} {2}".format(ii.accessibility, "virtual", self.__4c_ExtractClassName(ii.basename)))
            else:
                iExprList.append("{0} {1}".format(ii.accessibility, self.__4c_ExtractClassName(ii.basename)))

        return ": " + ", ".join(iExprList)

    def __4c_ExtractClassName(self, classPath):
        idx = classPath.rfind(":")
        if idx == -1:
            return classPath
        else:
            return classPath[:idx]

    def __4f_createMockMethodWithDefaultParam(self, func):
        '''With function has default parameter(s), we have to create a mock function with same name + extention mock:
        e.g: funcname: helloWorld --> helloWorld_mock
        and implement helloWorld as:
        type helloWorld(param=xxx) { hellWorld_mock(param); }
        than any assertion on helleWorld must be apply on helloWorld_mock
        '''
        assert (isinstance(func, Function))
        mockFuncName = func.name + "_mock"
        self.__4f_createMockMethod(func, mockFuncName)
        self._activeCodeWriter.writeln(self.__4f_createFuncThatCallsToOtherFunc(func, mockFuncName))


    def __4f_createFuncThatCallsToOtherFunc(self, func, otherFuncCall):
        return "{0} {1} {2} {{ {3}({4}); }}".format(func.type, func.name, func.argsstring, otherFuncCall,
                                                 ", ".join([ param.name for param in func.paramsList ] ))

    def __4f_createMockMethod(self, func, altName=""):
        assert (isinstance(func, Function))
        lastCloseBracket = func.argsstring.rfind(")")
        if func.argsstring[lastCloseBracket:].find("const") != -1:
            mockMethod = GmockCodeGentor.MOCK_CONST_METHOD
        else:
            mockMethod = GmockCodeGentor.MOCK_METHOD

        argsstring = ", ".join([param.type + " " + param.name for param in func.paramsList])
        if altName == "": altName = func.name
        self._activeCodeWriter.writeln(
            "{0}{1}({2}, {3} ({4}) );".format(mockMethod,
                                              func.paramCount(),
                                              altName,
                                              func.type,
                                              argsstring))

    def __4f_createClassMethodMock(self, func):
        action = self.conditioner.doWhatWithFunction(func)
        if action == CodeGenConditioner.ACT_Ignore:
            return
        elif action == CodeGenConditioner.ACT_DefineEmpty:

            self._activeCodeWriter.writeln(func.getReturnType() + func.name + func.argsstring + "{}")
        elif action == CodeGenConditioner.ACT_KeepOrigin:
            self._activeCodeWriter.writeln(func.getReturnType() + func.name + func.argsstring + ";")
        else: #action == CodeGenConditioner.ACT_GenMock
            if func.hasDefaultParam():
                self.__4f_createMockMethodWithDefaultParam(func)
            else:
                self.__4f_createMockMethod(func)

    def __4f_createNonClassFunctionMock(self, func):
        assert (isinstance(func, Function))
        # self._curHeaderInfo.nonClassFunctionList.append(func)
        theCallToGlobalMockMethod = self._curHeaderInfo.getGlobalMockClassInstance() + "." + func.name
        self._activeCodeWriter.writeln("static inline " + self.__4f_createFuncThatCallsToOtherFunc(func, theCallToGlobalMockMethod))

    def __pickCodeUnitsInCurrentHeader(self, codeUnitList):
        return [cobj for cobj in codeUnitList if cobj.location.file == self._curHeaderInfo.header.location.file]

    def __pickSpecificCodeUnits(self, codeUnitList, kind):
        return [unit for unit in codeUnitList if unit.kind == kind]

    def __genCodeForCodeUnits(self, *listOfCodeUnitList):
        '''each code object should be written to file in the same order as origin header file'''
        totalList = []
        for codeUnitList in listOfCodeUnitList:
            totalList += codeUnitList

        # sort to make sure the order is correct
        totalList.sort(key=lambda obj: obj.location.line)
        for cobj in totalList:
            cobj.exposeTo(self)

    def __genCodeForCompoundNonClassTypeMembers(self, enums, typedefs, innerclasses, functions): # namespace and header
        self.__genCodeForCodeUnits(enums)
        self.__genCodeForCodeUnits(typedefs)
        self.__genCodeForCodeUnits(innerclasses)
        self.__genMockClassForGlobalFunctions(functions)
        self.__genCodeForCodeUnits(functions)

    def __genMockClassForGlobalFunctions(self, functions):
        if len(functions) == 0:
            return
        cls = Class()
        cls.dataAvailable = True
        cls.name = self._curHeaderInfo.getGlobalMockClassName()
        cls.compoundname = cls.name
        cls.kind = "class"
        cls.location = self._curHeaderInfo.header.location
        for func in functions:
            newFunc = Function()
            newFunc.name = func.name
            newFunc.type = func.type
            newFunc.isStatic = False
            newFunc.argsstring = func.argsstring
            newFunc.paramsList = func.paramsList
            newFunc.definition = func.definition
            newFunc.location = self._curHeaderInfo.header.location
            newFunc.setParent(cls)
        cls.exposeTo(self)
        self._activeCodeWriter.writeln("static {0} {1};".format(self._curHeaderInfo.getGlobalMockClassName(), self._curHeaderInfo.getGlobalMockClassInstance()))

    def __createWriter(self, path):
        print("Start writing to " + path)
        if gbWriteConsole == True:
            return CppCodeWriter.new("console", path)
        else:
            return CppCodeWriter.new("file", path)

class NormalMockConditioner(CodeGenConditioner):
    def __init__(self): self.projectData = None
    def doWhatWithHeader(self, h): return CodeGenConditioner.ACT_GenMock
    def doWhatWitClass(self, cls): return CodeGenConditioner.ACT_GenMock
    def doWhatWithNamespace(self, ns): return CodeGenConditioner.ACT_GenMock
    def doWhatWithFunction(self, func):
        if func.isStatic \
                or func.isDestructor() \
                or func.name.startswith("operator") \
                or (func.definition != None and func.definition.startswith(
            "static")):  # TBD: how to resolve static methods?? whats about singleton??
            return CodeGenConditioner.ACT_Ignore

        # type == "" means Constructor
        funcDefinedByLanguage = re.match("\(.*\)\s*=", func.argsstring) != None and not func.isPureVirtual()
        if funcDefinedByLanguage:
            return CodeGenConditioner.ACT_KeepOrigin

        if func.parent.kind == "struct" or (not funcDefinedByLanguage and func.isConstructor()):
            return CodeGenConditioner.ACT_DefineEmpty

        return CodeGenConditioner.ACT_GenMock


class AsfMockConditioner(NormalMockConditioner): #extends NormalMockConditioner
    def __init__(self): self.projectData = None
    # def doWhatWithHeader(self, h):    #inherit from parent
    # def doWhatWithNamespace(self, ns) #inherit from parent
    def doWhatWitClass(self, cls):
        if cls.name.endswith("IF"):
            return CodeGenConditioner.ACT_KeepOrigin
    def doWhatWithFunction(self, f):
        if not isinstance(f.parent, Class) or self.doWhatWitClass(f.parent) != CodeGenConditioner.ACT_KeepOrigin:
            return NormalMockConditioner.doWhatWithFunction(self, f)
        elif f.isDestructor():
            return CodeGenConditioner.ACT_DefineEmpty
        else:
            return  CodeGenConditioner.ACT_KeepOrigin

