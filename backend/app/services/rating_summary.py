"""Rating statistics for the reviews actually stored, not marketplace totals."""


def summarize_ratings(reviews):
    counts = {str(star): 0 for star in range(1, 6)}
    total = 0
    for review in reviews:
        total += 1
        if review.rating in range(1, 6):
            counts[str(review.rating)] += 1
    rated = sum(counts.values())
    return {
        "counts": counts,
        "rated_reviews": rated,
        "unrated_reviews": total - rated,
        "average_rating": round(sum(int(star) * count for star, count in counts.items()) / rated, 2) if rated else None,
    }
