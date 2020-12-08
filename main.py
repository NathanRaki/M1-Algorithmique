import praw
import xmltodict
import urllib.request
import datetime as dt

from objects.corpus import Corpus
from objects.document import RedditDocument, ArxivDocument

corpus = Corpus("Corona")

reddit = praw.Reddit(client_id='EOpJbD-dhnSW6w', client_secret='RGT0E-ceVmPHxyxT9fzPUTSRsg0eJA', user_agent='Reddit WebScraping')
hot_posts = reddit.subreddit('Coronavirus').hot(limit=100)
for post in hot_posts:
    datet = dt.datetime.fromtimestamp(post.created)
    txt = '%s. %s' % (post.title, post.selftext)
    txt = txt.replace('\n', ' ')
    txt = txt.replace('\r', ' ')
    doc = RedditDocument(post.title,
                   datet,
                   post.url,
                   txt,
                   [post.author_fullname],
                   post.num_comments)
    corpus.add_doc(doc)
    
url = 'http://export.arxiv.org/api/query?search_query=all:covid&start=0&max_results=100'
data = urllib.request.urlopen(url).read().decode()
docs = xmltodict.parse(data)['feed']['entry']

for doc in docs:
    datet = dt.datetime.strptime(doc['published'], '%Y-%m-%dT%H:%M:%SZ')
    try:
        authors = [aut['name'] for aut in doc['author']][0]
    except:
        authors = [doc['author']['name']]
    txt = '%s. %s' % (doc['title'], doc['summary'])
    txt = txt.replace('\n', ' ')
    txt = txt.replace('\r', ' ')
    doc = ArxivDocument(doc['title'],
                   datet,
                   doc['id'],
                   txt,
                   authors)
    corpus.add_doc(doc)
    
# Illustrate __str__
for _,v in corpus.collection.items():
    #print(v)
    pass
# Illustrate __repr__
for _,v in corpus.collection.items():
    #print([v])
    pass
    
for match in corpus.search('disease'):
    #print(match)
    pass
    
#print(corpus.concorde('corona', 20))

for _, doc in corpus.collection.items():
    #print(doc.summarize())
    pass
    
corpus.stats()