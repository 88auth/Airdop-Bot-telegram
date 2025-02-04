import tweepy
import pandas as pd
from datetime import datetime
from google.colab import drive
import os
import requests
import time

# Mount Google Drive
drive.mount('/content/drive')

# Tentukan folder penyimpanan di Google Drive
drive_folder = "/content/drive/MyDrive/TwitterData/"
os.makedirs(drive_folder, exist_ok=True)

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# Twitter API credentials
BEARER_TOKEN = os.environ["BEARER_TOKEN"]

# Initialize Tweepy Client
client = tweepy.Client(bearer_token=BEARER_TOKEN)

# **Daftar kata kunci yang akan dicari**
keywords = ["airdrop", "Airdrop", "airDrop", "AirDrop", "AIRDROP"]
search_query = " OR ".join(keywords)  # Gabungkan dengan OR agar semua variasi dicari

def get_twitter_data(query, max_results=10, retries=3):
    """
    Fetch tweets containing links with retry mechanism
    """
    for attempt in range(retries):
        try:
            tweets = client.search_recent_tweets(
                query=query + " has:links",
                tweet_fields=["created_at", "public_metrics", "entities", "text"],
                max_results=max_results,
                expansions='author_id'
            )
            
            data = []
            if tweets.data:
                for tweet in tweets.data:
                    urls = [url['expanded_url'] for url in tweet.entities['urls']] if tweet.entities and 'urls' in tweet.entities else []
                    metrics = tweet.public_metrics

                    data.append({
                        'tweet_id': tweet.id,
                        'post_text': tweet.text,
                        'post_urls': ', '.join(urls),
                        'likes': metrics['like_count'],
                        'retweets': metrics['retweet_count'],
                        'replies': metrics['reply_count'],
                        'impressions': metrics['impression_count'],
                        'created_at': tweet.created_at
                    })
                
                return data  # Return jika sukses
                
            else:
                return []

        except tweepy.TooManyRequests as e:
            wait_time = (2 ** attempt) * 15  # Exponential Backoff (15s, 30s, 60s)
            print(f"Rate limit tercapai. Menunggu {wait_time} detik sebelum mencoba lagi...")
            time.sleep(wait_time)
        except Exception as e:
            print(f"Error lain: {e}")
            break  # Stop jika error bukan 429
    
    return []

def save_to_csv(data, filename):
    """Save collected data to CSV in Google Drive"""
    df = pd.DataFrame(data)
    file_path = os.path.join(drive_folder, filename)
    df.to_csv(file_path, index=False)
    print(f"Data saved to {file_path} ({len(data)} records)")
    return file_path

def send_telegram_message(text):
    """Send a text message to Telegram (Markdown enabled)"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    return response.json()

def send_tweets_to_telegram(tweets):
    """Send each tweet as a separate Telegram message with a link to the original post"""
    for tweet in tweets:
        tweet_link = f"https://twitter.com/i/web/status/{tweet['tweet_id']}"
        message = f"""
📢 **Tweet Baru Ditemukan!**

📝 *{tweet['post_text']}*

🔗 [Lihat Tweet]({tweet_link})

❤️ {tweet['likes']} | 🔁 {tweet['retweets']} | 💬 {tweet['replies']}
📅 {tweet['created_at']}
        """
        send_telegram_message(message)
        time.sleep(1)  # Mencegah rate limit dengan delay 1 detik per pesan

def send_telegram_file(file_path):
    """Send CSV file to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    with open(file_path, "rb") as file:
        response = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID}, files={"document": file})
    return response.json()

if __name__ == "__main__":
    # Number of tweets to collect (max 10 per request)
    tweet_count = 10
    
    # Collect data with retry
    tweet_data = get_twitter_data(search_query, tweet_count)
    
    # Save to CSV in Google Drive
    if tweet_data:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"twitter_export_{timestamp}.csv"
        file_path = save_to_csv(tweet_data, filename)
        
        # Kirim setiap tweet dalam bubble chat terpisah
        send_tweets_to_telegram(tweet_data)
        
        # Kirim file CSV ke Telegram
        send_telegram_file(file_path)
    else:
        send_telegram_message("❌ Tidak ada tweet yang ditemukan.")
