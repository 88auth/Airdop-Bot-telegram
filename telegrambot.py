import tweepy
import requests
import time
from datetime import datetime
import os

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

if __name__ == "__main__":
    # Number of tweets to collect (max 10 per request)
    tweet_count = 10
    
    # Collect data with retry
    tweet_data = get_twitter_data(search_query, tweet_count)
    
    # Kirim setiap tweet dalam bubble chat terpisah
    if tweet_data:
        send_tweets_to_telegram(tweet_data)
    else:
        send_telegram_message("❌ Tidak ada tweet yang ditemukan.")
