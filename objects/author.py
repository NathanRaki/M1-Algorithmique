class Author():
    
    def __init__(self, name):
        self.name = name
        self.productions = {}
        self.ndoc = 0
        
    def add(self, doc):
        self.productions[self.ndoc] = doc
        self.ndoc += 1
        
    def __str__(self):
        return "Auteur: %s, Number of docs: %s" % (self.name, self.ndoc)
    
    def getType(self):
        pass