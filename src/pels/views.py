from django.http import HttpResponse



def home_view(request):
    return HttpResponse("Hello World")


def customer_page(request):
    return HttpResponse("Welcome Customer")