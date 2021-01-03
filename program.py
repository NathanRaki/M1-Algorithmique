import scroll
import tkinter as tk
import tkinter.ttk as ttk

import praw
import xmltodict
import numpy as np
import urllib.request
import datetime as dt

from objects.corpus import Corpus
from objects.document import RedditDocument, ArxivDocument

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def genCorpus(platform, nb, keyword):
    try:
        corpus = Corpus("%s:%s" % (platform, keyword))
        if platform == "reddit":
            api = praw.Reddit(client_id='EOpJbD-dhnSW6w', client_secret='RGT0E-ceVmPHxyxT9fzPUTSRsg0eJA', user_agent='Reddit WebScraping')
            posts = api.subreddit(keyword).hot(limit=nb)
            for post in posts:
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
        elif platform == "arxiv":
            url = "http://export.arxiv.org/api/query?search_query=all:%s&start=0&max_results=%s" % (keyword, str(nb))
            api = urllib.request.urlopen(url).read().decode()
            posts = xmltodict.parse(api)['feed']['entry']
            for post in posts:
                datet = dt.datetime.strptime(post['published'], '%Y-%m-%dT%H:%M:%SZ')
                try:
                    authors = [aut['name'] for aut in post['author']][0]
                except:
                    authors = [post['author']['name']]
                txt = '%s. %s' % (post['title'], post['summary'])
                txt = txt.replace('\n', ' ')
                txt = txt.replace('\r', ' ')
                doc = ArxivDocument(post['title'],
                               datet,
                               post['id'],
                               txt,
                               authors)
                corpus.add_doc(doc)
        return corpus
    except Exception as e:
        print('Error with %s corpus generation : %s' % (platform, e))

