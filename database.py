import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

# Create a new SQLite database
conn = sqlite3.connect('users.db')
c = conn.cursor()

# Create the users table
c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, password TEXT)''')

# Create the saved_videos table
c.execute('''CREATE TABLE IF NOT EXISTS saved_videos
             (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, video_url TEXT)''')

# Create the sentiment_history table
c.execute('''CREATE TABLE IF NOT EXISTS sentiment_history
             (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, video_url TEXT, sentiment TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

conn.commit()
conn.close()



def create_user(name, email, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Check if the email already exists
    c.execute("SELECT COUNT(*) FROM users WHERE email = ?", (email,))
    if c.fetchone()[0] > 0:
        return False

    # Hash the password
    hashed_password = generate_password_hash(password)

    # Insert the new user
    c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, hashed_password))
    conn.commit()
    conn.close()
    return True

def get_user(email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()
    return dict(zip(['id', 'name', 'email', 'password'], user)) if user else None

def authenticate_user(email, password):
    user = get_user(email)
    if user and check_password_hash(user['password'], password):
        return user
    return None

def save_user_video(user_id, video_url):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO saved_videos (user_id, video_url) VALUES (?, ?)", (user_id, video_url))
    conn.commit()
    conn.close()

def get_user_saved_videos(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT video_url FROM saved_videos WHERE user_id = ?", (user_id,))
    videos = [row[0] for row in c.fetchall()]
    conn.close()
    return videos

def save_user_sentiment(user_id, video_url, sentiment):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO sentiment_history (user_id, video_url, sentiment) VALUES (?, ?, ?)", (user_id, video_url, sentiment))
    conn.commit()
    conn.close()

def get_user_sentiment_history(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT video_url, sentiment, timestamp FROM sentiment_history WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    history = [dict(zip(['video_url', 'sentiment', 'timestamp'], row)) for row in c.fetchall()]
    conn.close()
    return history