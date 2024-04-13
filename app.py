"""
Function to import Transformations and run the streamlit dashboard
"""
import json
import streamlit as st
from streamlit_echarts import st_echarts
from millify import millify
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder
from transform import parse_video, youtube_metrics, get_top_positive_comments, get_top_negative_comments
from database import create_user, get_user, authenticate_user, save_user_video, get_user_saved_videos, save_user_sentiment, get_user_sentiment_history
import pandas as pd
import matplotlib.pyplot as plt
  
def show_home_page(VIDEO_URL):
    st.title('YouTube Analytics Dashboard')
    with st.form("video_form"):
        if VIDEO_URL:
            url_input = st.text_input('Enter URL', value=VIDEO_URL, key="url_input")
        else:
            url_input = st.text_input('Enter URL', key="url_input")

        example_button = st.form_submit_button("Example")
        submit_button = st.form_submit_button("Submit")

    if submit_button or example_button:
        if example_button:
            VIDEO_URL = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        else:
            VIDEO_URL = url_input
    
    try:
        with st.spinner('Crunching numbers...'):
            df = parse_video(VIDEO_URL)
            df_metrics = youtube_metrics(VIDEO_URL)
            

            # Metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("**Views**", millify(df_metrics[0], precision=2))
            col2.metric("**Likes**", millify(df_metrics[1], precision=2))
            col3.metric("**Comments**", millify(df_metrics[2], precision=2))

            # Embedded Video
            st.video(VIDEO_URL)

            # Top Comments
            st.subheader("Most liked comments")
            df_top = df[['Author', 'Comment', 'Timestamp', 'Likes']].sort_values(
                'Likes', ascending=False).reset_index(drop=True)

            gd1 = GridOptionsBuilder.from_dataframe(df_top.head(11))
            gridoptions1 = gd1.build()
            AgGrid(df_top.head(11), gridOptions=gridoptions1,
                   theme='streamlit', columns_auto_size_mode='FIT_CONTENTS',
                   update_mode='NO_UPDATE')

            st.subheader("Languages")
            df_langs = df['Language'].value_counts().rename_axis(
                'Language').reset_index(name='count')

            options2 = {
                "tooltip": {
                    "trigger": 'axis',
                    "axisPointer": {
                        "type": 'shadow'
                    },
                    "formatter": '{b}: {c}%'
                },
                "yAxis": {
                    "type": "category",
                    "data": df_langs['Language'].tolist(),
                },
                "xAxis": {"type": "value",
                          "axisTick": {
                              "alignWithLabel": "true"
                          }
                          },
                "series": [{"data": df_langs['count'].tolist(), "type": "bar"}],
            }
            st_echarts(options=options2, height="500px")
              # Most Replied Comments
            st.subheader("Most Replied Comments")
            df_replies = df[['Author', 'Comment', 'Timestamp', 'TotalReplies']].sort_values(
                'TotalReplies', ascending=False).reset_index(drop=True)

            gd2 = GridOptionsBuilder.from_dataframe(df_replies.head(11))
            gridoptions2 = gd2.build()
            AgGrid(df_replies.head(11), gridOptions=gridoptions2,
                   theme='streamlit', columns_auto_size_mode='FIT_CONTENTS',
                   update_mode='NO_UPDATE')

            # Sentiments of the Commentors
            st.subheader("Reviews")
            sentiments = df[df['Language'] == 'English']
            data_sentiments = sentiments['TextBlob_Sentiment_Type'].value_counts(
            ).rename_axis('Sentiment').reset_index(name='counts')

            data_sentiments['Review_percent'] = (
                100. * data_sentiments['counts'] / data_sentiments['counts'].sum()).round(1)

            result = data_sentiments.to_json(orient="split")
            parsed = json.loads(result)

            options = {
                "tooltip": {"trigger": "item",
                            "formatter": '{d}%'},
                "legend": {"top": "5%", "left": "center"},
                "series": [
                    {
                        "name": "Sentiment",
                        "type": "pie",
                        "radius": ["40%", "70%"],
                        "avoidLabelOverlap": False,
                        "itemStyle": {
                            "borderRadius": 10,
                            "borderColor": "#fff",
                            "borderWidth": 2,
                        },
                        "label": {"show": False, "position": "center"},
                        "emphasis": {
                            "label": {"show": True, "fontSize": "30", "fontWeight": "bold"}
                        },
                        "labelLine": {"show": False},
                        "data": [
                            # NEUTRAL
                            {"value": parsed['data'][1][2],
                             "name": parsed['data'][1][0]},
                            # POSITIVE
                            {"value": parsed['data'][0][2],
                             "name": parsed['data'][0][0]},
                            # NEGATIVE
                            {"value": parsed['data'][2][2],
                             "name": parsed['data'][2][0]}
                        ],
                    }
                ],
            }
            st_echarts(
                options=options, height="500px",
            )
            if 'user' in st.session_state:
                user_id = st.session_state.user['id']
                sentiment = data_sentiments['data'][0][0]  # Assuming the first sentiment is the overall sentiment
                save_user_sentiment(user_id, VIDEO_URL, sentiment)
            
            st.subheader("Sentiment Percentage")
            total_comments = data_sentiments['counts'].sum()
            positive_percent = (data_sentiments.loc[data_sentiments['Sentiment'] == 'POSITIVE', 'counts'].item() / total_comments) * 100
            negative_percent = (data_sentiments.loc[data_sentiments['Sentiment'] == 'NEGATIVE', 'counts'].item() / total_comments) * 100
            neutral_percent = (data_sentiments.loc[data_sentiments['Sentiment'] == 'NEUTRAL', 'counts'].item() / total_comments) * 100

            col1, col2, col3 = st.columns(3)
            col1.metric("Positive", f"{positive_percent:.2f}%")
            col2.metric("Negative", f"{negative_percent:.2f}%")
            col3.metric("Neutral", f"{neutral_percent:.2f}%")

            st.subheader("Comment Length Analysis")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.hist(df['Comment_Length'], bins=20, edgecolor='black')
            ax.set_title('Distribution of Comment Lengths')
            ax.set_xlabel('Comment Length (Number of Words)')
            ax.set_ylabel('Frequency')
            st.pyplot(fig)

            st.subheader("Top Positive Comments")
            top_positive_comments = get_top_positive_comments(df)
            st.dataframe(top_positive_comments)

            # Display top negative comments
            st.subheader("Top Negative Comments")
            top_negative_comments = get_top_negative_comments(df)
            st.dataframe(top_negative_comments)


            
    except:
        if VIDEO_URL and not VIDEO_URL.startswith('https://www.youtube.com/watch?v='):
           st.error(
            ' The URL Should be of the form: https://www.youtube.com/watch?v=videoID', icon="🚨")
           
    return VIDEO_URL
           
