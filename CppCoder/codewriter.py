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
