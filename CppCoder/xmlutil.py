import xml.etree.ElementTree as ET
from environ import errorHelp

def createXMLDB(path):
    xmltree = ET.parse(path)
    if xmltree != None:
        return xmltree.getroot()
    else:
        return None

def findText(elem, tag):
    return elem.findtext(tag, "")

def getText(elem, propName):
    return elem.get(propName, "")

def findTagProp(elem, tagName, propName):
    tag = elem.find(tagName)
    if tag != None:
        return tag.get(propName, "")
    else:
        return ""

def joinTextOfEntireChildren(elem, delim=""):
    return delim.join(elem.itertext())