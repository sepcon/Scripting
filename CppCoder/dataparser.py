from data import Project

class DataParser:
    def __init__(self, workingDir):
        self.workingDir = workingDir
        self.project = Project()

    def parse(self):
        if not self.project.ready:
            raise Exception("The data hasn't been ready yet")