class Program():
    
    def __init__(self):
        self.state = "Term Frequency"
        self.loaded = False
        self.figures = dict()
        self.corpuses = dict()
        self.top = tk.Tk()

        w = 1920
        h = 1080
        ws = self.top.winfo_screenwidth()
        hs = self.top.winfo_screenheight()
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)

        self.top.geometry("%dx%d+%d+%d" % (w, h, x, y))
        self.top.minsize(1, 1)
        self.top.maxsize(1905, 1050)
        self.top.resizable(1,  1)
        self.top.title("Corpus Analyze")

        self.TCombobox1 = ttk.Combobox(self.top, state="readonly", values=["Term Frequency", "Vocabulary"])
        self.TCombobox1.place(relx=0.351, rely=0.044, relheight=0.043, relwidth=0.295)
        self.TCombobox1.configure(takefocus="")
        self.TCombobox1.current(0)
        self.TCombobox1.bind("<<ComboboxSelected>>", self.updateNotebook)

        self.Frame1 = tk.Frame(self.top)
        self.Frame1.place(relx=0.029, rely=0.117, relheight=0.843, relwidth=0.94)

        self.Frame1.configure(relief='groove')
        self.Frame1.configure(borderwidth="2")
        self.Frame1.configure(relief="groove")

        self.TNotebook1 = ttk.Notebook(self.Frame1)
        self.TNotebook1.place(relx=0.01, rely=0.017, relheight=0.962, relwidth=0.973)
        self.TNotebook1.configure(takefocus="")
        self.TNotebook1_t1 = tk.Frame(self.TNotebook1)
        self.TNotebook1_t1.configure(background="#d9d9d9")
        self.TNotebook1.add(self.TNotebook1_t1, padding=3)
        self.TNotebook1.tab(0, text="Config",compound="left",underline="-1",)
        self.TNotebook1_t3 = tk.Frame(self.TNotebook1)
        self.TNotebook1_t3.configure(background="#d9d9d9")
        self.TNotebook1.add(self.TNotebook1_t3, padding=3)
        self.TNotebook1.tab(1, text="Results",compound="left",underline="-1",)
        self.TNotebook1_t2 = tk.Frame(self.TNotebook1)
        self.TNotebook1_t2.configure(background="#d9d9d9")
        self.TNotebook1.add(self.TNotebook1_t2, padding=3)
        self.TNotebook1.tab(2, text="Debug",compound="left",underline="-1",)

    def tfGui(self):
        self.Labelframe1 = tk.LabelFrame(self.TNotebook1_t1)
        self.Labelframe1.place(relx=0.064, rely=0.076, relheight=0.294
                , relwidth=0.126)
        self.Labelframe1.configure(background="#d9d9d9")
        self.Labelframe1.configure(relief='groove')
        self.Labelframe1.configure(text='''Select Source''')

        self.reddit = tk.IntVar()
        self.arxiv = tk.IntVar()
        self.twitter = tk.IntVar()
        self.Checkbutton1 = tk.Checkbutton(self.Labelframe1, variable=self.reddit)
        self.Checkbutton1.place(relx=0.085, rely=0.194, relheight=0.135
                , relwidth=0.788, bordermode='ignore')
        self.Checkbutton1.configure(background="#d9d9d9")
        self.Checkbutton1.configure(activebackground="#e9e9e9")
        self.Checkbutton1.configure(highlightthickness=0)
        self.Checkbutton1.configure(justify='left')
        self.Checkbutton1.configure(text='''Reddit''')

        self.Checkbutton1_1 = tk.Checkbutton(self.Labelframe1, variable=self.arxiv)
        self.Checkbutton1_1.place(relx=0.085, rely=0.387, relheight=0.135
                , relwidth=0.788, bordermode='ignore')
        self.Checkbutton1_1.configure(background="#d9d9d9")
        self.Checkbutton1_1.configure(activebackground="#e9e9e9")
        self.Checkbutton1_1.configure(highlightthickness=0)
        self.Checkbutton1_1.configure(justify='left')
        self.Checkbutton1_1.configure(text='''Arxiv''')

        self.Checkbutton1_2 = tk.Checkbutton(self.Labelframe1, variable=self.twitter)
        self.Checkbutton1_2.place(relx=0.085, rely=0.581, relheight=0.135
                , relwidth=0.788, bordermode='ignore')
        self.Checkbutton1_2.configure(background="#d9d9d9")
        self.Checkbutton1_2.configure(activebackground="#e9e9e9")
        self.Checkbutton1_2.configure(highlightthickness=0)
        self.Checkbutton1_2.configure(justify='left')
        self.Checkbutton1_2.configure(text='''Twitter''')

        self.Labelframe2 = tk.LabelFrame(self.TNotebook1_t1)
        self.Labelframe2.place(relx=0.214, rely=0.076, relheight=0.237
                , relwidth=0.298)
        self.Labelframe2.configure(background="#d9d9d9")
        self.Labelframe2.configure(relief='groove')
        self.Labelframe2.configure(text='''Parameters''')
        
        self.Labelframe2.grid_rowconfigure(0, weight=1)
        self.Labelframe2.grid_rowconfigure(1, weight=1)
        self.Labelframe2.grid_rowconfigure(2, weight=1)
        self.Labelframe2.grid_columnconfigure(0, weight=1)
        self.Labelframe2.grid_columnconfigure(1, weight=1)

        self.Spinbox1 = tk.Spinbox(self.Labelframe2, from_=1.0, to=1000.0)
        #self.Spinbox1.place(relx=0.287, rely=0.64, relheight=0.168, relwidth=0.283, bordermode='ignore')
        self.Spinbox1.grid(row=1, column=1, sticky="nsew")
        self.Spinbox1.configure(activebackground="#f9f9f9")
        self.Spinbox1.configure(background="white")
        self.Spinbox1.configure(font="TkDefaultFont")
        self.Spinbox1.configure(highlightbackground="black")
        self.Spinbox1.configure(selectbackground="blue")
        self.Spinbox1.configure(selectforeground="white")

        self.Entry1 = tk.Entry(self.Labelframe2)
        #self.Entry1.place(relx=0.287, rely=0.4, height=21, relwidth=0.595, bordermode='ignore')
        self.Entry1.grid(row=0, column=1, sticky="nsew")
        self.Entry1.configure(background="white")
        self.Entry1.configure(font="TkFixedFont")
        
        self.Spinbox2 = tk.Spinbox(self.Labelframe2, from_=1.0, to=1000.0)
        self.Spinbox2.grid(row=2, column=1, sticky="nsew")
        self.Spinbox2.configure(activebackground="#f9f9f9")
        self.Spinbox2.configure(background="white")
        self.Spinbox2.configure(font="TkDefaultFont")
        self.Spinbox2.configure(highlightbackground="black")
        self.Spinbox2.configure(selectbackground="blue")
        self.Spinbox2.configure(selectforeground="white")

        self.Label1 = tk.Label(self.Labelframe2)
        #self.Label1.place(relx=0.036, rely=0.4, height=19, width=66, bordermode='ignore')
        self.Label1.grid(row=0, column=0, sticky="nsew")
        self.Label1.configure(text='''Keyword''')

        self.Label1_1 = tk.Label(self.Labelframe2)
        #self.Label1_1.place(relx=0.036, rely=0.64, height=19, width=66, bordermode='ignore')
        self.Label1_1.grid(row=1, column=0, sticky="nsew")
        self.Label1_1.configure(activebackground="#f9f9f9")
        self.Label1_1.configure(text='''Quantity''')
        
        self.Label1_2 = tk.Label(self.Labelframe2)
        #self.Label1_2.place(relx=0.036, rely=0.64, height=19, width=66, bordermode='ignore')
        self.Label1_2.grid(row=2, column=0, sticky="nsew")
        self.Label1_2.configure(activebackground="#f9f9f9")
        self.Label1_2.configure(text='''Top''')
        
        self.Button1 = tk.Button(self.TNotebook1_t1)
        self.Button1.place(relx=0.578, rely=0.152, height=29, width=69)
        self.Button1.configure(text='''Generate''')
        self.Button1.configure(command=self.generate)
        
        self.PlotFrame = tk.Frame(self.TNotebook1_t3)
        self.PlotFrame.place(relx=0.05, rely=0.05, relheight=0.9, relwidth=0.9)
        self.PlotFrame.configure(background="#d9d9d9")
        self.PlotFrame.configure(relief='groove')
        self.PlotFrame.configure(borderwidth="2")
        self.PlotFrame.configure(relief="groove")
        
        self.Output = scroll.ScrolledText(self.TNotebook1_t2)
        self.Output.place(relx=0.022, rely=0.032, relheight=0.933, relwidth=0.954)
        self.Output.configure(background="#5f5f5f")
        self.Output.configure(borderwidth="2")
        self.Output.configure(wrap="none")
        
    def generate(self):
        self.destroyResults()
        self.platforms = list()
        coords = [(0,0), (0,1), (1,0), (1,1)]
        if self.reddit.get():
            self.platforms.append("reddit")
            self.redditCorpus = genCorpus("reddit", int(self.Spinbox1.get()), self.Entry1.get())
            self.corpuses["reddit"] = self.redditCorpus
            if self.redditCorpus:
                self.Output.insert(tk.END, self.redditCorpus.stats())
                self.Output.see("end")
        if self.arxiv.get():
            self.platforms.append("arxiv")
            self.arxivCorpus = genCorpus("arxiv", int(self.Spinbox1.get()), self.Entry1.get())
            self.corpuses["arxiv"] = self.arxivCorpus
            if self.arxivCorpus:
                self.Output.insert(tk.END, self.arxivCorpus.stats())
                self.Output.see("end")
        if self.twitter.get():
            self.platforms.append("twitter")
            
        for i in range(len(self.platforms)):
            self.PlotFrame.grid_rowconfigure(coords[i][0], weight=1)
            self.PlotFrame.grid_columnconfigure(coords[i][1], weight=1)
            self.figures[self.platforms[i]] = dict()
            self.figures[self.platforms[i]]['fig'] = plt.Figure(figsize=(6,5), dpi=100)
            self.figures[self.platforms[i]]['ax'] = self.figures[self.platforms[i]]['fig'].add_subplot(111)
            self.figures[self.platforms[i]]['widget'] = FigureCanvasTkAgg(self.figures[self.platforms[i]]['fig'], self.PlotFrame)
            self.figures[self.platforms[i]]['widget'].get_tk_widget().grid(row=coords[i][0], column=coords[i][1], sticky="nsew")
            self.figures[self.platforms[i]]['widget'].get_tk_widget().configure(background="#000000")
            self.figures[self.platforms[i]]['widget'].get_tk_widget().configure(relief='groove')
            self.figures[self.platforms[i]]['widget'].get_tk_widget().configure(borderwidth="2")
            self.figures[self.platforms[i]]['df'] = self.corpuses[self.platforms[i]].topwords(int(self.Spinbox2.get()))
            self.figures[self.platforms[i]]['df'].plot(kind='bar', legend=False, ax=self.figures[self.platforms[i]]['ax'])
            self.figures[self.platforms[i]]['ax'].set_xticklabels(self.figures[self.platforms[i]]['ax'].xaxis.get_majorticklabels(), rotation=45, fontsize=9)
            self.figures[self.platforms[i]]['ax'].set_yticks(np.arange(0, max(self.figures[self.platforms[i]]['df']['Count']), round(max(self.figures[self.platforms[i]]['df']['Count'])/10)))
            self.figures[self.platforms[i]]['ax'].set_title("%s : %s most used words in %s theme. (Over %s posts)" % (self.platforms[i], self.Spinbox2.get(), self.Entry1.get(), self.Spinbox1.get()))
            self.figures[self.platforms[i]]['fig'].subplots_adjust(bottom=0.2)
            self.figures[self.platforms[i]]['ax'].axes.get_xaxis().set_label_text('')
            self.figures[self.platforms[i]]['ax'].axes.get_yaxis().set_label_text('Occurrence')
            print(self.figures[self.platforms[i]]['df'])
            
        self.TNotebook1.select(self.TNotebook1_t3)

    def refresh(self):
        if self.state == "Term Frequency" and not self.loaded:
            self.tfGui()
            self.loaded = True
        
    def destroyResults(self):
        self.PlotFrame.grid_rowconfigure(0, weight=0)
        self.PlotFrame.grid_rowconfigure(1, weight=0)
        self.PlotFrame.grid_columnconfigure(0, weight=0)
        self.PlotFrame.grid_columnconfigure(1, weight=0)
        for _,v in self.figures.items():
            v['widget'].get_tk_widget().destroy()
        
    def destroyNotebook(self):
        self.destroyResults()
        if self.state == "Term Frequency":
            self.Labelframe1.destroy()
            self.Labelframe2.destroy()
            self.Button1.destroy()
            self.Output.delete('1.0', tk.END)
            
    def start(self):
        while True:
            try:
                self.top.update_idletasks()
                self.top.update()
                self.refresh()
            except Exception as e:
                print(type(e), ':', e)
                break
            
    def updateNotebook(self, event):
        self.TCombobox1.selection_clear() # Used to remove highlight on element
        self.destroyNotebook()
        self.state = self.TCombobox1.get()
        self.loaded = False


if __name__ == '__main__':
    program = Program()
    program.start()

