# Importing Modules and Functions
import os
import re
import time
import pickle
import requests
import threading
import xmltodict
import pandas as pd
import tkinter as tk
import urllib.request
import datetime as dt
import tkinter.ttk as ttk
import matplotlib.pyplot as plt
from nltk.stem import WordNetLemmatizer
from matplotlib.ticker import MaxNLocator
from gensim.parsing.preprocessing import STOPWORDS
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Global variables, used to make custom threads communicate with the main thread
df_arxiv = "" # DataFrame used to store arxiv plotting data
df_reddit = "" # DataFrame used to store reddit plotting data
to_plot = False # Flag, true when plotting data has been loaded
to_update = False # Flag, true when generation progress bar needs update
progress_arxiv_value = 0 # Arxiv progress bar value
progress_reddit_value = 0 # Reddit progress bar value

class Program():
    # Initialization
    def __init__(self):
        self.state = "Generate" # Initialize the GUI state
        self.loaded = False # Flag, False when GUI needs to be changed
        self.saves = dict()
        self.saves["reddit"] = [] # List reddit's saves
        self.saves["arxiv"] = [] # List arxiv's saves
        self.threads = dict() # Dict to store our custom threads
        self.plots = dict() # Dict to store our plotting data
        self.platforms_to_plot = [] # List of platforms selected by user
        self.plotcoords = [(0,0), (0,1), (1,0), (1,1)] # Coords to use with tkinter grid for plots
        
        self.top = tk.Tk() # Main tkinter window

        # Centering the tkinter window to screen
        w = 1280 # width
        h = 720 # height
        ws = self.top.winfo_screenwidth() # screenwidth
        hs = self.top.winfo_screenheight() # screenheight
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)

        # Configuring tkinter main window
        self.top.geometry("%dx%d+%d+%d" % (w, h, x, y))
        self.top.minsize(1, 1)
        self.top.maxsize(1920, 1080)
        self.top.resizable(1,  1)
        self.top.title("Corpus Analyze")

        # Scrolling Menu for our main Categories (Generate / MostUsedWords / TopicTrending)
        self.tk_categories = ttk.Combobox(self.top, state="readonly", values=["Generate", "Most Used Words", "Topic Trending"])
        self.tk_categories.place(relx=0.350, rely=0.045, relheight=0.045, relwidth=0.3)
        self.tk_categories.configure(takefocus="")
        self.tk_categories.current(0)
        self.tk_categories.bind("<<ComboboxSelected>>", self.updateNotebook)

        # Main Frame, right below the categories scrolling menu
        self.tk_mainFrame = tk.Frame(self.top)
        self.tk_mainFrame.place(relx=0.002, rely=0.120, relheight=0.8, relwidth=0.996)
        self.tk_mainFrame.configure(relief='groove')
        self.tk_mainFrame.configure(borderwidth="2")

        # Tkinter notebook to have multiple tabs for configuration and results
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
        
        # Initializing our ProgressBar styles (incomplete/complete)
        self.progress_style = ttk.Style()
        self.progress_style.theme_use('clam')
        self.progress_style.configure("red.Horizontal.TProgressbar", foreground="red", background="red")
        
        self.progress_style_completed = ttk.Style()
        self.progress_style_completed.theme_use('clam')
        self.progress_style_completed.configure("green.Horizontal.TProgressbar", foreground="green", background="green")

    # Build GUI for Generate category
    def GenerateGUI(self):
        # Main frame for config tab
        self.tk_frame_config = tk.LabelFrame(self.tk_notebook_config)
        self.tk_frame_config.place(relx=0.3, rely=0.05, relheight=0.6, relwidth=0.4)
        self.tk_frame_config.configure(background="#d9d9d9")
        self.tk_frame_config.configure(relief='groove')
        self.tk_frame_config.configure(text="Generate Your Data")
        
        # Configuring frame columns for grid
        for i in range(3):
            self.tk_frame_config.grid_columnconfigure(i, weight=1)
            
        # Reddit Label
        self.tk_label_reddit = tk.Label(self.tk_frame_config)
        self.tk_label_reddit.grid(row=0, column=0, columnspan=3, sticky="nsew")
        self.tk_label_reddit.configure(text="Reddit")
        self.tk_label_reddit.configure(background="#d9d9d9")
        
        # Reddit Topic Label
        self.tk_label_topic_reddit = tk.Label(self.tk_frame_config)
        self.tk_label_topic_reddit.grid(row=1, column=0, sticky="e")
        self.tk_label_topic_reddit.configure(text="Topic : ")
        self.tk_label_topic_reddit.configure(background="#d9d9d9")
        
        # Reddit Topic Entry
        self.tk_entry_reddit_topic = tk.Entry(self.tk_frame_config)
        self.tk_entry_reddit_topic.grid(row=1, column=1, sticky="nsew")
        self.tk_entry_reddit_topic.configure(background="#d9d9d9")
        
        # Reddit Generate Button
        self.tk_button_reddit_generate = tk.Button(self.tk_frame_config, width=10)
        self.tk_button_reddit_generate.grid(row=1, column=2, sticky="nsew", padx=5)
        self.tk_button_reddit_generate.configure(text="Generate")
        self.tk_button_reddit_generate.configure(command=(lambda: self.thread_func(create_pickle, "reddit", self.tk_entry_reddit_topic.get(), self.tk_spinbox_number_reddit.get())))
        
        # Reddit Number Label
        self.tk_label_number_reddit = tk.Label(self.tk_frame_config)
        self.tk_label_number_reddit.grid(row=2, column=0, sticky="e")
        self.tk_label_number_reddit.configure(text="Number : ")
        self.tk_label_number_reddit.configure(background="#d9d9d9")
        
        # Reddit Number Spinbox
        self.tk_spinbox_number_reddit = tk.Spinbox(self.tk_frame_config, from_=1, to=10000)
        self.tk_spinbox_number_reddit.grid(row=2, column=1, sticky="nsew", pady=5)
        
        # Reddit Progress Bar
        self.progress_reddit = ttk.Progressbar(self.tk_frame_config, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_reddit.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=30, pady=(5,15))
        
        # Arxiv Label
        self.tk_label_arxiv = tk.Label(self.tk_frame_config)
        self.tk_label_arxiv.grid(row=4, column=0, columnspan=3, sticky="nsew")
        self.tk_label_arxiv.configure(text="Arxiv")
        self.tk_label_arxiv.configure(background="#d9d9d9")
        
        # Arxiv Topic Label
        self.tk_label_topic_arxiv = tk.Label(self.tk_frame_config)
        self.tk_label_topic_arxiv.grid(row=5, column=0, sticky="e")
        self.tk_label_topic_arxiv.configure(text="Topic : ")
        self.tk_label_topic_arxiv.configure(background="#d9d9d9")
        
        # Arxiv Topic Entry
        self.tk_entry_arxiv_topic = tk.Entry(self.tk_frame_config)
        self.tk_entry_arxiv_topic.grid(row=5, column=1, sticky="nsew")
        self.tk_entry_arxiv_topic.configure(background="#d9d9d9")
        
        # Arxiv Generate Button
        self.tk_button_arxiv_generate = tk.Button(self.tk_frame_config, width=10)
        self.tk_button_arxiv_generate.grid(row=5, column=2, sticky="nsew", padx=5)
        self.tk_button_arxiv_generate.configure(text="Generate")
        self.tk_button_arxiv_generate.configure(command=(lambda: self.thread_func(create_pickle, "arxiv", self.tk_entry_arxiv_topic.get(), self.tk_spinbox_number_arxiv.get())))
        
        # Arxiv Number Label
        self.tk_label_number_arxiv = tk.Label(self.tk_frame_config)
        self.tk_label_number_arxiv.grid(row=6, column=0, sticky="e")
        self.tk_label_number_arxiv.configure(text="Number : ")
        self.tk_label_number_arxiv.configure(background="#d9d9d9")
        
        # Arxiv Number Spinbox
        self.tk_spinbox_number_arxiv = tk.Spinbox(self.tk_frame_config, from_=1, to=10000)
        self.tk_spinbox_number_arxiv.grid(row=6, column=1, sticky="nsew", pady=5)
        
        # Arxiv Progress Bar
        self.progress_arxiv = ttk.Progressbar(self.tk_frame_config, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_arxiv.grid(row=7, column=0, columnspan=3, sticky="nsew", padx=30, pady=(5,15))
        
    # Build GUI for MostUsedWords category
    def MostUsedWordsGUI(self):
        # Main frame for config tab
        self.tk_frame_config = tk.LabelFrame(self.tk_notebook_config)
        self.tk_frame_config.place(relx=0.3, rely=0.05, relheight=0.6, relwidth=0.4)
        self.tk_frame_config.configure(background="#d9d9d9")
        self.tk_frame_config.configure(relief='groove')
        self.tk_frame_config.configure(text="Select Topics and Number of words to plot")
        
        # Configuring frame columns for grid
        for i in range(3):
            self.tk_frame_config.grid_columnconfigure(i, weight=1)
            
        # Reddit Label
        self.tk_label_reddit = tk.Label(self.tk_frame_config)
        self.tk_label_reddit.grid(row=0, column=1, sticky="nsew")
        self.tk_label_reddit.configure(text="Reddit")
        self.tk_label_reddit.configure(background="#d9d9d9")
        
        # Reddit Topic Label
        self.tk_label_topic_reddit = tk.Label(self.tk_frame_config)
        self.tk_label_topic_reddit.grid(row=1, column=0, sticky="e")
        self.tk_label_topic_reddit.configure(text="Topic : ")
        self.tk_label_topic_reddit.configure(background="#d9d9d9")
        
        # Reddit Topic Scrolling Menu
        self.tk_combobox_reddit_topic = ttk.Combobox(self.tk_frame_config, state="readonly", values=self.saves["reddit"])
        self.tk_combobox_reddit_topic.grid(row=1, column=1, sticky="nsew", pady=(5,15))
        self.tk_combobox_reddit_topic.configure(background="#d9d9d9")
        
        # Reddit Number Label
        self.tk_label_number_reddit = tk.Label(self.tk_frame_config)
        self.tk_label_number_reddit.grid(row=2, column=0, sticky="e")
        self.tk_label_number_reddit.configure(text="Number : ")
        self.tk_label_number_reddit.configure(background="#d9d9d9")
        
        # Reddit Number Spinbox
        self.tk_spinbox_number_reddit = tk.Spinbox(self.tk_frame_config, from_=1, to=30)
        self.tk_spinbox_number_reddit.grid(row=2, column=1, sticky="nsew", pady=5)
        self.tk_spinbox_number_reddit.configure(background="#d9d9d9")
        
        # Arxiv Label
        self.tk_label_arxiv = tk.Label(self.tk_frame_config)
        self.tk_label_arxiv.grid(row=3, column=1, sticky="nsew")
        self.tk_label_arxiv.configure(text="Arxiv")
        self.tk_label_arxiv.configure(background="#d9d9d9")
        
        # Arxiv Topic Label
        self.tk_label_topic_arxiv = tk.Label(self.tk_frame_config)
        self.tk_label_topic_arxiv.grid(row=4, column=0, sticky="e")
        self.tk_label_topic_arxiv.configure(text="Topic : ")
        self.tk_label_topic_arxiv.configure(background="#d9d9d9")
        
        # Arxiv Topic Scrolling Menu
        self.tk_combobox_arxiv_topic = ttk.Combobox(self.tk_frame_config, state="readonly", values=self.saves["arxiv"])
        self.tk_combobox_arxiv_topic.grid(row=4, column=1, sticky="nsew", pady=(5,15))
        self.tk_combobox_arxiv_topic.configure(background="#d9d9d9")
        
        # Arxiv Number Label
        self.tk_label_number_arxiv = tk.Label(self.tk_frame_config)
        self.tk_label_number_arxiv.grid(row=5, column=0, sticky="e")
        self.tk_label_number_arxiv.configure(text="Number : ")
        self.tk_label_number_arxiv.configure(background="#d9d9d9")
        
        # Arxiv Number Spinbox
        self.tk_spinbox_number_arxiv = tk.Spinbox(self.tk_frame_config, from_=1, to=30)
        self.tk_spinbox_number_arxiv.grid(row=5, column=1, sticky="nsew", pady=5)
        self.tk_spinbox_number_arxiv.configure(background="#d9d9d9")
        
        # Plotting Button
        self.tk_button_plot = tk.Button(self.tk_frame_config, width=10)
        self.tk_button_plot.grid(row=6, column=1, sticky="nsew")
        self.tk_button_plot.configure(text="Plot")
        self.tk_button_plot.configure(command=(lambda: self.thread_func(MUW)))
        
        self.reload_saves() # Load all saves
    
    # Build GUI for TopicTrending category
    def TopicTrendingGUI(self):
        # Main frame for config tab
        self.tk_frame_config = tk.LabelFrame(self.tk_notebook_config)
        self.tk_frame_config.place(relx=0.3, rely=0.05, relheight=0.6, relwidth=0.4)
        self.tk_frame_config.configure(background="#d9d9d9")
        self.tk_frame_config.configure(relief='groove')
        self.tk_frame_config.configure(text='''Generate Your Data''')
        
        # Configuring frame columns for grid
        for i in range(3):
            self.tk_frame_config.grid_columnconfigure(i, weight=1)
            
        # Reddit Label
        self.tk_label_reddit = tk.Label(self.tk_frame_config)
        self.tk_label_reddit.grid(row=0, column=1, sticky="nsew")
        self.tk_label_reddit.configure(text="Reddit")
        self.tk_label_reddit.configure(background="#d9d9d9")
        
        # Reddit Topic Label
        self.tk_label_topic_reddit = tk.Label(self.tk_frame_config)
        self.tk_label_topic_reddit.grid(row=1, column=0, sticky="e")
        self.tk_label_topic_reddit.configure(text="Topic : ")
        self.tk_label_topic_reddit.configure(background="#d9d9d9")
        
        # Reddit Topic Scrolling Menu
        self.tk_combobox_reddit_topic = ttk.Combobox(self.tk_frame_config, state="readonly", values=self.saves["reddit"])
        self.tk_combobox_reddit_topic.grid(row=1, column=1, sticky="nsew", pady=(5,15))
        self.tk_combobox_reddit_topic.configure(background="#d9d9d9")
        
        # Arxiv Label
        self.tk_label_arxiv = tk.Label(self.tk_frame_config)
        self.tk_label_arxiv.grid(row=2, column=1, sticky="nsew")
        self.tk_label_arxiv.configure(text="Arxiv")
        self.tk_label_arxiv.configure(background="#d9d9d9")
        
        # Arxiv Topic Label
        self.tk_label_topic_arxiv = tk.Label(self.tk_frame_config)
        self.tk_label_topic_arxiv.grid(row=3, column=0, sticky="e")
        self.tk_label_topic_arxiv.configure(text="Topic : ")
        self.tk_label_topic_arxiv.configure(background="#d9d9d9")
        
        # Arxiv Topic Scrolling Menu
        self.tk_combobox_arxiv_topic = ttk.Combobox(self.tk_frame_config, state="readonly", values=self.saves["arxiv"])
        self.tk_combobox_arxiv_topic.grid(row=3, column=1, sticky="nsew", pady=(5,15))
        self.tk_combobox_arxiv_topic.configure(background="#d9d9d9")
        
        # Plotting Button
        self.tk_button_plot = tk.Button(self.tk_frame_config, width=10)
        self.tk_button_plot.grid(row=4, column=1, sticky="nsew")
        self.tk_button_plot.configure(text="Plot")
        self.tk_button_plot.configure(command=(lambda: self.thread_func(TT)))
        
        self.reload_saves() # Load all saves
        
    # Start a thread with function given in parameters
    def thread_func(self, func, *args):
    # Here we must separate categories because we need to access specific tkinter widgets
        # If in Generate Category and first argument is reddit
        if self.state == "Generate" and args[0] == "reddit":
            self.progress_reddit['value'] = 0 # Initialize Progress Bar Value
            self.progress_reddit.configure(style="red.Horizontal.TProgressbar") # Change Progress Bar Style
            self.tk_button_reddit_generate.config(text="Generating...") # Changing Button text
            self.tk_button_reddit_generate['state'] = 'disabled' # Disabling the Generate Button
            self.threads[args[0]] = threading.Thread(target=func, args=args) # Initialize thread in threads["reddit"]
            self.threads[args[0]].start() # Start the thread
        # If in Generate Category and first argument is arxiv 
        elif self.state == "Generate" and args[0] == "arxiv":
            self.progress_arxiv['value'] = 0
            self.progress_arxiv.configure(style="red.Horizontal.TProgressbar")
            self.tk_button_arxiv_generate.config(text="Generating...")
            self.tk_button_arxiv_generate['state'] = 'disabled'
            self.threads[args[0]] = threading.Thread(target=func, args=args)
            self.threads[args[0]].start()
        # If in MostUsedWords Category
        elif self.state == "Most Used Words":
            self.getPlatforms() # Refresh self.platforms_to_plot
            self.tk_button_plot.config(text="Processing...")
            self.tk_button_plot['state'] = 'disabled'
            for platform in self.platforms_to_plot:
                args = (platform,) # initialize args tuple
                if platform == "reddit":
                    keyword = self.tk_combobox_reddit_topic.get() # getting keyword value
                    number = self.tk_spinbox_number_reddit.get() # getting number value
                    args = args + (keyword, number) # updating args
                elif platform == "arxiv":
                    keyword = self.tk_combobox_arxiv_topic.get()
                    number = self.tk_spinbox_number_arxiv.get()
                    args = args + (keyword, number)
                self.threads[platform] = threading.Thread(target=func, args=args)
                self.threads[platform].start()
        # If in TopicTrending Category
        elif self.state == "Topic Trending":
            self.getPlatforms()
            self.tk_button_plot.config(text="Processing...")
            self.tk_button_plot['state'] = 'disabled'
            for platform in self.platforms_to_plot:
                args = (platform,)
                if platform == "reddit":
                    keyword = self.tk_combobox_reddit_topic.get()
                    args = args + (keyword,)
                elif platform == "arxiv":
                    keyword = self.tk_combobox_arxiv_topic.get()
                    args = args + (keyword,)
                self.threads[platform] = threading.Thread(target=func, args=args)
                self.threads[platform].start()
        
    # Parse the Saves Directory and update self.saves
    def reload_saves(self):
        self.saves["reddit"] = [""]
        self.saves["arxiv"] = [""]
        # For each Reddit Save
        for filename in os.scandir("./saved/reddit"):
            self.saves["reddit"].append(re.sub(".pickle", "", filename.name)) # Load all filenames with .pickle extension
            if hasattr(self, 'tk_combobox_reddit_topic'): # If the widget exists
                if self.tk_combobox_reddit_topic.winfo_exists(): # If the widgets hasn't been destroyed
                    self.tk_combobox_reddit_topic.configure(values=self.saves["reddit"]) # Update Scrolling Menu values
        # For each Arxiv Save
        for filename in os.scandir("./saved/arxiv"):
            self.saves["arxiv"].append(re.sub(".pickle", "", filename.name))
            if hasattr(self, 'tk_combobox_reddit_topic'):
                if self.tk_combobox_arxiv_topic.winfo_exists():
                    self.tk_combobox_arxiv_topic.configure(values=self.saves["arxiv"])
        
    # Plot MostUsedWords Data
    def MUWPlot(self):
        self.prepareResults() # Prepare the widgets to display plots
        global df_reddit, df_arxiv
        
        # Load DataFrames int our plotting Dict
        if "reddit" in self.platforms_to_plot:
            self.plots["reddit"] = dict()
            self.plots["reddit"]["df"] = df_reddit
        if "arxiv" in self.platforms_to_plot:
            self.plots["arxiv"] = dict()
            self.plots["arxiv"]["df"] = df_arxiv
            
        # For each platform that needs to be plotted
        for i in range(len(self.platforms_to_plot)):
            platform = self.platforms_to_plot[i] # Get the platform name
            
            # Configure corresponding row and column in tkinter grid
            self.PlotFrame.grid_rowconfigure(self.plotcoords[i][0], weight=1)
            self.PlotFrame.grid_columnconfigure(self.plotcoords[i][1], weight=1)
            
            # Getting the user's input
            if platform == "reddit":
                number = self.tk_spinbox_number_reddit.get()
                keyword = self.tk_combobox_reddit_topic.get()
            elif platform == "arxiv":
                number = self.tk_spinbox_number_arxiv.get()
                keyword = self.tk_combobox_arxiv_topic.get()
            
            # Create fig and axes from matplotlib
            self.plots[platform]['fig'] = plt.Figure(figsize=(6,5), dpi=100)
            self.plots[platform]['ax'] = self.plots[platform]['fig'].add_subplot(111)
            # Create tkinter widget to display matplotlib plot
            self.plots[platform]['widget'] = FigureCanvasTkAgg(self.plots[platform]['fig'], self.PlotFrame)
            self.plots[platform]['widget'].get_tk_widget().grid(row=self.plotcoords[i][0], column=self.plotcoords[i][1], sticky="nsew")
            self.plots[platform]['widget'].get_tk_widget().configure(background="#000000")
            self.plots[platform]['widget'].get_tk_widget().configure(relief='groove')
            self.plots[platform]['widget'].get_tk_widget().configure(borderwidth="2")
            # Plot our DataFrame on ax
            self.plots[platform]['df'].plot(kind='bar', legend=False, ax=self.plots[platform]['ax'])
            # Configure legend, abscissa and ordinate axis
            self.plots[platform]['ax'].set_xticklabels(self.plots[platform]['ax'].xaxis.get_majorticklabels(), rotation=45, fontsize=9)
            self.plots[platform]['ax'].yaxis.set_major_locator(MaxNLocator(integer=True))
            self.plots[platform]['ax'].set_title("%s : %s most used words in %s theme" % (platform, number, keyword))
            self.plots[platform]['fig'].subplots_adjust(bottom=0.2)
            self.plots[platform]['ax'].axes.get_xaxis().set_label_text('')
            self.plots[platform]['ax'].axes.get_yaxis().set_label_text('Occurrence')
        self.tk_notebook.select(self.tk_notebook_results) # Set focus on the results tab in Notebook
        df_reddit, df_arxiv = "", "" # Deleting global DataFrame values
    
    # Plot TopicTrending Data
    def TTPlot(self):
        self.prepareResults() # Prepare the widgets to display plots
        global df_reddit, df_arxiv
        
        # Load DataFrames int our plotting Dict
        if "reddit" in self.platforms_to_plot:
            self.plots["reddit"] = dict()
            self.plots["reddit"]["df"] = df_reddit
        if "arxiv" in self.platforms_to_plot:
            self.plots["arxiv"] = dict()
            self.plots["arxiv"]["df"] = df_arxiv
        
        # For each platform that needs to be plotted
        for i in range(len(self.platforms_to_plot)):
            platform = self.platforms_to_plot[i] # Get the platform name
            
            # Configure corresponding row and column in tkinter grid
            self.PlotFrame.grid_rowconfigure(self.plotcoords[i][0], weight=1)
            self.PlotFrame.grid_columnconfigure(self.plotcoords[i][1], weight=1)
            
            # Getting the user's input
            if platform == "reddit":
                keyword = self.tk_combobox_reddit_topic.get()
            elif platform == "arxiv":
                keyword = self.tk_combobox_arxiv_topic.get()
            
            # Create fig and axes from matplotlib
            self.plots[platform]['fig'] = plt.Figure(figsize=(6,5), dpi=100)
            self.plots[platform]['ax'] = self.plots[platform]['fig'].add_subplot(111)
            # Create tkinter widget to display matplotlib plot
            self.plots[platform]['widget'] = FigureCanvasTkAgg(self.plots[platform]['fig'], self.PlotFrame)
            self.plots[platform]['widget'].get_tk_widget().grid(row=self.plotcoords[i][0], column=self.plotcoords[i][1], sticky="nsew")
            self.plots[platform]['widget'].get_tk_widget().configure(background="#000000")
            self.plots[platform]['widget'].get_tk_widget().configure(relief='groove')
            self.plots[platform]['widget'].get_tk_widget().configure(borderwidth="2")
            # Plot our DataFrame on ax
            self.plots[platform]['df'].plot(legend=False, ax=self.plots[platform]['ax'])
            # Configure legend, abscissa and ordinate axis
            self.plots[platform]['ax'].tick_params(axis='x', rotation=45)
            self.plots[platform]['ax'].set_title("%s Subreddit Trend" % keyword)
            self.plots[platform]['ax'].axes.get_xaxis().set_label_text('')
        self.tk_notebook.select(self.tk_notebook_results) # Set focus on the results tab in Notebook
        df_reddit, df_arxiv = "", "" # Deleting global DataFrame values
    
    # Refresh self.platforms_to_plot based on user's input
    def getPlatforms(self):
        self.platforms_to_plot = []
        if self.tk_combobox_reddit_topic.get():
            self.platforms_to_plot.append("reddit")
        if self.tk_combobox_arxiv_topic.get():
            self.platforms_to_plot.append("arxiv")

    # Destroy and Create tkinter widgets to display matplotlib plots
    def prepareResults(self):
        self.destroyResults()
        self.PlotFrame = tk.Frame(self.tk_notebook_results)
        self.PlotFrame.place(relx=0.05, rely=0.05, relheight=0.9, relwidth=0.9)
        self.PlotFrame.configure(background="#d9d9d9")
        self.PlotFrame.configure(relief='groove')
        self.PlotFrame.configure(borderwidth="2")
        
    # Destroy the Results Tab content
    def destroyResults(self):
        if hasattr(self, 'PlotFrame'):
            self.PlotFrame.destroy()
        
    # Update Notebook, called when the user changes the Scrolling Menu Category
    def updateNotebook(self, event):
        self.tk_categories.selection_clear() # Used to remove highlight on element
        self.destroyNotebook() # Destroy the current notebook content
        self.state = self.tk_categories.get() # Changing the current state
        self.tk_notebook.select(self.tk_notebook_config) # Focus on the config tab
        self.loaded = False # Signals that GUI need to be changed
        
    # Destroy the notebook content
    def destroyNotebook(self):
        self.destroyResults() 
        self.tk_frame_config.destroy()
            
    # Used to start our Program
    def start(self):
        # Main Loop
        while True:
            try:
                # Updating Tkinter at each frame
                self.top.update_idletasks()
                self.top.update()
                self.refresh() # Custom function to be called at each frame
            except Exception as e:
                print(type(e), ':', e)
                break
            
    # Check if all DataFrame values have been processed
    def plot_ready(self):
        global df_reddit, df_arxiv
        # For each platform that needs to be plotted
        for platform in self.platforms_to_plot:
            # If df_reddit is not a pd.DataFrame yet
            if platform == "reddit" and not isinstance(df_reddit, pd.DataFrame):
                return False
            # If df_arxiv is not a pd.DataFrame yet
            elif platform == "arxiv" and not isinstance(df_arxiv, pd.DataFrame):
                return False
        return True

    # Called at each Frame, used to check flags
    def refresh(self):
        global progress_reddit_value, progress_arxiv_value, to_update, to_plot
        
        # GUI changing, if self.loaded = False
        if self.state == "Generate" and not self.loaded:
            self.GenerateGUI()
            self.loaded = True
        elif self.state == "Most Used Words" and not self.loaded:
            self.MostUsedWordsGUI()
            self.loaded = True
        elif self.state == "Topic Trending" and not self.loaded:
            self.TopicTrendingGUI()
            self.loaded = True
            
        # Data Generation and Progress Bar Updating, if to_update = True
        if self.state == "Generate" and to_update:
            if "reddit" in self.threads:
                if self.threads["reddit"].is_alive():
                    self.progress_reddit['value'] = progress_reddit_value
                else:
                    self.progress_reddit['value'] = 100
                    self.progress_reddit.configure(style="green.Horizontal.TProgressbar")
                    self.tk_button_reddit_generate.config(text="Generate")
                    self.tk_button_reddit_generate['state'] = 'normal'
                    self.reload_saves()
            if "arxiv" in self.threads:
                if self.threads["arxiv"].is_alive():
                    self.progress_arxiv['value'] = progress_arxiv_value
                else:
                    self.progress_arxiv['value'] = 100
                    self.progress_arxiv.configure(style="green.Horizontal.TProgressbar")
                    self.tk_button_arxiv_generate.config(text="Generate")
                    self.tk_button_arxiv_generate['state'] = 'normal'
                    self.reload_saves()
            to_update = False
            
        # Data Plotting, if to_plot = True
        if self.state == "Most Used Words" and to_plot:
            if self.plot_ready():
                self.MUWPlot()
                self.tk_button_plot.config(text="Plot")
                self.tk_button_plot['state'] = 'normal'
                to_plot = False
        elif self.state == "Topic Trending" and to_plot:
            if self.plot_ready():
                self.TTPlot()
                self.tk_button_plot.config(text="Plot")
                self.tk_button_plot['state'] = 'normal'
                to_plot = False
                
# Used to clean a string: remove special chars, stopwords and lemmatize words
def nettoyer_texte(text):
    # Replacing specials chars and specific strings like "http"
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
    # list found on https://gist.github.com/sebleier/554280
    stopwords = ["i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"]
    all_stopwords = STOPWORDS.union(stopwords)
    words = result.split()
    result = [word for word in words if word not in all_stopwords]
    
    # Lemmatize text
    lemmatizer = WordNetLemmatizer()
    result = [lemmatizer.lemmatize(word) for word in result]
    
    result = ' '.join( [word for word in result if len(word)>1] )
    return result

# Create a pickle from Data returned by API requests
def create_pickle(platform, keyword, number):
    global progress_reddit_value, progress_arxiv_value, to_update
    count = 0 # Current number of results
    number = int(number) # Results Number asked by user
    keyword = keyword.lower()
    df = pd.DataFrame(columns=['title', 'date', 'url', 'text']) # DataFrame format
    
    # Reddit API
    if platform == "reddit":
        url = "https://api.pushshift.io/reddit/submission/search?limit=1000&lang=en&sort=desc&subreddit={}&before={}" # Reddit API url
        prev_time = round(time.time())
        # Main Loop
        while True:
            # If we have enough results
            if count >= number:
                break
            try:
                new_url = url.format(keyword, str(prev_time)) # Get 1000 results on keyword subreddit before prev_time
                json = requests.get(new_url) # Get response 
                json_data = json.json() # Response to json
            except Exception as e:
                print("Error: %s" % e)
                continue
            
            # If no data has been found (reached end)
            if 'data' not in json_data:
                break
            docs = json_data['data']
            
            # If 'data' is empty (reached end)
            if len(docs) == 0:
                break
            
            # For each result
            for doc in docs:
                try:
                    txt = doc['selftext'].replace('\n', ' ').replace('\r', ' ') # Format the text
                    df.loc[len(df)] = [doc['title'], doc['created_utc'], doc['url'], txt] # Add a row to the DataFrame
                    prev_time = doc['created_utc'] - 1 # Updating prev_time
                    count += 1 # Incremeting count
                except Exception as e:
                    print("Error : %s" % e)
                    continue
                # If we have enough results
                if count == number: 
                    break
            progress_reddit_value = int((count / number) * 100) # Updating Progress Bar value
            to_update = True # Signals that we need to update the GUI
    # Arxiv API
    elif platform == "arxiv":
        url = "http://export.arxiv.org/api/query?search_query=all:{}&start={}&max_results={}" # Arxiv API url
        # Main Loop
        while True:
            # If we have enough results
            if count >= number:
                break
            try:
                new_url = url.format(keyword, str(count), "200") # Get 200 results with keyword query from result n°count
                data = urllib.request.urlopen(new_url).read().decode() # Get response
                docs = xmltodict.parse(data)['feed']['entry'] # Response to dict
            except Exception as e:
                print("Error: %s" % e)
                break
            
            # If response is empty (reached end)
            if len(docs) == 0:
                break
            
            # For each result
            for doc in docs:
                date = dt.datetime.strptime(doc['published'], "%Y-%m-%dT%H:%M:%SZ") # Format Date
                date = (date - dt.datetime(1970,1,1)).total_seconds() # Convert date to seconds since Epoch Time
                txt = doc['summary'].replace('\n', ' ').replace('\r', ' ') # Format the text
                df.loc[len(df)] = [doc['title'], date, doc['id'], txt] # Add a row to the DataFrame
                count += 1 # Incrementing count
                # If we have enough results
                if count == number:
                    break
            progress_arxiv_value = int((count / number) * 100) # Updating Progress Bar value
            to_update = True # Signals that we need to update the GUI
    
    mindate = (dt.datetime(2017,1,1) - dt.datetime(1970,1,1)).total_seconds() # Creating a minimum Data (1st Jan 2017)
    df = df[~(df['date'] < mindate)] # Removing every result before this date
    # Saving to .pickle
    with open("saved/%s/%s-%s.pickle" % (platform, keyword.lower(), str(count)), "wb") as handle:
        pickle.dump(df, handle, protocol=pickle.HIGHEST_PROTOCOL)
    to_update = True # Signals that we need to update the GUI
    
# MostUsedWords processing function
def MUW(platform, keyword, number):
    global df_reddit, df_arxiv, to_plot
    # Load keyword.pickle
    try:
        with open('saved/%s/%s.pickle' % (platform, keyword), 'rb') as handle:
            df = pickle.load(handle)
    except Exception as e:
        print("Error : %s" % e)
        return
    
    ret = pd.DataFrame(columns=["Word", "Count"]) # Create return value
    text = ' '.join(df['text']) # Concatenate all texts
    text = nettoyer_texte(text) # Clean the text
    freq = {}
    # For each word in text
    for word in text.split(" "):
        if word:
            freq[word] = freq[word] + 1 if word in freq else 1 # Add 1 to its value in the frequence dict
    freq = {k: v for k, v in sorted(freq.items(), key=lambda item: item[1], reverse=True)} # Sort the words by count in descending order
    top_words = []
    # For each key, value in freq dict
    for k,v in freq.items():
        if len(top_words) < int(number): # Used to select only the number first words
            top_words.append([k, v]) # Add it to our top_words array
    for word in top_words:
        ret.loc[len(ret)] = word # Add each word to our DataFrame
        
    # Change the right global value (depending on the platform)
    if platform == "reddit":
        df_reddit = ret.set_index('Word')
    elif platform == "arxiv":
        df_arxiv = ret.set_index('Word')
    to_plot = True # Signals that this function has ended and this DataFrame is ready to be plotted

# TopicTrending processing function
def TT(platform, keyword):
    global df_reddit, df_arxiv, to_plot
    # Load keyword.pickle
    try:
        with open('saved/%s/%s.pickle' % (platform, keyword), 'rb') as handle:
            df = pickle.load(handle)
    except Exception as e:
        print("Error : %s" % e)
        return
    
    ret = pd.DataFrame(columns=["date", "count"]) # Create return value
    date_format = "%m-%Y"
    date = pd.to_datetime(df['date'], unit='s').dt.strftime(date_format) # Format our date from seconds to str(datetime)
    # If we have only 2 or less different dates
    if len(date.drop_duplicates()) <= 2:
        date_format = "%d-%m-%Y" # change the date format
        date = pd.to_datetime(df['date'], unit='s').dt.strftime(date_format) # This time we consider the days
    # Updating return DataFrame
    ret['date'] = date
    ret['count'] = df['text']
    # Grouping values by date, counting their occurence
    ret = ret.groupby('date').count()
    # Converting the index to datetime (so it can be sorted correctly)
    ret.index = pd.to_datetime(ret.index, format=date_format)
    # Sort the indexes
    ret = ret.sort_index()
    
    # Change the right global value (depending on the platform)
    if platform == "reddit":
        df_reddit = ret
    elif platform == "arxiv":
        df_arxiv = ret
    to_plot = True # Signals that this function has ended and this DataFrame is ready to be plotted

# Main function
if __name__ == '__main__':
    program = Program() # Create an instance of Program
    program.start() # Start it

