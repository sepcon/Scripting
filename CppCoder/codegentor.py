
class ICodeGentor:
    ''' Visitor patterns ?? not really that
     Design approach:
     1. Data: Collect Discoverable Data from xml database and don't need to care about how to convert it to code
        Discoverable Data must provide functionality to expose its data to CodeGenerator via exposeTo(codeGentor CodeGenerator)
        follows the Visitor pattern
    #   CodeObject:
          `-- exposeTo(codeGentor)
    #
        Header: (.h file) --> CompoundType
             --- Members (Global functions, enums, variable)
             `-- Namespaces
              `- Classes
        Namespace: --> CompoundType
             --- Members (functions, enums, variables)
             `-- Sub-namespaces
              `- Inner-classes
        Classe: --> CompoundType
             --- Members (functions, enums, variables)
             `-- Inner-classes
        Member: --> MemberType
             ---  name
             `--  kind ( "enum", "function", "variable" ... )
              `-- scope - visibility
               `- parent - which CompoundType object it belongs to (class/namespace/header)

     2. CodeGenerator: can provide many kinds of CodeGenerator, with the input is Discoverable Data
         Must provide below interfaces:
    #    ICodeGentor
          `-- onFunctionExposed(function DiscoverableData)
          `-- onVariableExposed(varialbe DiscoverableData)
          `-- onClassExposed(class DiscoverableData)
          `-- onNamespaceExposed(namespace DiscoverableData)
          `-- onHeaderExposed(header DiscoverableData)
          `-- onEnumExposed(enum DiscoverableData)
    '''
    def onFunctionExposed(self, f):raise Exception("{0}: function onFunctionExposed has not implemented yet".format(self))
    def onVariableExposed(self, v):raise Exception("{0}: function onVariableExposed has not implemented yet".format(self))
    def onClassExposed(self, c):raise Exception("{0}: function onClassExposed has not implemented yet".format(self))
    def onNamespaceExposed(self, ns):raise Exception("{0}: function onNamespaceExposed has not implemented yet".format(self))
    def onHeaderExposed(self, h):raise Exception("{0}: function onHeaderExposed has not implemented yet".format(self))
    def onEnumExposed(self, e):raise Exception("{0}: function onEnumExposed has not implemented yet".format(self))
    def onTypeDefExposed(self, t): Exception("{0}: function onTypeDefExposed has not implemented yet".format(self))




