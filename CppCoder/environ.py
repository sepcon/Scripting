import os
import sys
import re
def warning(msg):
    sys.stderr.write("WARNING: {0}\n".format(msg))

def errorHelp(msg):
    sys.stderr.write("ERROR: {0}\n".format(msg))
    print("""Usage:
    python genmock.py   header1.h   header2.h   headerN.h   path/to/output/directory
    OR
    python genmock.py   *.h     path/to/output/directory
    """)
    exit(-1)

def checkEnviron():
    if os.system("which doxygen") != 0:
        errorHelp("cannot found doxygen in system, please install it!!")


class ArgParser:
    def __init__(self):
        self.outdir = ""
        self.input = []

    def parse(self):
        if len(sys.argv) < 3:
            errorHelp("Argument missing!!")
        self.outdir = os.path.abspath(sys.argv[-1])
        self.input = sys.argv[1:-1]
        for i in range(len(self.input)):
            self.input[i] = os.path.abspath(self.input[i])

    def __validateHeaderList(self):
        alterList = []
        for header in self.input:
            if not os.path.exists(header):
                basename = os.path.basename(header)
                if basename.find("*") == -1:
                    continue
                headerPattern = re.compile(basename)
                for file in os.listdir(os.path.dirname(header)):
                    if headerPattern.match(file):
                        alterList.append(file)
            else:
                alterList.append(header)

        self.input = alterList