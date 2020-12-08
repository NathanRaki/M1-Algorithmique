from gensim.summarization.summarizer import summarize

class Document():
    def __init__(self, title, date, url, text):
        self.title = title
        self.date = date
        self.url = url
        self.text = text
        
    def get_title(self):
        return self.title
    
    def get_date(self):
        return self.date
    
    def get_url(self):
        return self.url
    
    def get_text(self):
        return self.text
    
    def summarize(self):
        try:
            summary = summarize(self.text)
            if summary:
                return summarize(self.text)
            else:
                raise
        except:
            return "This document cannot be summarized."
        
    def __str__(self):
        return "Document %s: %s" % (self.getType(), self.title)
    
    def __repr__(self):
        return self.title
    
    def getType(self):
        pass

class RedditDocument(Document):
    def __init__(self, title, date, url, text, author, nbcomments):
        super().__init__(title, date, url, text)
        self.author = author
        self.nbcomments = nbcomments
        
    def get_authors(self):
        return self.author
        
    def get_nbcomments(self):
        return self.nbcomments
    
    def __str__(self):
        return super().__str__()
    
    def getType(self):
        return 'Reddit'
        
class ArxivDocument(Document):
    def __init__(self, title, date, url, text, authors):
        super().__init__(title, date, url, text)
        self.authors = authors
        
    def get_authors(self):
        return self.authors
        
    def __str__(self):
        return super().__str__()
    
    def getType(self):
        return 'Arxiv'
