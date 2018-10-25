import xml.etree.ElementTree as ET

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

class CodeObject:
    class Location:
        def __init__(self, xmlelem):
            self.file = XMLElem.findTagProp(xmlelem, "location", "file")
            try:
                self.line = int(XMLElem.findTagProp(xmlelem, "location", "line"))
            except:
                self.line = 0

    def __init__(self, xmlElem = None):
        if xmlElem != None:
            self.collectLocationInfo(xmlElem)
        else:
            self.location = None

    def collectLocationInfo(self, xmlElem):
        self.location = CodeObject.Location(xmlElem)

    def exposeTo(self, codeGentor): raise Exception("{0}: Function has not implemented yet".format(self))

class Member(CodeObject):
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
        CodeObject.__init__(self, xmlMemberdef)
        self.parent = parent
        self.name = XMLElem.findText(xmlMemberdef, "name")
        self.isStatic = (XMLElem.getText(xmlMemberdef, "static") == "yes")
        self.scope = XMLElem.getText(xmlMemberdef, "prot")

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
    class Parameter:
        def __init__(self, type, name, defval):
            self.type = type
            self.name = name
            self.defval = defval

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
        paramList = []
        for xmlparam in xmlMemberdef.iter("param"):
            parameter = Function.Parameter(XMLElem.findText(xmlparam, "type"), XMLElem.findText(xmlparam, "declname"), XMLElem.findText(xmlparam, "defval"))
            paramList.append(parameter)

        return paramList

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
    def __init__(self, xmlMemberdef, cls = None):
        HasTypeMember.__init__(self, xmlMemberdef, cls)

    def exposeTo(self, codeGentor):
        codeGentor.onVariableExposed(self)

class CompoundType(CodeObject):
    kindsOfSectionVisibleToWorld = set(["public-func", "public-attrib", "public-type" , "enum", "func" ])

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
        CodeObject.__init__(self)
        self.refid = refid
        self.workspace = workspace
        self.kind = kind
        self.members = set()


    def getXMLDB(self):
        return self.workspace.getXMLDB(self.refid)

    def collectMembers(self, xmlCompounddef):
        for sectiondef in xmlCompounddef.iter("sectiondef"):
            if sectiondef.get("kind") not in CompoundType.kindsOfSectionVisibleToWorld:
                return
            for memberdef in sectiondef.iter("memberdef"):
                newMem = Member.new(memberdef, self)
                if newMem != None:
                    self.members.add(newMem)

class Class(CompoundType):
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

        self.collectLocationInfo(compounddef)
        self.collectMembers(compounddef) # it should be enums/variables/methods
        self.collectAndParseSubClass(compounddef)

    def collectAndParseSubClass(self, compounddef):
        for innerclass in compounddef.iter("innerclass"):
            self.subclasses.append(self.workspace.addClass(innerclass.get("refid")))

        for subclass in self.subclasses:
            subclass.parse()

class Namespace(CompoundType):
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

        self.collectLocationInfo(compounddef)
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
        self.parsed = False

    def exposeTo(self, codeGentor):
        codeGentor.onHeaderExposed(self)

    def parse(self):
        self.parsed = True
        root = self.getXMLDB()
        compounddef = root.find("compounddef")
        if compounddef == None:
            return False

        self.includes = compounddef.findall("includes")
        self.collectMembers(compounddef) # it should be enums
        self.collectNamespaces(compounddef)
        self.collectClasses(compounddef)
        self.collectLocationInfo(compounddef)

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
