import subprocess
import shutil

from xmlparser import *
from gmockgentor import *


class Worker:
    def __init__(self):
        checkEnviron()
        argParser = ArgParser()
        argParser.parse()
        self.input = argParser.input
        self.outdir = argParser.outdir
        self.workingDir = os.path.join(self.outdir, ".tmp-mock-workspace")
        self.dataType = "xml"
        self.codeGentorType = "gmocker"
        self.parsed = False

    def __del__(self):
        self._clean()

    def dojob(self):
        self._createWorkspace()
        self._launchDoxygen()
        self._genCode(self._parseDoxygenOutput())
        self._clean()

    def _createWorkspace(self):
        if not os.path.exists(self.outdir):
            print("{0} doesnot exist, create it".format(self.outdir))
            os.makedirs(self.outdir)
        if not os.path.exists(self.workingDir):
            os.makedirs(self.workingDir)

        self._copyToWorkspace(self.input)

        FileWriter(os.path.join(self.workingDir, "Doxyfile")).writeln("GENERATE_HTML=no\nGENERATE_LATEX=no\nGENERATE_XML=yes\nXML_PROGRAMLISTING=no\nFILE_PATTERNS=*.h\nXML_OUTPUT={0}/xml\nINPUT={0}".format(self.workingDir))

    def _copyToWorkspace(self, input):
        if isinstance(input, list):
            for i in input:
                if os.path.isfile(i):
                    self._copyToWorkspace(i)
                elif os.path.isdir(i):
                    self._copyToWorkspace([ os.path.join(i, file) for file in os.listdir(i) ])
                else:
                    print("WARNING: {0} is not a file a directory".format(i))

        elif os.path.isdir(input):
            self._copyToWorkspace([ os.path.join(input, file) for file in os.listdir(input) ])
        elif os.path.isfile(input):
            name = os.path.basename(input)
            print("Copying file {0} to workspace".format(input))
            shutil.copyfile(input, os.path.join(self.workingDir, name))
        else:
            errorHelp(input + ": don't know type of this input")


    def _launchDoxygen(self):
        os.chdir(self.workingDir)
        self._runExternalCommand("doxygen",  os.path.join(self.workingDir, "Doxyfile"))

    def _parseDoxygenOutput(self):
        dataParser = XMLParser(os.path.join(self.workingDir, "xml"))
        return dataParser.parse()

    def _genCode(self, projectData):
        codeGentor = GmockCodeGentor(projectData, self.outdir)
        codeGentor.genCode()

    def _runExternalCommand(self, command, argsStr):
        process = subprocess.Popen([command, argsStr])
        ret = process.wait()
        return ret

    def _clean(self):
        if self.workingDir != "":
            # os.system("rm -rf " + self.workingDir + " 2>/dev/null")
            self.input = ""
            self.outdir = ""
            self.workingDir = ""
            self.headers = {}
            self.namespaces = {}
            self.classes = {}
            self.parsed = False
            print("Workspace cleaned!")

if __name__ == "__main__":
    Worker().dojob()

    # wsp = Worker(["/home/cgo1hc/samba/views/nincg3_GEN/ai_projects/generated/components/asf/asf/NavigationService/dbus/src-gen/org/bosch/cm/navigation/NavigationServiceConst.h"], "/home/cgo1hc/Desktop/sds_adapter_mock")
    # wsp.dojob()
