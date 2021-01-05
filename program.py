import os
import re
import scroll
import pickle
import tkinter as tk
import tkinter.ttk as ttk
from matplotlib.ticker import MaxNLocator

import trending

import threading

import praw
import xmltodict
import pandas as pd
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
                try:
                    #pprint.pprint(vars(post))
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
                except Exception as e:
                    print('Error: %s' % e)
        elif platform == "arxiv":
            url = "http://export.arxiv.org/api/query?search_query=all:%s&start=0&max_results=%s" % (keyword, str(nb))
            api = urllib.request.urlopen(url).read().decode()
            posts = xmltodict.parse(api)['feed']['entry']
            for post in posts:
                #pprint.pprint(post)
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
        self.plots = dict()
        self.corpuses = dict()
        self.plotcoords = [(0,0), (0,1), (1,0), (1,1)]
        
        self.trending_reddit = trending.reddit
        self.trending_arxiv = trending.arxiv
        self.trending_twitter = trending.twitter
        self.progress_reddit_value = 0
        self.progress_arxiv_value = 0
        self.progress_twitter_value = 0
        self.updateneeded = False
        
        self.threads = dict()
        
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

        self.tk_categories = ttk.Combobox(self.top, state="readonly", values=["Term Frequency", "Trending"])
        self.tk_categories.place(relx=0.350, rely=0.045, relheight=0.045, relwidth=0.3)
        self.tk_categories.configure(takefocus="")
        self.tk_categories.current(0)
        self.tk_categories.bind("<<ComboboxSelected>>", self.updateNotebook)

        self.tk_mainFrame = tk.Frame(self.top)
        self.tk_mainFrame.place(relx=0.002, rely=0.120, relheight=0.8, relwidth=0.996)
        self.tk_mainFrame.configure(relief='groove')
        self.tk_mainFrame.configure(borderwidth="2")

        self.tk_notebook = ttk.Notebook(self.tk_mainFrame)
        self.tk_notebook.place(relx=0.01, rely=0.017, relheight=0.962, relwidth=0.973)
        self.tk_notebook.configure(takefocus="")
        self.tk_notebook_config = tk.Frame(self.tk_notebook)
        self.tk_notebook_config.configure(background="#d9d9d9")
        self.tk_notebook.add(self.tk_notebook_config, padding=3)
        self.tk_notebook.tab(0, text="Config",compound="left",underline="-1",)
        self.tk_notebook_results = tk.Frame(self.tk_notebook)
        self.tk_notebook_results.configure(background="#d9d9d9")
        self.tk_notebook.add(self.tk_notebook_results, padding=3)
        self.tk_notebook.tab(1, text="Results",compound="left",underline="-1",)
        self.tk_notebook_debug = tk.Frame(self.tk_notebook)
        self.tk_notebook_debug.configure(background="#d9d9d9")
        self.tk_notebook.add(self.tk_notebook_debug, padding=3)
        self.tk_notebook.tab(2, text="Debug",compound="left",underline="-1",)

    def tfGui(self):
        self.tk_frame_platform = tk.LabelFrame(self.tk_notebook_config)
        self.tk_frame_platform.place(relx=0.064, rely=0.076, relheight=0.294, relwidth=0.126)
        self.tk_frame_platform.configure(background="#d9d9d9")
        self.tk_frame_platform.configure(relief='groove')
        self.tk_frame_platform.configure(text='''Select Source''')

        self.reddit = tk.IntVar()
        self.arxiv = tk.IntVar()
        self.twitter = tk.IntVar()
        
        self.tk_check_reddit = tk.Checkbutton(self.tk_frame_platform, variable=self.reddit)
        self.tk_check_reddit.place(relx=0.085, rely=0.194, relheight=0.135, relwidth=0.788, bordermode='ignore')
        self.tk_check_reddit.configure(background="#d9d9d9")
        self.tk_check_reddit.configure(activebackground="#e9e9e9")
        self.tk_check_reddit.configure(highlightthickness=0)
        self.tk_check_reddit.configure(justify='left')
        self.tk_check_reddit.configure(text='''Reddit''')

        self.tk_check_arxiv = tk.Checkbutton(self.tk_frame_platform, variable=self.arxiv)
        self.tk_check_arxiv.place(relx=0.085, rely=0.387, relheight=0.135, relwidth=0.788, bordermode='ignore')
        self.tk_check_arxiv.configure(background="#d9d9d9")
        self.tk_check_arxiv.configure(activebackground="#e9e9e9")
        self.tk_check_arxiv.configure(highlightthickness=0)
        self.tk_check_arxiv.configure(justify='left')
        self.tk_check_arxiv.configure(text='''Arxiv''')

        self.tk_check_twitter = tk.Checkbutton(self.tk_frame_platform, variable=self.twitter)
        self.tk_check_twitter.place(relx=0.085, rely=0.581, relheight=0.135, relwidth=0.788, bordermode='ignore')
        self.tk_check_twitter.configure(background="#d9d9d9")
        self.tk_check_twitter.configure(activebackground="#e9e9e9")
        self.tk_check_twitter.configure(highlightthickness=0)
        self.tk_check_twitter.configure(justify='left')
        self.tk_check_twitter.configure(text='''Twitter''')

        self.tk_frame_parameters = tk.LabelFrame(self.tk_notebook_config)
        self.tk_frame_parameters.place(relx=0.214, rely=0.076, relheight=0.237, relwidth=0.298)
        self.tk_frame_parameters.configure(background="#d9d9d9")
        self.tk_frame_parameters.configure(relief='groove')
        self.tk_frame_parameters.configure(text='''Parameters''')
        self.tk_frame_parameters.grid_rowconfigure(0, weight=1)
        self.tk_frame_parameters.grid_rowconfigure(1, weight=1)
        self.tk_frame_parameters.grid_rowconfigure(2, weight=1)
        self.tk_frame_parameters.grid_columnconfigure(0, weight=1)
        self.tk_frame_parameters.grid_columnconfigure(1, weight=1)

        self.tk_postQuantity = tk.Spinbox(self.tk_frame_parameters, from_=1.0, to=1000.0)
        #self.tk_postQuantity.place(relx=0.287, rely=0.64, relheight=0.168, relwidth=0.283, bordermode='ignore')
        self.tk_postQuantity.grid(row=1, column=1, sticky="nsew")
        self.tk_postQuantity.configure(activebackground="#f9f9f9")
        self.tk_postQuantity.configure(background="white")
        self.tk_postQuantity.configure(font="TkDefaultFont")
        self.tk_postQuantity.configure(highlightbackground="black")
        self.tk_postQuantity.configure(selectbackground="blue")
        self.tk_postQuantity.configure(selectforeground="white")

        self.tk_entry_keyword = tk.Entry(self.tk_frame_parameters)
        #self.tk_entry_keyword.place(relx=0.287, rely=0.4, height=21, relwidth=0.595, bordermode='ignore')
        self.tk_entry_keyword.grid(row=0, column=1, sticky="nsew")
        self.tk_entry_keyword.configure(background="white")
        self.tk_entry_keyword.configure(font="TkFixedFont")
        
        self.tk_topwordQuantity = tk.Spinbox(self.tk_frame_parameters, from_=1.0, to=1000.0)
        self.tk_topwordQuantity.grid(row=2, column=1, sticky="nsew")
        self.tk_topwordQuantity.configure(activebackground="#f9f9f9")
        self.tk_topwordQuantity.configure(background="white")
        self.tk_topwordQuantity.configure(font="TkDefaultFont")
        self.tk_topwordQuantity.configure(highlightbackground="black")
        self.tk_topwordQuantity.configure(selectbackground="blue")
        self.tk_topwordQuantity.configure(selectforeground="white")

        self.tk_label_keyword = tk.Label(self.tk_frame_parameters)
        #self.tk_label_keyword.place(relx=0.036, rely=0.4, height=19, width=66, bordermode='ignore')
        self.tk_label_keyword.grid(row=0, column=0, sticky="nsew")
        self.tk_label_keyword.configure(text='''Keyword''')

        self.tk_label_postQuantity = tk.Label(self.tk_frame_parameters)
        #self.tk_label_postQuantity.place(relx=0.036, rely=0.64, height=19, width=66, bordermode='ignore')
        self.tk_label_postQuantity.grid(row=1, column=0, sticky="nsew")
        self.tk_label_postQuantity.configure(activebackground="#f9f9f9")
        self.tk_label_postQuantity.configure(text='''Quantity''')
        
        self.tk_label_topwordQuantity = tk.Label(self.tk_frame_parameters)
        #self.tk_label_topwordQuantity.place(relx=0.036, rely=0.64, height=19, width=66, bordermode='ignore')
        self.tk_label_topwordQuantity.grid(row=2, column=0, sticky="nsew")
        self.tk_label_topwordQuantity.configure(activebackground="#f9f9f9")
        self.tk_label_topwordQuantity.configure(text='''Top''')
        
        self.tk_button_generate = tk.Button(self.tk_notebook_config)
        self.tk_button_generate.place(relx=0.578, rely=0.152, height=29, width=69)
        self.tk_button_generate.configure(text='''Generate''')
        self.tk_button_generate.configure(command=self.generate)
        
        self.Output = scroll.ScrolledText(self.tk_notebook_debug)
        self.Output.place(relx=0.022, rely=0.032, relheight=0.933, relwidth=0.954)
        self.Output.configure(background="#5f5f5f")
        self.Output.configure(borderwidth="2")
        self.Output.configure(wrap="none")
        
    def trGui(self):
        self.reddit_saves = []
        self.arxiv_saves = []
        self.twitter_saves = []
        
        self.tk_frame_parameters = tk.LabelFrame(self.tk_notebook_config)
        self.tk_frame_parameters.place(relx=0.01, rely=0.01, relheight=0.5, relwidth=0.3)
        self.tk_frame_parameters.configure(background="#d9d9d9")
        self.tk_frame_parameters.configure(relief='groove')
        self.tk_frame_parameters.configure(text='''Parameters''')
        
        for i in range(3):
            self.tk_frame_parameters.grid_columnconfigure(i, weight=1)
            
        self.progress_style = ttk.Style()
        self.progress_style.theme_use('clam')
        self.progress_style.configure("red.Horizontal.TProgressbar", foreground="red", background="red")
        
        self.progress_style_completed = ttk.Style()
        self.progress_style_completed.theme_use('clam')
        self.progress_style_completed.configure("green.Horizontal.TProgressbar", foreground="green", background="green")
            
        self.tk_label_reddit = tk.Label(self.tk_frame_parameters)
        self.tk_label_reddit.grid(row=0, column=0, columnspan=3, sticky="nsew")
        self.tk_label_reddit.configure(text="Reddit")
        self.tk_label_reddit.configure(background="#d9d9d9")
        
        self.tk_label_topic_reddit = tk.Label(self.tk_frame_parameters)
        self.tk_label_topic_reddit.grid(row=1, column=0, sticky="e")
        self.tk_label_topic_reddit.configure(text="Topic : ")
        self.tk_label_topic_reddit.configure(background="#d9d9d9")
        
        self.tk_entry_reddit_topic = tk.Entry(self.tk_frame_parameters)
        self.tk_entry_reddit_topic.grid(row=1, column=1, sticky="nsew")
        self.tk_entry_reddit_topic.configure(background="#d9d9d9")
        
        self.tk_button_reddit_generate = tk.Button(self.tk_frame_parameters, width=10)
        self.tk_button_reddit_generate.grid(row=1, column=2, sticky="nsew", padx=5)
        self.tk_button_reddit_generate.configure(text="Generate")
        self.tk_button_reddit_generate.configure(command=(lambda: self.gen_trend("reddit")))
        
        self.progress_reddit = ttk.Progressbar(self.tk_frame_parameters, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_reddit.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=30, pady=(5,15))
        
        self.tk_label_arxiv = tk.Label(self.tk_frame_parameters)
        self.tk_label_arxiv.grid(row=3, column=0, columnspan=3, sticky="nsew")
        self.tk_label_arxiv.configure(text="Arxiv")
        self.tk_label_arxiv.configure(background="#d9d9d9")
        
        self.tk_label_topic_arxiv = tk.Label(self.tk_frame_parameters)
        self.tk_label_topic_arxiv.grid(row=4, column=0, sticky="e")
        self.tk_label_topic_arxiv.configure(text="Topic : ")
        self.tk_label_topic_arxiv.configure(background="#d9d9d9")
        
        self.tk_entry_arxiv_topic = tk.Entry(self.tk_frame_parameters)
        self.tk_entry_arxiv_topic.grid(row=4, column=1, sticky="nsew")
        self.tk_entry_arxiv_topic.configure(background="#d9d9d9")
        
        self.tk_button_arxiv_generate = tk.Button(self.tk_frame_parameters, width=10)
        self.tk_button_arxiv_generate.grid(row=4, column=2, sticky="nsew", padx=5)
        self.tk_button_arxiv_generate.configure(text="Generate")
        self.tk_button_arxiv_generate.configure(command=(lambda: self.gen_trend("arxiv")))
        
        self.progress_arxiv = ttk.Progressbar(self.tk_frame_parameters, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_arxiv.grid(row=5, column=0, columnspan=3, sticky="nsew", padx=30, pady=(5,15))
        
        self.tk_label_twitter = tk.Label(self.tk_frame_parameters)
        self.tk_label_twitter.grid(row=6, column=0, columnspan=3, sticky="nsew")
        self.tk_label_twitter.configure(text="Twitter")
        self.tk_label_twitter.configure(background="#d9d9d9")
        
        self.tk_label_topic_twitter = tk.Label(self.tk_frame_parameters)
        self.tk_label_topic_twitter.grid(row=7, column=0, sticky="e")
        self.tk_label_topic_twitter.configure(text="Topic : ")
        self.tk_label_topic_twitter.configure(background="#d9d9d9")
        
        self.tk_entry_twitter_topic = tk.Entry(self.tk_frame_parameters)
        self.tk_entry_twitter_topic.grid(row=7, column=1, sticky="nsew", padx=5)
        self.tk_entry_twitter_topic.configure(background="#d9d9d9")
        
        self.tk_button_twitter_generate = tk.Button(self.tk_frame_parameters, width=10)
        self.tk_button_twitter_generate.grid(row=7, column=2, sticky="nsew", padx=5)
        self.tk_button_twitter_generate.configure(text="Generate")
        self.tk_button_twitter_generate.configure(command=(lambda: self.gen_trend("twitter")))
        
        self.progress_twitter = ttk.Progressbar(self.tk_frame_parameters, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_twitter.grid(row=8, column=0, columnspan=3, sticky="nsew", padx=30, pady=(5,15))
        
        ####
        self.tk_frame_plotting = tk.LabelFrame(self.tk_notebook_config)
        self.tk_frame_plotting.place(relx=0.31, rely=0.01, relheight=0.5, relwidth=0.3)
        self.tk_frame_plotting.configure(background="#d9d9d9")
        self.tk_frame_plotting.configure(relief='groove')
        self.tk_frame_plotting.configure(text='''Plotting''')
        
        for i in range(3):
            self.tk_frame_plotting.grid_columnconfigure(i, weight=1)
            
        self.tk_label_reddit_plot = tk.Label(self.tk_frame_plotting)
        self.tk_label_reddit_plot.grid(row=0, column=0, columnspan=3, sticky="nsew")
        self.tk_label_reddit_plot.configure(text="Reddit")
        self.tk_label_reddit_plot.configure(background="#d9d9d9")
        
        self.tk_label_topic_reddit_plot = tk.Label(self.tk_frame_plotting)
        self.tk_label_topic_reddit_plot.grid(row=1, column=0, sticky="e", pady=(5,15))
        self.tk_label_topic_reddit_plot.configure(text="Topic : ")
        self.tk_label_topic_reddit_plot.configure(background="#d9d9d9")
        
        self.tk_combobox_reddit_topic = ttk.Combobox(self.tk_frame_plotting, state="readonly", values=self.reddit_saves)
        self.tk_combobox_reddit_topic.grid(row=1, column=1, sticky="nsew", pady=(5,15))
        self.tk_combobox_reddit_topic.configure(background="#d9d9d9")
        
        self.tk_button_reddit_plot = tk.Button(self.tk_frame_plotting, width=10)
        self.tk_button_reddit_plot.grid(row=1, column=2, sticky="nsew", padx=5, pady=(5,15))
        self.tk_button_reddit_plot.configure(text="Generate")
        #self.tk_button_reddit_plot.configure(command=(lambda: self.gen_trend("reddit")))
        
        self.tk_label_arxiv_plot = tk.Label(self.tk_frame_plotting)
        self.tk_label_arxiv_plot.grid(row=2, column=0, columnspan=3, sticky="nsew")
        self.tk_label_arxiv_plot.configure(text="Arxiv")
        self.tk_label_arxiv_plot.configure(background="#d9d9d9")
        
        self.tk_label_topic_arxiv_plot = tk.Label(self.tk_frame_plotting)
        self.tk_label_topic_arxiv_plot.grid(row=3, column=0, sticky="e", pady=(5,15))
        self.tk_label_topic_arxiv_plot.configure(text="Topic : ")
        self.tk_label_topic_arxiv_plot.configure(background="#d9d9d9")
        
        self.tk_combobox_arxiv_topic = ttk.Combobox(self.tk_frame_plotting, state="readonly", values=self.arxiv_saves)
        self.tk_combobox_arxiv_topic.grid(row=3, column=1, sticky="nsew", pady=(5,15))
        self.tk_combobox_arxiv_topic.configure(background="#d9d9d9")
        
        self.tk_button_arxiv_plot = tk.Button(self.tk_frame_plotting, width=10)
        self.tk_button_arxiv_plot.grid(row=3, column=2, sticky="nsew", padx=5, pady=(5,15))
        self.tk_button_arxiv_plot.configure(text="Generate")
        #self.tk_button_arxiv_plot.configure(command=(lambda: self.gen_trend("arxiv")))
        
        self.tk_label_twitter_plot = tk.Label(self.tk_frame_plotting)
        self.tk_label_twitter_plot.grid(row=4, column=0, columnspan=3, sticky="nsew")
        self.tk_label_twitter_plot.configure(text="Twitter")
        self.tk_label_twitter_plot.configure(background="#d9d9d9")
        
        self.tk_label_topic_twitter_plot = tk.Label(self.tk_frame_plotting)
        self.tk_label_topic_twitter_plot.grid(row=5, column=0, sticky="e", pady=(5,15))
        self.tk_label_topic_twitter_plot.configure(text="Topic : ")
        self.tk_label_topic_twitter_plot.configure(background="#d9d9d9")
        
        self.tk_combobox_twitter_topic = ttk.Combobox(self.tk_frame_plotting, state="readonly", values=self.twitter_saves)
        self.tk_combobox_twitter_topic.grid(row=5, column=1, sticky="nsew", pady=(5,15))
        self.tk_combobox_twitter_topic.configure(background="#d9d9d9")
        
        self.tk_button_twitter_plot = tk.Button(self.tk_frame_plotting, width=10)
        self.tk_button_twitter_plot.grid(row=5, column=2, sticky="nsew", padx=5, pady=(5,15))
        self.tk_button_twitter_plot.configure(text="Generate")
        #self.tk_button_twitter_plot.configure(command=(lambda: self.gen_trend("twitter")))
        
        self.reload_saves()
        
    def reload_saves(self):
        self.reddit_saves = []
        self.arxiv_saves = []
        self.twitter_saves = []
        for filename in os.scandir("./saved/reddit"):
            self.reddit_saves.append(re.sub(".pickle", "", filename.name))
            self.tk_combobox_reddit_topic.configure(values=self.reddit_saves)
        
    def gen_trend(self, platform):
        #self.progress = ttk.Progressbar(self.tk_frame_parameters, orient=tk.HORIZONTAL, length=100, mode='determinate')
        #self.progress.grid(row=4, column=0, columnspan=2, sticky="nsew")
        if platform == "reddit":
            keyword = self.tk_entry_reddit_topic.get()
            
            self.progress_reddit['value'] = 0
            self.threads[platform] = threading.Thread(target=trending.reddit, args=[self, keyword])
            self.threads[platform].start()
        elif platform == "arxiv":
            keyword = self.tk_entry_arxiv_topic.get()
            threading.Thread(target=trending.arxiv, args=[self, keyword]).start()
        elif platform == "twitter":
            keyword = self.tk_entry_twitter_topic.get()
            threading.Thread(target=trending.twitter, args=[self, keyword]).start()
            
        #self.tk_label_warning.configure(text="Generating data for %s..." % keyword)
       
    
    def timeplots(self):
        self.prepareResults()
        if len(self.platforms) == 0:
            self.tk_label_warning.configure(text="Please select at least one platform to plot from.")
            return
        for i in range(len(self.platforms)):
            self.PlotFrame.grid_rowconfigure(self.plotcoords[i][0], weight=1)
            self.PlotFrame.grid_columnconfigure(self.plotcoords[i][1], weight=1)
            self.plots[self.platforms[i]] = dict()
            self.plots[self.platforms[i]]['fig'] = plt.Figure(figsize=(6,5), dpi=100)
            self.plots[self.platforms[i]]['ax'] = self.plots[self.platforms[i]]['fig'].add_subplot(111)
            self.plots[self.platforms[i]]['widget'] = FigureCanvasTkAgg(self.plots[self.platforms[i]]['fig'], self.PlotFrame)
            self.plots[self.platforms[i]]['widget'].get_tk_widget().grid(row=self.plotcoords[i][0], column=self.plotcoords[i][1], sticky="nsew")
            self.plots[self.platforms[i]]['widget'].get_tk_widget().configure(background="#000000")
            self.plots[self.platforms[i]]['widget'].get_tk_widget().configure(relief='groove')
            self.plots[self.platforms[i]]['widget'].get_tk_widget().configure(borderwidth="2")
            self.plots[self.platforms[i]]['ax'].set_title("%s Subreddit Trend" % self.tk_entry_keyword.get())
            self.plots[self.platforms[i]]['ax'].axes.get_xaxis().set_label_text('')
            
            try:
                with open('%s-%s.pickle' % (self.platforms[i], self.tk_entry_keyword.get().lower()), 'rb') as handle:
                    df = pickle.load(handle)
            except Exception as e:
                print(e)
                self.tk_label_warning.configure(text="File not found, please use generate button with this keyword to import data from API.")
                return

            df['created_utc'] = pd.to_datetime(df['created_utc'], unit='s').dt.strftime("%d-%m-%Y")
            df = df.groupby('created_utc').count()
            df.index = pd.to_datetime(df.index, format="%d-%m-%Y")
            df = df.sort_index()
            df.plot(legend=False, ax=self.plots[self.platforms[i]]['ax'])
            
        self.tk_notebook.select(self.tk_notebook_results)
        
    def generate(self):
        self.prepareResults()
        for platform in self.platforms:
            self.corpuses[platform] = genCorpus(platform, int(self.tk_postQuantity.get()), self.tk_entry_keyword.get())
            self.Output.insert(tk.END, self.corpuses[platform].stats())
            self.Output.see("end")
            
        for i in range(len(self.platforms)):
            self.PlotFrame.grid_rowconfigure(self.plotcoords[i][0], weight=1)
            self.PlotFrame.grid_columnconfigure(self.plotcoords[i][1], weight=1)
            self.plots[self.platforms[i]] = dict()
            self.plots[self.platforms[i]]['fig'] = plt.Figure(figsize=(6,5), dpi=100)
            self.plots[self.platforms[i]]['ax'] = self.plots[self.platforms[i]]['fig'].add_subplot(111)
            self.plots[self.platforms[i]]['widget'] = FigureCanvasTkAgg(self.plots[self.platforms[i]]['fig'], self.PlotFrame)
            self.plots[self.platforms[i]]['widget'].get_tk_widget().grid(row=self.plotcoords[i][0], column=self.plotcoords[i][1], sticky="nsew")
            self.plots[self.platforms[i]]['widget'].get_tk_widget().configure(background="#000000")
            self.plots[self.platforms[i]]['widget'].get_tk_widget().configure(relief='groove')
            self.plots[self.platforms[i]]['widget'].get_tk_widget().configure(borderwidth="2")
            self.plots[self.platforms[i]]['df'] = self.corpuses[self.platforms[i]].topwords(int(self.tk_topwordQuantity.get()))
            self.plots[self.platforms[i]]['df'].plot(kind='bar', legend=False, ax=self.plots[self.platforms[i]]['ax'])
            self.plots[self.platforms[i]]['ax'].set_xticklabels(self.plots[self.platforms[i]]['ax'].xaxis.get_majorticklabels(), rotation=45, fontsize=9)
            self.plots[self.platforms[i]]['ax'].yaxis.set_major_locator(MaxNLocator(integer=True))
            #self.plots[self.platforms[i]]['ax'].set_yticks(np.linspace(0, max(self.plots[self.platforms[i]]['df']['Count']), round(max(self.plots[self.platforms[i]]['df']['Count'])/10.)))
            self.plots[self.platforms[i]]['ax'].set_title("%s : %s most used words in %s theme. (Over %s posts)" % (self.platforms[i], self.tk_topwordQuantity.get(), self.tk_entry_keyword.get(), self.tk_postQuantity.get()))
            self.plots[self.platforms[i]]['fig'].subplots_adjust(bottom=0.2)
            self.plots[self.platforms[i]]['ax'].axes.get_xaxis().set_label_text('')
            self.plots[self.platforms[i]]['ax'].axes.get_yaxis().set_label_text('Occurrence')
            print(self.plots[self.platforms[i]]['df'])
            
        self.tk_notebook.select(self.tk_notebook_results)
            
    def prepareResults(self):
        self.destroyResults()
        self.platforms = list()
        if self.reddit.get():
            self.platforms.append("reddit")
        if self.arxiv.get():
            self.platforms.append("arxiv")
        if self.twitter.get():
            self.platforms.append("twitter")
        
        self.PlotFrame = tk.Frame(self.tk_notebook_results)
        self.PlotFrame.place(relx=0.05, rely=0.05, relheight=0.9, relwidth=0.9)
        self.PlotFrame.configure(background="#d9d9d9")
        self.PlotFrame.configure(relief='groove')
        self.PlotFrame.configure(borderwidth="2")
        
        
    def destroyResults(self):
        if hasattr(self, 'PlotFrame'):
            self.PlotFrame.destroy()
        for _,v in self.plots.items():
            v['widget'].get_tk_widget().destroy()
        
    def updateNotebook(self, event):
        self.tk_categories.selection_clear() # Used to remove highlight on element
        self.destroyNotebook()
        self.state = self.tk_categories.get()
        self.loaded = False
        
    def destroyNotebook(self):
        self.destroyResults()
        if self.state == "Term Frequency":
            self.tk_frame_platform.destroy()
            self.tk_frame_parameters.destroy()
            self.tk_button_generate.destroy()
            self.Output.delete('1.0', tk.END)
        if self.state == "Trending":
            self.tk_frame_parameters.destroy()
            self.tk_frame_plotting.destroy()
            
    def start(self):
        while True:
            try:
                self.top.update_idletasks()
                self.top.update()
                self.refresh()
            except Exception as e:
                print(type(e), ':', e)
                break
            
    def refresh(self):
        if self.state == "Term Frequency" and not self.loaded:
            self.tfGui()
            self.loaded = True
        elif self.state == "Trending" and not self.loaded:
            self.trGui()
            self.loaded = True
            
        if self.state == "Trending":
            if "reddit" in self.threads:
                if self.threads["reddit"].is_alive():
                    self.progress_reddit.configure(style="red.Horizontal.TProgressbar")
                    self.tk_button_reddit_generate.config(text="Generating...")
                    self.tk_button_reddit_generate['state'] = 'disabled'
                else:
                    self.progress_reddit.configure(style="green.Horizontal.TProgressbar")
                    self.tk_button_reddit_generate.config(text="Generate")
                    self.tk_button_reddit_generate['state'] = 'normal'
            if "arxiv" in self.threads:
                if self.threads["arxiv"].is_alive():
                    self.progress_arxiv.configure(style="red.Horizontal.TProgressbar")
                    self.tk_button_arxiv_generate.config(text="Generating...")
                    self.tk_button_arxiv_generate['state'] = 'disabled'
                else:
                    self.progress_arxiv.configure(style="green.Horizontal.TProgressbar")
                    self.tk_button_arxiv_generate.config(text="Generate")
                    self.tk_button_arxiv_generate['state'] = 'normal'
            if "twitter" in self.threads:
                if self.threads["twitter"].is_alive():
                    self.progress_twitter.configure(style="red.Horizontal.TProgressbar")
                    self.tk_button_twitter_generate.config(text="Generating...")
                    self.tk_button_twitter_generate['state'] = 'disabled'
                else:
                    self.progress_twitter.configure(style="green.Horizontal.TProgressbar")
                    self.tk_button_twitter_generate.config(text="Generate")
                    self.tk_button_twitter_generate['state'] = 'normal'
            
        if self.updateneeded:
            if(self.progress_reddit_value == 100):
                self.reload_saves()
            self.progress_reddit['value'] = self.progress_reddit_value
            self.progress_arxiv['value'] = self.progress_arxiv_value
            self.progress_twitter['value'] = self.progress_twitter_value
            self.updateneeded = False


if __name__ == '__main__':
    program = Program()
    program.start()

