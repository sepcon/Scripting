import os
import sys

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

