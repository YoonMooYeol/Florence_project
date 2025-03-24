from django.test import TestCase
import os
from django.conf import settings
from dotenv import load_dotenv

load_dotenv()

print(os.getenv('DJANGO_ENV'))

# Create your tests here.

