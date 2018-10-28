import xmlutil
from data import *
from coder import *


def _toLineNumber(string):
    try:
        return int(string)
    except:
        return 0

class XMLParser(DataParser):
    __kindsOfSectionVisibleToWorld = set(["public-func", "public-attrib", "public-type" , "enum", "func" ])

    def __init__(self, workingDir):
        DataParser.__init__(self, workingDir)

    def parse(self):
        indexxmlRoot = xmlutil.createXMLDB(os.path.join(self.workingDir, "index.xml"))
        for compound in indexxmlRoot.iter("compound"):
            kind = compound.get("kind")
            refid = compound.get("refid")
            if kind == "file":
                self.project.addHeader(refid)
            elif kind == "namespace":
                self.project.addNamespace(refid)
            elif kind == "class" or kind == "struct":
                cls = self.project.addClass(refid)
        def parseComounds(compoundMap, extractFunc):
            for cmp in compoundMap.values():
                self._makeCompoundDataAvailable(cmp, extractFunc)

        parseComounds(self.project.headers, XMLParser._extractHeaderInfo)
        parseComounds(self.project.namespaces, XMLParser._extractNamespaceInfo)
        parseComounds(self.project.classes, XMLParser._extractClassInfo)
        # for header in self.project.headers.values():
        #     self._extractHeaderInfo(header)
        # for namespace in self.project.namespaces.values():
        #     self._extractNamespaceInfo(namespace)
        # for cls in self.project.classes.values():
        #     self._extractClassInfo(cls)

        self.project.ready = True

        return self.project


    def _makeCompoundDataAvailable(self, compound, extractFunc):
        if extractFunc(self, compound) == True:
            compound.dataAvailable = True
        else:
            compound.dataAvailable = False

    @staticmethod
    def _extractCodeUnitInfo(codeunit, xmlelem):
        assert (isinstance(codeunit, CodeUnit))
        if codeunit.location == None: codeunit.location = CodeUnit.Location()
        codeunit.kind = xmlutil.getText(xmlelem, "kind")
        codeunit.name = xmlutil.findText(xmlelem, "name")
        codeunit.location.file = xmlutil.findTagProp(xmlelem, "location", "file")
        codeunit.location.line = _toLineNumber(xmlutil.findTagProp(xmlelem, "location", "line"))

    @staticmethod
    def _extractMemberInfo(member, xmlMemberdef):
        assert (isinstance(member, Member))
        XMLParser._extractCodeUnitInfo(member, xmlMemberdef)
        member.isStatic = (xmlutil.getText(xmlMemberdef, "static") == "yes")
        member.scope = xmlutil.getText(xmlMemberdef, "prot")

    @staticmethod
    def _extractHasTypeMemberInfo(member, xmlMemberdef):
        assert (isinstance(member, HasTypeMember))
        XMLParser._extractMemberInfo(member, xmlMemberdef)
        member.argsstring = xmlutil.findText(xmlMemberdef, "argsstring")
        member.definition = xmlutil.findText(xmlMemberdef, "definition")
        typeTag = xmlMemberdef.find("type")
        if typeTag != None:
            if typeTag.text == None:
                member.type = xmlutil.findText(typeTag, "ref")
            else:
                member.type = typeTag.text

    @staticmethod
    def _extractFunctionInfo(function, xmlMemberdef):
        assert (isinstance(function, Function))
        XMLParser._extractHasTypeMemberInfo(function, xmlMemberdef)
        function.explicit = (xmlMemberdef.get("explicit") == "yes")
        function.inline = (xmlMemberdef.get("explicit") == "yes")
        function.const = (xmlMemberdef.get("const") == "yes")
        function.virtualType = xmlMemberdef.get("virt")
        for xmlparam in xmlMemberdef.iter("param"):
            function.paramsList.append(Function.Parameter(xmlutil.findText(xmlparam, "type"), xmlutil.findText(xmlparam, "declname"),
                                           xmlutil.findText(xmlparam, "defval")))

    @staticmethod
    def _extractVariableInfo(variable, xmlMemberdef):
        assert (isinstance(variable, Variable))
        XMLParser._extractHasTypeMemberInfo(variable, xmlMemberdef)

    @staticmethod
    def _extractEnumInfo(enum, xmlMemberdef):
        assert (isinstance(enum, Enum))
        XMLParser._extractMemberInfo(enum, xmlMemberdef)
        enum.values = [
                Enum.Value(
                xmlutil.findText(xmlelem, "name"),
                xmlutil.findText(xmlelem, "initializer")
                ) for xmlelem in xmlMemberder.iter("enumvalue")
                ]

    @staticmethod
    def _extractCompoundTypeInfo(compound, xmlCompounddef):
        XMLParser._extractCodeUnitInfo(compound, xmlCompounddef)
        for sectiondef in xmlCompounddef.iter("sectiondef"):
            if sectiondef.get("kind") not in XMLParser.__kindsOfSectionVisibleToWorld:
                continue
            for memberdef in sectiondef.iter("memberdef"):
                member = None
                kind = memberdef.get("kind")
                if kind == "variable":
                    member = Variable()
                    XMLParser._extractVariableInfo(member, memberdef)
                elif kind == "function":
                    member = Function()
                    XMLParser._extractFunctionInfo(member, memberdef)
                elif kind == "enum":
                    member= Enum()
                    XMLParser._extractEnumInfo(member, memberdef)

                if member != None:
                    compound.members.add(member)
                    member.parent = compound

        return True

    def _extractClassInfo(self, cls):
        assert (isinstance(cls, Class))
        if cls.dataAvailable: return True

        compounddef = self._findCompounddef(cls.refid)
        if compounddef == None: return False

        XMLParser._extractCompoundTypeInfo(cls, compounddef)

        compoundname = compounddef.find("compoundname")
        if compoundname != None:
            cls.compoundname = compoundname.text
            lastOf2Colon = cls.compoundname.rfind(":")
            if lastOf2Colon == -1:
                cls.name = cls.compoundname
            else:
                cls.name = cls.compoundname[lastOf2Colon + 1:]
            for innerclass in compounddef.iter("innerclass"):
                cls.innerclasses.append(self.project.addClass(innerclass.get("refid")))
            for innerclass in cls.innerclasses:
                self._makeCompoundDataAvailable(innerclass, XMLParser._extractClassInfo)

            return True
        else:
            return False

    def _extractNamespaceInfo(self, namespace):
        assert (isinstance(namespace, Namespace))
        if namespace.dataAvailable: return True
        compounddef = self._findCompounddef(namespace.refid)
        if compounddef == None:return False

        XMLParser._extractCompoundTypeInfo(namespace, compounddef)
        namespace.compoundname = xmlutil.findText(compounddef, "compoundname")
        for innerclassDB in compounddef.iter("innerclass"):
            cls = self.project.addClass(innerclassDB.get("refid"))
            namespace.innerclasses.add(cls)
            self._makeCompoundDataAvailable(cls, XMLParser._extractClassInfo)

        return True


    def _extractHeaderInfo(self, header):
        assert (isinstance(header, Header))
        if header.dataAvailable: return True

        compounddef = self._findCompounddef(header.refid)
        if compounddef == None: return False

        XMLParser._extractCompoundTypeInfo(header, compounddef)
        for include in compounddef.iter("includes"):
            header.includes.append(Header.Include(include.text, xmlutil.getText(include, "local") == "yes"))

        for innernamespaceDB in compounddef.iter("innernamespace"):
            header.namespaces.append(self.project.addNamespace(innernamespaceDB.get("refid")))
        for innerclassDB in compounddef.iter("innerclass"):
            header.innerclasses.add(self.project.addClass(innerclassDB.get("refid")))

        return True

    def _findCompounddef(self, refid):
        xmlfilePath = os.path.join(self.workingDir, refid + ".xml")
        if not os.path.isfile(xmlfilePath):
            errorHelp("{0} does not exist, error maybe due to doxygen works incorrectly".format(xmlfilePath))
        xmldb = xmlutil.createXMLDB(xmlfilePath)
        if xmldb == None:
            errorHelp("Error while parsing file " + xmlfilePath)

        return xmldb.find("compounddef")