def show_about_page():
    st.title("About Us")
    st.write("This is a Streamlit application that provides a YouTube Analytics Dashboard. It allows users to analyze the comments and sentiments of a YouTube video.")
    st.write("The application was developed by [Your Name] using Python and various data analysis libraries.")
    st.write("If you have any questions or feedback, please feel free to reach out to us at [Your Email].")


def show_login_page():
    st.title("Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")
    pass

    if st.button("Login", key="login_button"):
        user = authenticate_user(email, password)
        if user:
            st.session_state.user = user
            show_user_dashboard()
        else:
            st.error("Invalid email or password")

def show_signup_page():
    st.title("Sign Up")

    # Initialize a flag to track successful sign-up
    signup_successful = False

    # Clear input fields if the sign-up was successful in the previous attempt
    if "signup_success" in st.session_state and st.session_state.signup_success:
        st.session_state["signup_name"] = ""
        st.session_state["signup_email"] = ""
        st.session_state["signup_password"] = ""
        st.session_state.signup_success = False

    name = st.text_input("Name", key="signup_name")
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_password")

    if st.button("Sign Up", key="signup_button"):
        if create_user(name, email, password):
            # Set the flag to indicate successful sign-up
            signup_successful = True
            st.success("Account created successfully!")
        else:
            st.error("Email already exists. Please try a different email.")
    
    # Update the session state with the sign-up success flag
    st.session_state.signup_success = signup_successful

def show_user_dashboard():
    st.title("User Dashboard")
    user = st.session_state.get('user')
    if user:
        st.write(f"Welcome, {user['name']}!")

        saved_videos = get_user_saved_videos(user['id'])
        st.subheader("Saved Videos")
        for video_url in saved_videos:
            st.write(video_url)

        sentiment_history = get_user_sentiment_history(user['id'])
        st.subheader("Sentiment Analysis History")
        if sentiment_history:
            df_sentiment_history = pd.DataFrame(sentiment_history)
            st.dataframe(df_sentiment_history)
        else:
            st.write("No sentiment analysis history found.")

        new_video_url = st.text_input("Add a new video URL", key="new_video_url")
        if st.button("Analyze", key="analyze_button"):
            if new_video_url:
                try:
                    # Analyze the new video URL
                    with st.spinner('Analyzing video...'):
                        df = parse_video(new_video_url)
                        df_metrics = youtube_metrics(new_video_url)

                        # Save the video URL
                        save_user_video(user['id'], new_video_url)

                        # Perform sentiment analysis
                        sentiments = df[df['Language'] == 'English']
                        data_sentiments = sentiments['TextBlob_Sentiment_Type'].value_counts().rename_axis('Sentiment').reset_index(name='counts')
                        data_sentiments['Review_percent'] = (100. * data_sentiments['counts'] / data_sentiments['counts'].sum()).round(1)

                        result = data_sentiments.to_json(orient="split")
                        parsed = json.loads(result)

                        sentiment = parsed['data'][0][0]  # Assuming the first sentiment is the overall sentiment
                        save_user_sentiment(user['id'], new_video_url, sentiment)

                        st.success("Video analysis completed successfully!")
                except Exception as e:
                    st.error(f"Error analyzing video: {e}")
            else:
                st.warning("Please enter a video URL to analyze.")

    else:
        st.warning("Please log in to access the user dashboard.")

def show_navigation():
    st.sidebar.title("Navigation")
    selection = st.sidebar.radio("Go to", list(pages.keys()), key="navigation_selection")
    return selection


def main():
    selection = show_navigation()
    VIDEO_URL = None

    if selection == "Home":
        VIDEO_URL = show_home_page(VIDEO_URL)
    elif selection in pages:
        pages[selection]()

pages={
    "Home": show_home_page,
    "About": show_about_page,
    "Login": show_login_page,
    "Signup": show_signup_page,
    "User Dashboard": show_user_dashboard
}

if __name__ == "__main__":
    main()