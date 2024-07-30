from flask import Flask , render_template,request, redirect, session, url_for,send_file
import requests 
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re
from nltk.sentiment import SentimentIntensityAnalyzer
from tqdm.notebook import tqdm_notebook
import tqdm
import nltk
import io
import seaborn as sns
import base64
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('maxent_ne_chunker')
nltk.download('words')
nltk.download('vader_lexicon')
app = Flask(__name__)



# Route to display form and handle submission
@app.route('/', methods=['GET', 'POST'])
def index():
    video_id = None
    comm = []
    comments = []
    total_comments = 0
    positive_count = 0
    pie_chart_base64 = None
    bar_chart_base64 = None
    sentiment_counts = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
   
    if request.method == 'POST':
        video_url = request.form.get('video_url')
        video_id = extract_video_id(video_url)
    comments = []
    if request.method == 'POST':
        video_url = request.form.get('video_url')
        api_key = 'AIzaSyCLj4zvPt9M9eb4Ap13WHy2gR9WV4ZA7tU'  # Replace with your YouTube Data API key
        video_id = extract_video_id(video_url)
        
        if video_id:
            comments = fetch_comments(video_id, api_key)
            comm = commentsfetch(video_id)
            sentiment_data = analyze_sentiments([comment['text'] for comment in comm])
             # Count sentiment types
            positive_count = sum(1 for data in sentiment_data if data['compound'] > 0)
            total_comments = len(comm)
            sentiments = [comment['sentiment'] for comment in comm]
            pie_chart_base64 = create_pie_chart(sentiments)
            bar_chart_base64 = create_bar_chart(sentiments)

        # Calculate sentiment counts
            for comment in comm:
                sentiment_counts[comment['sentiment']] += 1
            
            sentiments = [comment['sentiment'] for comment in comm]
            pie_chart_base64 = create_pie_chart(sentiments)
            bar_chart_base64 = create_bar_chart(sentiments)
    
    
    # No persistent storage of video_id between requests, so it will be removed on page refresh
    return render_template('index.html', video_id=video_id,comments=comments,comm=comm, positive_count=positive_count,pie_chart_base64=pie_chart_base64, bar_chart_base64=bar_chart_base64,sentiment_counts=sentiment_counts,total_comments=total_comments)


@app.route('/about')
def about():
    # Handle about route logic
    return render_template('about.html')



app.secret_key = '67thuge45x5578989jknkjbhdt4w3sfx65rf6r6r67g'  # Set a secret key for session management

# Route to render the contact form page
@app.route('/submit_contact_form', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Get form data from the request object
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        # You can add additional validation or processing here

        # For demonstration purposes, print the form data
        print(f"Received contact form submission: Name - {name}, Email - {email}, Message - {message}")

        # Store a success message in session
        session['message'] = 'Form submitted successfully!'

        # Redirect to the same page to prevent form resubmission on refresh
        return redirect(url_for('contact'))

    # Render the contact form page with the success message if it exists
    return render_template('contact.html', message=session.pop('message', None))


# Initialize the YouTube API client
def get_youtube_service(api_key):
    return build('youtube', 'v3', developerKey='AIzaSyCLj4zvPt9M9eb4Ap13WHy2gR9WV4ZA7tU')
# Helper function to extract YouTube video ID
def extract_video_id(url):
    pattern = r"(?:youtu\.be/|youtube\.com/(?:embed/|watch\?v=|v/|watch\?.+&v=))([a-zA-Z0-9_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

sia = SentimentIntensityAnalyzer()


# Function to classify comment sentiment
def classify_sentiment(text):
    score = sia.polarity_scores(text)['compound']
    if score > 0:
        return 'Positive'
    elif score < 0:
        return 'Negative'
    else:
        return 'Neutral'
    
# Function to fetch comments using YouTube API
def fetch_comments(video_id, api_key):
    youtube = get_youtube_service(api_key)
    comments = []
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,
        )
        response = request.execute()
        for item in response.get('items', []):
            comment_data = item['snippet']['topLevelComment']['snippet']
            comment = {
                'author': comment_data['authorDisplayName'],
                'published_at': comment_data['publishedAt'],
                'text': comment_data['textOriginal'],
                'like_count': comment_data['likeCount'],
                'sentiment': classify_sentiment(comment_data['textOriginal'])
            }
            comments.append(comment)

    except Exception as e:
        print(f"An error occurred: {e}")
    
    return comments[:20]

def commentsfetch(video_id):
    youtube = build('youtube', 'v3', developerKey='AIzaSyCLj4zvPt9M9eb4Ap13WHy2gR9WV4ZA7tU')
    comm = []
    nextPageToken = None

    while True:
        response = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            pageToken=nextPageToken,
            maxResults=100
        ).execute()

        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']
            commento = {
                'text': comment['textOriginal'],
                'sentiment': classify_sentiment(comment['textOriginal'])
            }
            comm.append(commento)

        nextPageToken = response.get('nextPageToken')

        if not nextPageToken:
            break

    return comm


def analyze_sentiments(comments):
    sentiment_data = []
    for comment in comments:
        sentiment_scores = sia.polarity_scores(comment)
        sentiment_data.append({
            'comment': comment,
            'compound': sentiment_scores['compound'],
            'positive': sentiment_scores['pos'],
            'neutral': sentiment_scores['neu'],
            'negative': sentiment_scores['neg']
        })
    return sentiment_data
# Function to create and return a base64-encoded pie chart for sentiment distribution
def create_pie_chart(sentiments):
    sentiment_counts = {sentiment: sentiments.count(sentiment) for sentiment in set(sentiments)}
    
    labels = list(sentiment_counts.keys())
    values = list(sentiment_counts.values())
    
    plt.figure(figsize=(8, 6),facecolor='lightblue')
    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140, colors=sns.color_palette('pastel'), wedgeprops={'edgecolor': 'black'})
    plt.title('Sentiment Distribution')
    
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()
    
    return base64.b64encode(img.getvalue()).decode('utf-8')

# Function to create and return a base64-encoded bar chart for sentiment distribution
def create_bar_chart(sentiments):
    sentiment_counts = {sentiment: sentiments.count(sentiment) for sentiment in set(sentiments)}
    
    plt.figure(figsize=(10, 6),facecolor="lightblue")
    sns.barplot(x=list(sentiment_counts.keys()), y=list(sentiment_counts.values()), palette='pastel')
    plt.xlabel('Sentiment')
    plt.ylabel('Count')
    plt.title('Sentiment Distribution')
    plt.xticks(rotation=45)
    
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()
    
    return base64.b64encode(img.getvalue()).decode('utf-8')

   
if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('localhost', 5000, app,debug =True)


