import os
from django.conf import global_settings
import djcelery

djcelery.setup_loader()

def collapse_to_unique_list(*args):
    """Create a new list with all elements from a given lists without reapeated
    elements

    """
    combined = []
    for arg in args:
        for elem in arg or ():
            if elem not in combined:
                combined.append(elem)
    return combined


def augment_settings(settings):

    # order is important:
    # otree unregisters User & Group, which are installed by auth.
    # otree templates need to get loaded before the admin.
    new_installed_apps = collapse_to_unique_list([
            'django.contrib.auth',
            'otree',
            'floppyforms',
            'django.contrib.admin',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'otree.session',
            'otree.models_concrete',
            'otree.timeout',
            'djcelery',
        ],
        settings['INSTALLED_APPS'],
        settings['INSTALLED_OTREE_APPS']
    )

    new_template_dirs = collapse_to_unique_list(
        [
            os.path.join(settings['BASE_DIR'], 'templates/')
        ],
        settings.get('TEMPLATE_DIRS')
    )

    new_staticfiles_dirs = collapse_to_unique_list(
        settings.get('STATICFILES_DIRS'),
        [
            os.path.join(settings['BASE_DIR'], 'static')
        ]
    )

    new_middleware_classes = collapse_to_unique_list(
        [
            'django.contrib.sessions.middleware.SessionMiddleware',
            #'django.middleware.locale.LocaleMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware'
        ],
        settings.get('MIDDLEWARE_CLASSES')
    )

    augmented_settings = {
        'INSTALLED_APPS': new_installed_apps,
        'TEMPLATE_DIRS': new_template_dirs,
        'STATICFILES_DIRS': new_staticfiles_dirs,
        'MIDDLEWARE_CLASSES': new_middleware_classes,
    }


    LANGUAGE_CODE = (
        settings.get('LANGUAGE_CODE') or global_settings.LANGUAGE_CODE
    )
    CURRENCY_LOCALE = settings.get('CURRENCY_LOCALE', '')
    if not CURRENCY_LOCALE:

        # favor en_GB currency formatting since it represents negative amounts
        # with minus signs rather than parentheses
        if LANGUAGE_CODE[:2] == 'en':
            CURRENCY_LOCALE = 'en_GB'
        else:
            CURRENCY_LOCALE = LANGUAGE_CODE
    CURRENCY_LOCALE = CURRENCY_LOCALE.replace('-','_')

    logging = {
        'version': 1,
        'disable_existing_loggers': False,
        'root': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'formatters': {
            'verbose': {
                'format': '[%(levelname)s|%(asctime)s] %(name)s > %(message)s'
            },
            'simple': {
                'format': '%(levelname)s %(message)s'
            },
        },
        'handlers': {
            'console':{
                'level':'INFO',
                'class':'logging.StreamHandler',
                'formatter': 'verbose'
            },
        },
        'loggers': {
            'otree.test.core':{
                'handlers': ['console'],
                'propagate': False,
                'level': 'INFO',
            },
        }
    }

    overridable_settings = {

        # pages with a time limit for the player can have a grace period
        # to compensate for network latency.
        # the timer is started and stopped server-side,
        # so this grace period should account for time spent during
        # download, upload, page rendering, etc.
        'TIMEOUT_LATENCY_ALLOWANCE_SECONDS': 10,

        'SESSION_SAVE_EVERY_REQUEST': True,
        'TEMPLATE_DEBUG': settings['DEBUG'],
        'STATIC_ROOT': 'staticfiles',
        'STATIC_URL': '/static/',
        'ROOT_URLCONF': 'otree.default_urls',
        'PAYMENT_CURRENCY_CODE': 'USD',
        'CURRENCY_LOCALE': CURRENCY_LOCALE,
        'LANGUAGE_CODE': LANGUAGE_CODE,
        'CURRENCY_DECIMAL_PLACES': 2,
        'TIME_ZONE': 'UTC',
        'USE_TZ': True,
        'SESSION_SERIALIZER': (
            'django.contrib.sessions.serializers.PickleSerializer'
        ),
        'ALLOWED_HOSTS': ['*'],
        'OTREE_CHANGE_LIST_COLUMN_MIN_WIDTH': 50, # In pixels
        'OTREE_CHANGE_LIST_UPDATE_INTERVAL': '10000', # default to 10 seconds(10000 miliseconds)
        'TEMPLATE_CONTEXT_PROCESSORS': (
            global_settings.TEMPLATE_CONTEXT_PROCESSORS +
            ('django.core.context_processors.request',)
        ),
        'SESSIONS_MODULE': 'sessions',
        'LOGGING': logging
    }


    settings.update(augmented_settings)

    for k, v in overridable_settings.items():
        if not settings.has_key(k):
            settings[k] = v

    # payment is in Money, which is hardcoded to look at CURRENCY_CODE
    settings['CURRENCY_CODE'] = settings['PAYMENT_CURRENCY_CODE']
    settings['CURRENCY_FORMAT'] = settings['PAYMENT_CURRENCY_CODE']
    settings['CURRENCY_CODE'] = settings['PAYMENT_CURRENCY_CODE']

    if settings.get('USE_POINTS'):
        settings['GAME_CURRENCY_CODE'] = 'points'
        settings['GAME_CURRENCY_FORMAT'] = settings.get('CURRENCY_FORMAT') or u'# points'
        settings['GAME_CURRENCY_DECIMAL_PLACES'] = 0
    else:
        settings['GAME_CURRENCY_CODE'] = settings['PAYMENT_CURRENCY_CODE']
        settings['GAME_CURRENCY_FORMAT'] = settings['PAYMENT_CURRENCY_CODE']
        settings['GAME_CURRENCY_CODE'] = settings['PAYMENT_CURRENCY_CODE']


