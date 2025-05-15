from .settings import *

# Par exemple, utiliser une base de données SQLite temporaire pour les tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
