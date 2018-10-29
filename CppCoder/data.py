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

class Variable(HasTypeMember):
    def __init__(self):
        HasTypeMember.__init__(self)

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

    def exposeTo(self, codeGentor):
        codeGentor.onEnumExposed(self)

class CompoundType(CodeUnit):
    def __init__(self, refid):
        CodeUnit.__init__(self)
        self.refid = refid
        self.compoundname = ""
        self.members = set()
        self.dataAvailable = False

class Class(CompoundType):
    def __init__(self, refid=""):
        CompoundType.__init__(self, refid)
        self.name = ""
        self.innerclasses = []
        self.parsed = False
        self.enums = []

    def isOrphan(self):
        return self.compoundname == self.name

    def exposeTo(self, codeGentor):
        codeGentor.onClassExposed(self)

class Namespace(CompoundType):
    def __init__(self, refid):
        CompoundType.__init__(self, refid)
        self.innerclasses = set()

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
        self.innerclasses = set()
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
        includeStr = ""
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