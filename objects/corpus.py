import re
import pickle
import pandas as pd
from objects.author import Author
from gensim.parsing.preprocessing import remove_stopwords

def nettoyer_texte(text):
    result = text.lower()
    result = result.replace('\n', ' ')
    result = re.sub(r"[0-9,.;@\-\(\)/#?%!:&$]+\ *", " ", result)
    result = remove_stopwords(result)
    return result

class Corpus():
    
    def __init__(self, name):
        self.name = name
        self.collection = {}
        self.authors = {}
        self.id2doc = {}
        self.id2aut = {}
        self.ndoc = 0
        self.naut = 0
        self.txt_cache = ''
        
    def generate_txt_cache(self):
        if not self.txt_cache:
            for _, doc in self.collection.items():
                self.txt_cache += (". %s" % doc.get_text())
    
    def stats(self):
        self.generate_txt_cache()
        text = nettoyer_texte(self.txt_cache)
        freq = {}
        for word in text.split(" "):
            if word:
                freq[word] = freq[word] + 1 if word in freq else 1
        freq = {k: v for k, v in sorted(freq.items(), key=lambda item: item[1], reverse=True)}
        top_words = []
        for k,v in freq.items():
            if len(top_words) < 5:
                top_words.append((k, v))
        print("### Statistiques du Corpus ###")
        print("Nombre de mots : %s" % len(freq))
        print("Mots les plus fréquents :")
        for word in top_words:
            print("\t%s -> %s occurence(s)" % (word[0], str(word[1])))
        
    def search(self, keyword):
        self.generate_txt_cache()
        pos = 0
        matches = []
        tmp = self.txt_cache
        while pos < len(tmp):
            tmp = tmp[pos:]
            match = re.search(keyword, tmp)
            if match:
                pos = match.start() + 1
                matches.append(tmp[match.start()-20:match.end()+20])
            else:
                break
        return matches
    
    def concorde(self, keyword, size):
        self.generate_txt_cache()
        pos = 0
        matches, list_keys = [], ['left_context', 'match', 'right_context']
        tmp = self.txt_cache
        while pos < len(tmp):
            tmp = tmp[pos:]
            match = re.search(keyword, tmp)
            if match:
                pos = match.start() + 1
                matches.append(dict(zip(list_keys, ['...'+tmp[match.start()-size:match.start()], match.group(0), tmp[match.end():match.end()+size]+'...'])))
            else:
                break
        return pd.DataFrame(matches, columns=list_keys)
        
    def sort_title(self, nreturn=None):
        if nreturn is None:
            nreturn = self.ndoc
        return [self.collection[k] for k,v in sorted(self.collection.items(), key=lambda item: item[1].get_title())][:(nreturn)]
    
    def sort_date(self, nreturn=None):
        if nreturn is None:
            nreturn = self.ndoc
        return [self.collection[k] for k,v in sorted(self.collection.items(), key=lambda item: item[1].get_date(), reverse=True)][:(nreturn)]
    
    def add_doc(self, doc):
        self.collection[self.ndoc] = doc
        self.id2doc[self.ndoc] = doc.get_title()
        self.ndoc += 1
        aut_names = doc.get_authors()
        for aut_name in aut_names:
            aut = self.get_aut2id(aut_name)
            if aut is not None:
                self.authors[aut].add(doc)
            else:
                self.add_aut(aut_name, doc)
        
    def add_aut(self, aut_name, doc):
        aut_temp = Author(aut_name)
        aut_temp.add(doc)
        self.authors[self.naut] = aut_temp
        self.id2aut[self.naut] = aut_name
        self.naut += 1
        
    def get_aut2id(self, author_name):
        aut2id = {v: k for k,v in self.id2aut.items()}
        _id = aut2id.get(author_name)
        return _id
    
    def save(self, file):
        pickle.dump(self, open(file, 'wb'))
        
    def __str__(self):
        return 'Corpus: %s, Number of docs: %s, Number of authors: %s' % (self.name, str(self.ndoc), str(self.naut))