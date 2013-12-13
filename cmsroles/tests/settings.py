SITE_ID = 1
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.sitemaps',
    'cms',
    'mptt',
    'menus',
    'south',
    'sekizai',
    'cmsroles',
]

CMS_TEMPLATES = [('cms_mock_template.html', 'cms_mock_template.html')]
CMS_MODERATOR = True
CMS_PERMISSION = True
STATIC_ROOT = '/static/'
STATIC_URL = '/static/'
ROOT_URLCONF = 'cmsroles.tests.urls'
TEMPLATE_CONTEXT_PROCESSORS = [
    "django.contrib.auth.context_processors.auth",
    'django.contrib.messages.context_processors.messages',
    "django.core.context_processors.i18n",
    "django.core.context_processors.debug",
    "django.core.context_processors.request",
    "django.core.context_processors.media",
    'django.core.context_processors.csrf',
    "cms.context_processors.media",
    "sekizai.context_processors.sekizai",
    "django.core.context_processors.static",
]
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME' : 'test.db', # Or path to database file if using sqlite3.
        'USER' : '', # Not used with sqlite3.
        'PASSWORD' : '', # Not used with sqlite3.
        'HOST' : '', # Set to empty string for localhost. Not used with sqlite3.
        'PORT' : '', # Set to empty string for default. Not used with sqlite3.
    }
}
MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)
TEMPLATE_LOADERS = (
    'cmsroles.tests.utils.MockLoader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    )
CACHE_BACKEND = 'locmem:///'

SOUTH_TESTS_MIGRATE = False
CMS_SITE_CHOICES_CACHE_KEY = 'CMS:site_choices'
CMS_PAGE_CHOICES_CACHE_KEY = 'CMS:page_choices'
CMS_CACHE_PREFIX = 'CMS'
CMS_LANGUAGES = [
    ('en', 'English'),
]
CMS_SOFTROOT = True
CMS_TEMPLATES_INHERITANCE = False
CMS_TEMPLATE_INHERITANCE_MAGIC = 'INHERIT'
CMS_MEDIA_URL = '/media/'
