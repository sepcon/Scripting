import xmlutil

class CodeUnit:
    class Location:
        def __init__(self, file = "", line = ""):
            self.file = file
            self.line = line

    def __init__(self):
        self.kind = ""
        self.name = ""
        self.location = CodeUnit.Location()
        self.parent = None
    def setParent(self, parent):
        self.parent = parent

    def exposeTo(self, codeGentor): raise Exception("{0}: Function has not implemented yet".format(self))

class Member(CodeUnit):
    def __init__(self):
        CodeUnit.__init__(self)
        self.isStatic = False
        self.scope = "" #public/private/protected

class HasTypeMember(Member):
    def __init__(self):
        Member.__init__(self)
        self.type = ""
        self.argsstring = ""
        self.definition = ""
class TypeDef(HasTypeMember):
    def __init__(self): HasTypeMember.__init__(self)
    def exposeTo(self, codeGentor):
        codeGentor.onTypeDefExposed(self)
    def setParent(self, parent):
        self.parent = parent
        parent.typedefs.append(self)

class Function(HasTypeMember):
    class Parameter:
        def __init__(self, type = "", name = "", defval = ""):
            self.type = type
            self.name = name
            self.defval = defval

    def __init__(self):
        HasTypeMember.__init__(self)
        self.explicit = False
        self.inline = False
        self.const =  False
        self.virtualType = ""
        self.paramsList =  []

    # def __copy__(self):
    #     _cp = type(self)()
    #

    def setParent(self, compound):
        compound.adoptFunction(self)

    def exposeTo(self, codeGentor):
        codeGentor.onFunctionExposed(self)


    def paramCount(self):
        return len(self.paramsList)

    def isPureVirtual(self):
        return self.virtualType == "pure-virtual"

    def hasDefaultParam(self):
        i = -1
        while(i >= -len(self.paramsList)):
            if self.paramsList[i].defval != "":
                return True
            i -= 1
        return False
    def isConstructor(self):
        return isinstance(self.parent, Class) and self.name == self.parent.name
    def isDestructor(self):
        return isinstance(self.parent, Class) and self.name.find("~") != -1
    def getReturnType(self):
        if self.virtualType != "non-virtual":
            return "virtual " + self.type
        else:
            return self.type

class Variable(HasTypeMember):
    def __init__(self):
        HasTypeMember.__init__(self)


    def setParent(self, compound):
        compound.adoptVariable(self)

    def exposeTo(self, codeGentor):
        codeGentor.onVariableExposed(self)

class Enum(Member):
    class Value:
        def __init__(self, name = "", initializer = ""):
            self.name = name
            self.initializer = initializer

    def __init__(self):
        Member.__init__(self)
        self.values = []

    def setParent(self, compound):
        compound.adoptEnum(self)

    def exposeTo(self, codeGentor):
        codeGentor.onEnumExposed(self)

class CompoundType(CodeUnit):
    def __init__(self, refid):
        CodeUnit.__init__(self)
        self.refid = refid
        self.compoundname = ""
        self.dataAvailable = False
        self.typedefs = []
        self.enums = []
        self.variables = []
        self.functions = []
        self.innerclasses = []

    def adoptTypeDef(self, t):
        t.parent = self
        self.typedefs.append(t)
    def adoptEnum(self, e):
        e.parent = self
        self.enums.append(e)
    def adoptVariable(self, v):
        v.parent = self
        self.variables.append(v)
    def adoptFunction(self, f):
        f.parent = self
        self.functions.append(f)
    def adoptClass(self, c):
        c.parent = self
        self.innerclasses.append(c)
    def members(self):
        return self.enums + self.typedefs + self.functions + self.variables

class Class(CompoundType):
    class InheritInfo:
        '''
        InheritInfo contains the information related to base class:
        1. baseref: refid of base class, from that we can query the base class's information via Project object
        2. accessibility: accessibility < public, protected, private>
        3. isVirtual: virtual inheritance or not
        '''
        def __init__(self, baseref = "", basename = "", accessibility = "public", isVirtual = False):
            self.baseref = baseref
            self.basename = basename
            self.accessibility = accessibility
            self.isVirtual = isVirtual

    def __init__(self, refid=""):
        CompoundType.__init__(self, refid)
        self.inheritInfo = None

    def hasBase(self): return self.inheritInfo != None

    def isOrphan(self): return self.compoundname == self.name

    def setParent(self, compound): compound.adoptClass(self)

    def exposeTo(self, codeGentor):codeGentor.onClassExposed(self)

class Namespace(CompoundType):
    def __init__(self, refid):
        CompoundType.__init__(self, refid)

    def exposeTo(self, codeGentor):
        codeGentor.onNamespaceExposed(self)


class Header(CompoundType):
    class Include:
        def __init__(self, file = "", islocal = False):
            self.file = file
            self.islocal = islocal

    def __init__(self, refid):
        CompoundType.__init__(self, refid)
        self.namespaces = []
        self.includes = []
        self.parsed = False

    def updateName(self):
        if self.compoundname != "":
            firstDotIdx = self.compoundname.find(".")
            if firstDotIdx != -1: self.name = self.compoundname[:firstDotIdx]
            else: self.name = self.compoundname

    def exposeTo(self, codeGentor):
        codeGentor.onHeaderExposed(self)

    def hasNamespace(self, ns):
        return ns in self.namespaces

    def hasClass(self, cls):
        return cls in self.innerclasses

    def createIncludeSection(self):
        includeStr = "#include <gmock/gmock.h>"
        for include in self.includes:
            if include.islocal:
                incOpen = "<"
                incClose = ">"
            else:
                incOpen = '"'
                incClose = '"'
            includeStr += "\n#include {0}{1}{2}".format(incOpen, include.file, incClose)
        return includeStr

class Project:
    def __init__(self):
        self.headers = {}
        self.namespaces = {}
        self.classes = {}
        self.ready = False

    def addHeader(self, refid):
        hd = self.headers.get(refid)
        if hd == None:
            hd = Header(refid)
            self.headers[refid] = hd
        return hd

    def addNamespace(self, refid):
        ns = self.namespaces.get(refid)
        if ns == None:
            ns = Namespace(refid)
            self.namespaces[refid] = ns
        return ns

    def addClass(self, refid):
        cls = self.classes.get(refid)
        if cls == None:
            cls = Class(refid)
            self.classes[refid] = cls
        return cls