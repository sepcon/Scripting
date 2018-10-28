import xml.etree.ElementTree as ET
from environ import errorHelp

def createXMLDB(path):
    xmltree = ET.parse(path)
    if xmltree != None:
        return xmltree.getroot()
    else:
        return None

def findText(elem, tag):
    t = elem.find(tag)
    if t != None and t.text != None:
        return t.text
    else:
        return ""


def getText(elem, propName):
    prop = elem.get(propName)
    if prop != None:
        return prop
    else:
        return ""

def findTagProp(elem, tagName, propName):
    tag = elem.find(tagName)
    if tag != None:
        prop = tag.get(propName)
        if prop != None:
            return prop
    return ""