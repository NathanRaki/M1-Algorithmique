import os
import re
import time
import pickle
import requests
import tkinter as tk
import tkinter.ttk as ttk
from matplotlib.ticker import MaxNLocator
import matplotlib.dates as mdates

import threading

import xmltodict
import pandas as pd
import urllib.request
import datetime as dt

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import nltk
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from gensim.parsing.preprocessing import STOPWORDS

def get_wordnet_pos(word) :
    tag = nltk.pos_tag([word])[0][1][0].upper()
    tags = {'J' : wordnet.ADJ,
            'N' : wordnet.NOUN,
            'V' : wordnet.VERB,
            'R' : wordnet.ADV}
    return tags.get(tag, wordnet.NOUN)

def nettoyer_texte(text):
    result = text.lower()
    result = result.replace('\n', ' ')
    result = re.sub("www", " ", result)
    result = re.sub("http", " ", result)
    result = re.sub(".com", " ", result)
    result = re.sub(".gg", " ", result)
    result = re.sub(r"[0-9,.;@\-\*\(\)/#?%!:|&$]+\ *", " ", result)
    result = re.sub("\[.*?\]", " " , result)
    result = re.sub(" +", " ", result)
    
    # Removing stopwords
    stopwords = set()
    stopwords.update(tuple(nltk.corpus.stopwords.words('english')))
    all_stopwords = STOPWORDS.union(stopwords)
    words = result.split()
    result = [word for word in words if word not in all_stopwords]
    
    # Lemmatize text
    lemmatizer = WordNetLemmatizer()
    result = [lemmatizer.lemmatize(word, get_wordnet_pos(word)) for word in result]
    
    result = ' '.join( [word for word in result if len(word)>1] )
    return result

def create_pickle(self, platform, keyword, number):
    
    count = 0
    number = int(number)
    keyword = keyword.lower()
    df = pd.DataFrame(columns=['title', 'date', 'url', 'text'])
    if platform == "reddit":
        url = "https://api.pushshift.io/reddit/submission/search?limit=1000&lang=en&sort=desc&subreddit={}&before={}"
        prev_time = round(time.time())
        
        while True:
            if count >= number:
                break
            try:
                new_url = url.format(keyword, str(prev_time))
                json = requests.get(new_url)
                json_data = json.json()
            except Exception as e:
                print("Error: %s" % e)
                continue
            
            if 'data' not in json_data:
                break
            docs = json_data['data']
            
            if len(docs) == 0:
                break
            
            for doc in docs:
                try:
                    txt = doc['selftext'].replace('\n', ' ').replace('\r', ' ')
                    df.loc[len(df)] = [doc['title'], doc['created_utc'], doc['url'], txt]
                    prev_time = doc['created_utc'] - 1
                    count += 1
                except Exception as e:
                    print("Error : %s" % e)
                    continue
                if count == number:
                    break
            self.progress_reddit_value = (count / number) * 100
            self.to_update = True
        self.progress_reddit_value = 100
        self.to_update = True
            
    elif platform == "arxiv":
        url = "http://export.arxiv.org/api/query?search_query=all:{}&start={}&max_results={}"
        while True:
            if count >= number:
                break
            try:
                new_url = url.format(keyword, str(count), str(count+2000))
                data = urllib.request.urlopen(new_url).read().decode()
                docs = xmltodict.parse(data)['feed']['entry']
            except Exception as e:
                print("Error: %s" % e)
                break
            
            if len(docs) == 0:
                break
            
            for doc in docs:
                date = dt.datetime.strptime(doc['published'], "%Y-%m-%dT%H:%M:%SZ")
                date = (date - dt.datetime(1970,1,1)).total_seconds()
                txt = doc['summary'].replace('\n', ' ').replace('\r', ' ')
                df.loc[len(df)] = [doc['title'], date, doc['id'], txt]
                count += 1
                if count == number:
                    break
            self.progress_arxiv_value = (count / number) * 100
            self.to_update = True
        self.progress_arxiv_value = 100
        self.to_update = True
    
    mindate = (dt.datetime(2017,1,1) - dt.datetime(1970,1,1)).total_seconds()
    df = df[~(df['date'] < mindate)]
    with open("saved/%s/%s-%s.pickle" % (platform, keyword.lower(), str(count)), "wb") as handle:
        pickle.dump(df, handle, protocol=pickle.HIGHEST_PROTOCOL)
    self.reload_saves()

