from .models import Order

def orders_waiting_for_review(request):
    # Get the count of orders with status WAIT_FOR_REVIEW
    waiting_for_review_count = Order.review.count()
    return {
        'waiting_for_review_count': waiting_for_review_count,
    }