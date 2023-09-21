# from rest_framework import serializers
# from products.models import Product

# class ProductSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Product
#         fields = '__all__'

from rest_framework import serializers
from .models import Word

class WordSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = Word 
        fields = ['word', 'laymans']