class Program():
    
    def __init__(self):
        self.state = "Generate"
        self.loaded = False
        self.plots = dict()
        self.plotcoords = [(0,0), (0,1), (1,0), (1,1)]
        
        self.create_pickle = create_pickle
        
        self.progress_reddit_value = 0
        self.progress_arxiv_value = 0
        self.to_update = False
        
        self.threads = dict()
        self.saves = dict()
        self.saves["reddit"] = []
        self.saves["arxiv"] = []
        self.platforms_to_plot = []
        
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

        self.tk_categories = ttk.Combobox(self.top, state="readonly", values=["Generate", "Most Used Words", "Topic Trending"])
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
        
        self.progress_style = ttk.Style()
        self.progress_style.theme_use('clam')
        self.progress_style.configure("red.Horizontal.TProgressbar", foreground="red", background="red")
        
        self.progress_style_completed = ttk.Style()
        self.progress_style_completed.theme_use('clam')
        self.progress_style_completed.configure("green.Horizontal.TProgressbar", foreground="green", background="green")

    def GenerateGUI(self):
        
        print("Building -Generate- GUI page...")
        
        self.tk_frame_config = tk.LabelFrame(self.tk_notebook_config)
        self.tk_frame_config.place(relx=0.3, rely=0.05, relheight=0.4, relwidth=0.4)
        self.tk_frame_config.configure(background="#d9d9d9")
        self.tk_frame_config.configure(relief='groove')
        self.tk_frame_config.configure(text='''Generate Your Data''')
        
        for i in range(3):
            self.tk_frame_config.grid_columnconfigure(i, weight=1)
            
        self.tk_label_reddit = tk.Label(self.tk_frame_config)
        self.tk_label_reddit.grid(row=0, column=0, columnspan=3, sticky="nsew")
        self.tk_label_reddit.configure(text="Reddit")
        self.tk_label_reddit.configure(background="#d9d9d9")
        
        self.tk_label_topic_reddit = tk.Label(self.tk_frame_config)
        self.tk_label_topic_reddit.grid(row=1, column=0, sticky="e")
        self.tk_label_topic_reddit.configure(text="Topic : ")
        self.tk_label_topic_reddit.configure(background="#d9d9d9")
        
        self.tk_entry_reddit_topic = tk.Entry(self.tk_frame_config)
        self.tk_entry_reddit_topic.grid(row=1, column=1, sticky="nsew")
        self.tk_entry_reddit_topic.configure(background="#d9d9d9")
        
        self.tk_button_reddit_generate = tk.Button(self.tk_frame_config, width=10)
        self.tk_button_reddit_generate.grid(row=1, column=2, sticky="nsew", padx=5)
        self.tk_button_reddit_generate.configure(text="Generate")
        self.tk_button_reddit_generate.configure(command=(lambda: self.thread_func(create_pickle, "reddit", self.tk_entry_reddit_topic.get(), self.tk_spinbox_number_reddit.get())))
        
        self.tk_label_number_reddit = tk.Label(self.tk_frame_config)
        self.tk_label_number_reddit.grid(row=2, column=0, sticky="e")
        self.tk_label_number_reddit.configure(text="Number : ")
        self.tk_label_number_reddit.configure(background="#d9d9d9")
        
        self.tk_spinbox_number_reddit = tk.Spinbox(self.tk_frame_config, from_=1, to=10000)
        self.tk_spinbox_number_reddit.grid(row=2, column=1, sticky="nsew", pady=5)
        
        self.progress_reddit = ttk.Progressbar(self.tk_frame_config, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_reddit.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=30, pady=(5,15))
        
        self.tk_label_arxiv = tk.Label(self.tk_frame_config)
        self.tk_label_arxiv.grid(row=4, column=0, columnspan=3, sticky="nsew")
        self.tk_label_arxiv.configure(text="Arxiv")
        self.tk_label_arxiv.configure(background="#d9d9d9")
        
        self.tk_label_topic_arxiv = tk.Label(self.tk_frame_config)
        self.tk_label_topic_arxiv.grid(row=5, column=0, sticky="e")
        self.tk_label_topic_arxiv.configure(text="Topic : ")
        self.tk_label_topic_arxiv.configure(background="#d9d9d9")
        
        self.tk_entry_arxiv_topic = tk.Entry(self.tk_frame_config)
        self.tk_entry_arxiv_topic.grid(row=5, column=1, sticky="nsew")
        self.tk_entry_arxiv_topic.configure(background="#d9d9d9")
        
        self.tk_button_arxiv_generate = tk.Button(self.tk_frame_config, width=10)
        self.tk_button_arxiv_generate.grid(row=5, column=2, sticky="nsew", padx=5)
        self.tk_button_arxiv_generate.configure(text="Generate")
        self.tk_button_arxiv_generate.configure(command=(lambda: self.thread_func(create_pickle, "arxiv", self.tk_entry_arxiv_topic.get(), self.tk_spinbox_number_arxiv.get())))
        
        self.tk_label_number_arxiv = tk.Label(self.tk_frame_config)
        self.tk_label_number_arxiv.grid(row=6, column=0, sticky="e")
        self.tk_label_number_arxiv.configure(text="Number : ")
        self.tk_label_number_arxiv.configure(background="#d9d9d9")
        
        self.tk_spinbox_number_arxiv = tk.Spinbox(self.tk_frame_config, from_=1, to=10000)
        self.tk_spinbox_number_arxiv.grid(row=6, column=1, sticky="nsew", pady=5)
        
        self.progress_arxiv = ttk.Progressbar(self.tk_frame_config, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_arxiv.grid(row=7, column=0, columnspan=3, sticky="nsew", padx=30, pady=(5,15))
        
    def MostUsedWordsGUI(self):
        self.tk_frame_config = tk.LabelFrame(self.tk_notebook_config)
        self.tk_frame_config.place(relx=0.3, rely=0.05, relheight=0.4, relwidth=0.4)
        self.tk_frame_config.configure(background="#d9d9d9")
        self.tk_frame_config.configure(relief='groove')
        self.tk_frame_config.configure(text='''Generate Your Data''')
        
        for i in range(3):
            self.tk_frame_config.grid_columnconfigure(i, weight=1)
            
        self.tk_label_reddit = tk.Label(self.tk_frame_config)
        self.tk_label_reddit.grid(row=0, column=1, sticky="nsew")
        self.tk_label_reddit.configure(text="Reddit")
        self.tk_label_reddit.configure(background="#d9d9d9")
        
        self.tk_label_topic_reddit = tk.Label(self.tk_frame_config)
        self.tk_label_topic_reddit.grid(row=1, column=0, sticky="e")
        self.tk_label_topic_reddit.configure(text="Topic : ")
        self.tk_label_topic_reddit.configure(background="#d9d9d9")
        
        self.tk_combobox_reddit_topic = ttk.Combobox(self.tk_frame_config, state="readonly", values=self.saves["reddit"])
        self.tk_combobox_reddit_topic.grid(row=1, column=1, sticky="nsew", pady=(5,15))
        self.tk_combobox_reddit_topic.configure(background="#d9d9d9")
        
        self.tk_label_number_reddit = tk.Label(self.tk_frame_config)
        self.tk_label_number_reddit.grid(row=2, column=0, sticky="e")
        self.tk_label_number_reddit.configure(text="Number : ")
        self.tk_label_number_reddit.configure(background="#d9d9d9")
        
        self.tk_spinbox_number_reddit = tk.Spinbox(self.tk_frame_config, from_=1, to=30)
        self.tk_spinbox_number_reddit.grid(row=2, column=1, sticky="nsew", pady=5)
        self.tk_spinbox_number_reddit.configure(background="#d9d9d9")
        
        self.tk_label_arxiv = tk.Label(self.tk_frame_config)
        self.tk_label_arxiv.grid(row=3, column=1, sticky="nsew")
        self.tk_label_arxiv.configure(text="Arxiv")
        self.tk_label_arxiv.configure(background="#d9d9d9")
        
        self.tk_label_topic_arxiv = tk.Label(self.tk_frame_config)
        self.tk_label_topic_arxiv.grid(row=4, column=0, sticky="e")
        self.tk_label_topic_arxiv.configure(text="Topic : ")
        self.tk_label_topic_arxiv.configure(background="#d9d9d9")
        
        self.tk_combobox_arxiv_topic = ttk.Combobox(self.tk_frame_config, state="readonly", values=self.saves["arxiv"])
        self.tk_combobox_arxiv_topic.grid(row=4, column=1, sticky="nsew", pady=(5,15))
        self.tk_combobox_arxiv_topic.configure(background="#d9d9d9")
        
        self.tk_label_number_arxiv = tk.Label(self.tk_frame_config)
        self.tk_label_number_arxiv.grid(row=5, column=0, sticky="e")
        self.tk_label_number_arxiv.configure(text="Number : ")
        self.tk_label_number_arxiv.configure(background="#d9d9d9")
        
        self.tk_spinbox_number_arxiv = tk.Spinbox(self.tk_frame_config, from_=1, to=30)
        self.tk_spinbox_number_arxiv.grid(row=5, column=1, sticky="nsew", pady=5)
        self.tk_spinbox_number_arxiv.configure(background="#d9d9d9")
        
        self.tk_button_plot = tk.Button(self.tk_frame_config, width=10)
        self.tk_button_plot.grid(row=6, column=1, sticky="nsew")
        self.tk_button_plot.configure(text="Plot")
        self.tk_button_plot.configure(command=(lambda: self.MUWPlot()))
        
        self.reload_saves()
    
    def TopicTrendingGUI(self):
        self.tk_frame_config = tk.LabelFrame(self.tk_notebook_config)
        self.tk_frame_config.place(relx=0.3, rely=0.05, relheight=0.4, relwidth=0.4)
        self.tk_frame_config.configure(background="#d9d9d9")
        self.tk_frame_config.configure(relief='groove')
        self.tk_frame_config.configure(text='''Generate Your Data''')
        
        for i in range(3):
            self.tk_frame_config.grid_columnconfigure(i, weight=1)
            
        self.tk_label_reddit = tk.Label(self.tk_frame_config)
        self.tk_label_reddit.grid(row=0, column=1, sticky="nsew")
        self.tk_label_reddit.configure(text="Reddit")
        self.tk_label_reddit.configure(background="#d9d9d9")
        
        self.tk_label_topic_reddit = tk.Label(self.tk_frame_config)
        self.tk_label_topic_reddit.grid(row=1, column=0, sticky="e")
        self.tk_label_topic_reddit.configure(text="Topic : ")
        self.tk_label_topic_reddit.configure(background="#d9d9d9")
        
        self.tk_combobox_reddit_topic = ttk.Combobox(self.tk_frame_config, state="readonly", values=self.saves["reddit"])
        self.tk_combobox_reddit_topic.grid(row=1, column=1, sticky="nsew", pady=(5,15))
        self.tk_combobox_reddit_topic.configure(background="#d9d9d9")
        
        self.tk_label_arxiv = tk.Label(self.tk_frame_config)
        self.tk_label_arxiv.grid(row=2, column=1, sticky="nsew")
        self.tk_label_arxiv.configure(text="Arxiv")
        self.tk_label_arxiv.configure(background="#d9d9d9")
        
        self.tk_label_topic_arxiv = tk.Label(self.tk_frame_config)
        self.tk_label_topic_arxiv.grid(row=3, column=0, sticky="e")
        self.tk_label_topic_arxiv.configure(text="Topic : ")
        self.tk_label_topic_arxiv.configure(background="#d9d9d9")
        
        self.tk_combobox_arxiv_topic = ttk.Combobox(self.tk_frame_config, state="readonly", values=self.saves["arxiv"])
        self.tk_combobox_arxiv_topic.grid(row=3, column=1, sticky="nsew", pady=(5,15))
        self.tk_combobox_arxiv_topic.configure(background="#d9d9d9")
        
        self.tk_button_plot = tk.Button(self.tk_frame_config, width=10)
        self.tk_button_plot.grid(row=4, column=1, sticky="nsew")
        self.tk_button_plot.configure(text="Plot")
        self.tk_button_plot.configure(command=(lambda: self.TTPlot()))
        
        self.reload_saves()
        
    def thread_func(self, func, *args):
        self.threads[args[0]] = threading.Thread(target=self.create_pickle, args=(self,)+args)
        self.threads[args[0]].start()
        
    def reload_saves(self):
        self.saves["reddit"] = [""]
        self.saves["arxiv"] = [""]
        for filename in os.scandir("./saved/reddit"):
            self.saves["reddit"].append(re.sub(".pickle", "", filename.name))
            self.tk_combobox_reddit_topic.configure(values=self.saves["reddit"])
        for filename in os.scandir("./saved/arxiv"):
            self.saves["arxiv"].append(re.sub(".pickle", "", filename.name))
            self.tk_combobox_arxiv_topic.configure(values=self.saves["arxiv"])
        
    def MUWPlot(self):
        self.prepareResults()
        self.getPlatforms()
        for i in range(len(self.platforms_to_plot)):
            platform = self.platforms_to_plot[i]
            self.PlotFrame.grid_rowconfigure(self.plotcoords[i][0], weight=1)
            self.PlotFrame.grid_columnconfigure(self.plotcoords[i][1], weight=1)
            
            if platform == "reddit":
                number = self.tk_spinbox_number_reddit.get()
                keyword = self.tk_combobox_reddit_topic.get()
            elif platform == "arxiv":
                number = self.tk_spinbox_number_arxiv.get()
                keyword = self.tk_combobox_arxiv_topic.get()
            
            self.plots[platform] = dict()
            self.plots[platform]['fig'] = plt.Figure(figsize=(6,5), dpi=100)
            self.plots[platform]['ax'] = self.plots[platform]['fig'].add_subplot(111)
            
            self.plots[platform]['widget'] = FigureCanvasTkAgg(self.plots[platform]['fig'], self.PlotFrame)
            self.plots[platform]['widget'].get_tk_widget().grid(row=self.plotcoords[i][0], column=self.plotcoords[i][1], sticky="nsew")
            self.plots[platform]['widget'].get_tk_widget().configure(background="#000000")
            self.plots[platform]['widget'].get_tk_widget().configure(relief='groove')
            self.plots[platform]['widget'].get_tk_widget().configure(borderwidth="2")
            
            self.plots[platform]['df'] = self.MUW(platform, keyword, number)
            self.plots[platform]['df'].plot(kind='bar', legend=False, ax=self.plots[platform]['ax'])
            
            self.plots[platform]['ax'].set_xticklabels(self.plots[platform]['ax'].xaxis.get_majorticklabels(), rotation=45, fontsize=9)
            self.plots[platform]['ax'].yaxis.set_major_locator(MaxNLocator(integer=True))
            #self.plots[platform]['ax'].set_yticks(np.linspace(0, max(self.plots[platform]['df']['Count']), round(max(self.plots[platform]['df']['Count'])/10.)))
            self.plots[platform]['ax'].set_title("%s : %s most used words in %s theme" % (platform, number, keyword))
            self.plots[platform]['fig'].subplots_adjust(bottom=0.2)
            self.plots[platform]['ax'].axes.get_xaxis().set_label_text('')
            self.plots[platform]['ax'].axes.get_yaxis().set_label_text('Occurrence')
        self.tk_notebook.select(self.tk_notebook_results)
        
    def MUW(self, platform, keyword, number):
        try:
            with open('saved/%s/%s.pickle' % (platform, keyword), 'rb') as handle:
                df = pickle.load(handle)
        except Exception as e:
            print("Error : %s" % e)
            return
        
        ret = pd.DataFrame(columns=["Word", "Count"])
        text = ' '.join(df['text'])
        text = nettoyer_texte(text)
        freq = {}
        for word in text.split(" "):
            if word:
                freq[word] = freq[word] + 1 if word in freq else 1
        freq = {k: v for k, v in sorted(freq.items(), key=lambda item: item[1], reverse=True)}
        top_words = []
        for k,v in freq.items():
            if len(top_words) < int(number):
                top_words.append([k, v])
        for word in top_words:
            ret.loc[len(ret)] = word
        return ret.set_index('Word')
    
    def TTPlot(self):
        self.prepareResults()
        self.getPlatforms()
        for i in range(len(self.platforms_to_plot)):
            platform = self.platforms_to_plot[i]
            self.PlotFrame.grid_rowconfigure(self.plotcoords[i][0], weight=1)
            self.PlotFrame.grid_columnconfigure(self.plotcoords[i][1], weight=1)
            
            if platform == "reddit":
                keyword = self.tk_combobox_reddit_topic.get()
            elif platform == "arxiv":
                keyword = self.tk_combobox_arxiv_topic.get()
            
            self.plots[platform] = dict()
            self.plots[platform]['fig'] = plt.Figure(figsize=(6,5), dpi=100)
            self.plots[platform]['ax'] = self.plots[platform]['fig'].add_subplot(111)
            
            self.plots[platform]['widget'] = FigureCanvasTkAgg(self.plots[platform]['fig'], self.PlotFrame)
            self.plots[platform]['widget'].get_tk_widget().grid(row=self.plotcoords[i][0], column=self.plotcoords[i][1], sticky="nsew")
            self.plots[platform]['widget'].get_tk_widget().configure(background="#000000")
            self.plots[platform]['widget'].get_tk_widget().configure(relief='groove')
            self.plots[platform]['widget'].get_tk_widget().configure(borderwidth="2")
            
            self.plots[platform]['df'] = self.TT(platform, keyword)
            self.plots[platform]['df'].plot(legend=False, ax=self.plots[platform]['ax'])
            
            
            self.plots[platform]['ax'].set_title("%s Subreddit Trend" % keyword)
            self.plots[platform]['ax'].axes.get_xaxis().set_label_text('')
            
            self.plots[platform]['ax'].xaxis.set_major_formatter(mdates.DateFormatter("%m-%Y"))
            self.plots[platform]['ax'].xaxis.set_minor_formatter(mdates.DateFormatter("%d-%m-%Y"))
        self.tk_notebook.select(self.tk_notebook_results)
        
    def TT(self, platform, keyword):
        try:
            with open('saved/%s/%s.pickle' % (platform, keyword), 'rb') as handle:
                df = pickle.load(handle)
        except Exception as e:
            print("Error : %s" % e)
            return
        
        date_format = "%m-%Y"
        date = pd.to_datetime(df['date'], unit='s').dt.strftime(date_format)
        if len(date.drop_duplicates()) <= 2:
            print("YES")
            date_format = "%d-%m-%Y"
            date = pd.to_datetime(df['date'], unit='s').dt.strftime(date_format)
        df['date'] = date
        df = df.groupby('date').count()
        print(date_format)
        df.index = pd.to_datetime(df.index, format=date_format)
        df = df.sort_index()
        return df
    
    def getPlatforms(self):
        self.platforms_to_plot = []
        if self.tk_combobox_reddit_topic.get():
            self.platforms_to_plot.append("reddit")
        if self.tk_combobox_arxiv_topic.get():
            self.platforms_to_plot.append("arxiv")

    def prepareResults(self):
        self.destroyResults()
        self.PlotFrame = tk.Frame(self.tk_notebook_results)
        self.PlotFrame.place(relx=0.05, rely=0.05, relheight=0.9, relwidth=0.9)
        self.PlotFrame.configure(background="#d9d9d9")
        self.PlotFrame.configure(relief='groove')
        self.PlotFrame.configure(borderwidth="2")
        
        
    def destroyResults(self):
        if hasattr(self, 'PlotFrame'):
            self.PlotFrame.destroy()
        
    def updateNotebook(self, event):
        self.tk_categories.selection_clear() # Used to remove highlight on element
        self.destroyNotebook()
        self.state = self.tk_categories.get()
        self.tk_notebook.select(self.tk_notebook_config)
        self.loaded = False
        
    def destroyNotebook(self):
        self.destroyResults()
        self.tk_frame_config.destroy()
            
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
        if self.state == "Generate" and not self.loaded:
            self.GenerateGUI()
            self.loaded = True
        elif self.state == "Most Used Words" and not self.loaded:
            self.MostUsedWordsGUI()
            self.loaded = True
        elif self.state == "Topic Trending" and not self.loaded:
            self.TopicTrendingGUI()
            self.loaded = True
            
        if self.state == "Generate":
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
            
        
        if self.to_update:
            self.progress_reddit['value'] = self.progress_reddit_value
            self.progress_arxiv['value'] = self.progress_arxiv_value
            self.to_update = False


if __name__ == '__main__':
    program = Program()
    program.start()

