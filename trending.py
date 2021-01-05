import time
import pickle
import requests
import pandas as pd

# Inspiré de github.com/Watchful1/Sketchpad/blob/master/postDownloader.py
def reddit(self, keyword):
    
    url = "https://api.pushshift.io/reddit/{}/search?limit=1000&lang=en&sort=desc&subreddit={}&before="
    start = round(time.time())
    count = 0
    goal = 200
    prevtime = start
    df = pd.DataFrame(columns=['title', 'created_utc'])
    while True:
        if count>=goal:
            break
        try:
            new_url = url.format("submission", keyword) + str(prevtime)
            json = requests.get(new_url)
            json_data = json.json()
        except Exception as e:
            print("Error: %s" % e)
            continue
        if 'data' not in json_data:
            break
        objects = json_data['data']
        if len(objects) == 0:
            break
        
        for object in objects:
            prevtime = object['created_utc'] - 1
            count += 1
            df.loc[len(df)] = [object['title'], object['created_utc']]
        
        print(count)
        self.progress_reddit_value = (count / goal) * 100
        self.updateneeded = True
        
    with open("saved/reddit/%s.pickle" % keyword.lower(), "wb") as handle:
        pickle.dump(df, handle, protocol=pickle.HIGHEST_PROTOCOL)
        
    #self.tk_label_warning.configure(text="Reddit Data Generated.")
    print(df.head())
    print(df.shape)
    
def arxiv(self, keyword):
    return

def twitter(self, keyword):
    return