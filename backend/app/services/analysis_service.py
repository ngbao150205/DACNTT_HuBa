from collections import Counter



def analyze_product_reviews(reviews):

    total_reviews = len(reviews)


    counter = Counter()


    for review in reviews:

        sentiment = review["sentiment"]["sentiment"]

        counter[sentiment] += 1



    positive_count = counter.get(
        "Positive",
        0
    )


    negative_count = counter.get(
        "Negative",
        0
    )


    neutral_count = counter.get(
        "Neutral",
        0
    )


    return {

        "total_reviews": total_reviews,


        "positive_count": positive_count,


        "negative_count": negative_count,


        "neutral_count": neutral_count,


        "positive_rate":
            round(
                positive_count / total_reviews * 100,
                2
            )
            if total_reviews
            else 0,


        "negative_rate":
            round(
                negative_count / total_reviews * 100,
                2
            )
            if total_reviews
            else 0,


        "neutral_rate":
            round(
                neutral_count / total_reviews * 100,
                2
            )
            if total_reviews
            else 0
    }