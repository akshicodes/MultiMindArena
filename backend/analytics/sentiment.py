from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

def calculate_sentiment(text: str) -> float:
    """
    Returns sentiment score between -1 and +1
    """
    return analyzer.polarity_scores(text)["compound"]