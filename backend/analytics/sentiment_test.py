from sentiment import calculate_sentiment

print("Positive:",
      calculate_sentiment("I absolutely love this project"))

print("Negative:",
      calculate_sentiment("This project is terrible and frustrating"))

print("Neutral:",
      calculate_sentiment("The debate has started"))