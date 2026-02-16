import hashlib
import os
# import sentry_sdk

from pathlib import Path

from django.urls import reverse_lazy
from environs import Env
# from sentry_sdk.integrations.django import DjangoIntegration

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

BASE_DIR = Path(__file__).resolve().parent.parent

env = Env()
env.read_env()

SECRET_KEY = env.str("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
API_TOKEN = env.str("API_TOKEN")
ADMIN = env.str("ADMIN")
DOMAIN_URL = env.str("DOMAIN_URL")

encoded_api_token = API_TOKEN.encode()
WEBHOOK_PATH = 'tgbot/' + hashlib.md5(encoded_api_token).hexdigest()
WEBHOOK_URL = f"{DOMAIN_URL}/{WEBHOOK_PATH}"

ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    # 'jazzmin',

    "unfold",  # before django.contrib.admin
    "unfold.contrib.filters",  # optional, if special filters are needed
    "unfold.contrib.forms",  # optional, if special form elements are needed
    "unfold.contrib.inlines",  # optional, if special inlines are needed
    "unfold.contrib.import_export",  # optional, if django-import-export package is used
    "unfold.contrib.guardian",  # optional, if django-guardian package is used
    "unfold.contrib.simple_history",  # optional, if django-simple-history package is used
    "unfold.contrib.location_field",  # optional, if django-location-field package is used
    "unfold.contrib.constance",  # optional, if django-constance package is used

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Download
    'tinymce',
    'django_celery_beat',

    # Local
    'responder',
    'broadcast',
    'commands',
]

if DEBUG:
    pass
    # INSTALLED_APPS.append('debug_toolbar')

print(f"\n{DEBUG = }\n")

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if not DEBUG:
    index = INSTALLED_APPS.index('django.contrib.staticfiles')
    INSTALLED_APPS.insert(index, "whitenoise.runserver_nostatic")
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware", )
else:
    pass
    # MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")

ROOT_URLCONF = 'src.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'src.wsgi.application'

DBS = {
    'sqlite': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
    'postgres': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env.str("DB_NAME"),
        'USER': env.str("DB_USER"),
        'PASSWORD': env.str("DB_PASSWORD"),
        'HOST': env.str("DB_HOST"),
        'PORT': env.str("DB_PORT"),
    },
    'pgbouncer': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env.str("DB_NAME"),
        'USER': env.str("DB_USER"),
        'PASSWORD': env.str("DB_PASSWORD"),
        'HOST': env.str("PGBOUNCER_HOST"),
        'PORT': env.str("PGBOUNCER_PORT"),
        'CONN_MAX_AGE': 0
    }
}

DATABASES = {
    "default": DBS[env.str("DB_TYPE", default='sqlite')]
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    'responder/static'
]

if not DEBUG:
    STORAGES = {
        # ...
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "LOCATION": os.path.join(BASE_DIR, "media"),
        }
    }
    WHITENOISE_KEEP_ONLY_HASHED_FILES = False

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# redis settings
REDIS_HOST = env.str("REDIS_HOST", "redis")
REDIS_PORT = env.int("REDIS_PORT", 6379)
REDIS_DB = env.int("REDIS_DB", 0)
REDIS_URL = f'{REDIS_HOST}://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Celery settings
CELERY_BROKER_URL = env.str('CELERY_BROKER_URL', default="redis://localhost:6379/0")  # Используем Redis
CELERY_RESULT_BACKEND = env.str('CELERY_RESULT_BACKEND', default="redis://localhost:6379/1")
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_EXTENDED = True
CELERY_TIMEZONE = TIME_ZONE

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env.str("CACHE_URL", default="redis://localhost:6379/2"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Tiny settings
TINYMCE_DEFAULT_CONFIG = {
    "height": "320px",
    # "width": "960px",
    "menubar": False,
    "plugins": "link code",
    "toolbar": "undo redo | bold italic | link | code",
    "custom_undo_redo_levels": 10,
    "language": "ru_Ru",
}

INTERNAL_IPS = [
    # ...
    "127.0.0.1",
    # ...
]

CSRF_TRUSTED_ORIGINS = [
    env.str("DOMAIN_URL", "http://localhost:8891"),
]
X_FRAME_OPTIONS = 'SAMEORIGIN'

if env.str("DOMAIN_URL"):
    CSRF_TRUSTED_ORIGINS.append(env.str("DOMAIN_URL"))

UNFOLD = {
    "SITE_TITLE": "EXOTIC",
    "SITE_HEADER": "EXOTIC",
    "SITE_URL": "/admin/",
    "SITE_SYMBOL": "receipt",
    "SITE_FAVICONS": [
        # {
        #     "rel": "icon",
        #     "sizes": "32x32",
        #     "type": "image/svg+xml",
        #     # "href": lambda request: static("logo.svg"),
        # },
    ],
    "SHOW_HISTORY": False,
    "SHOW_VIEW_ON_SITE": False,
    "ENVIRONMENT": "PDF-Checker",
    "LOGIN": {
        "redirect_after": lambda request: reverse_lazy("admin:index"),
    },
    "COLORS": {
        "primary": {
            "50": "oklch(97.7% .014 308.299)",
            "100": "oklch(94.6% .033 307.174)",
            "200": "oklch(90.2% .063 306.703)",
            "300": "oklch(82.7% .119 306.383)",
            "400": "oklch(71.4% .203 305.504)",
            "500": "oklch(62.7% .265 303.9)",
            "600": "oklch(55.8% .288 302.321)",
            "700": "oklch(49.6% .265 301.924)",
            "800": "oklch(43.8% .218 303.724)",
            "900": "oklch(38.1% .176 304.987)",
            "950": "oklch(29.1% .149 302.717)",
        },
    },
    "EXTENSIONS": {
        "modeltranslation": {
            "flags": {
                "en": "🇺🇸",
                "fr": "🇫🇷",
                "nl": "🇳🇱",
                "pl": "🇵🇱",
                "ru": "🇷🇺",
                "uk": "🇺🇦",
            },
        },
    },
    # "STYLES": [
    #     "/static/css/admin_global.css",
    # ],
    # "SCRIPTS": [
    #     "/static/js/admin_global.js",
    # ],
    # "APPS": {
    #     "django_celery_beat": "unfold.contrib.celery_beat",
    # },

    "APPS": {
        "django_celery_beat": "unfold.contrib.celery_beat",  # ЭТА СТРОКА ВСЁ ЧИНИТ
    },

    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "items": [
                    {
                        "title": "Аналитика",
                        "icon": "analytics",
                        # "link": lambda request: reverse_lazy("admin:common_analytics_changelist"),
                        # "link": lambda request: reverse_lazy("admin:index"),
                        "link": lambda request: reverse_lazy("admin-analytics"),
                    },
                ],
            },
            {
                "title": "Автоответчик",
                "separator": True,
                "items": [
                    {
                        "title": "Маски",
                        "icon": "book_6",
                        "link": lambda request: reverse_lazy("admin:responder_mask_changelist"),
                    },
                    {
                        "title": "Команды",
                        "icon": "code_blocks",
                        "link": lambda request: reverse_lazy("admin:responder_telegramcommand_changelist"),
                    },
                    {
                        "title": "Пользователи",
                        "icon": "person_pin",
                        "link": lambda request: reverse_lazy("admin:responder_telegramuser_changelist"),
                    },
                    {
                        "title": "Сообщения",
                        "icon": "chat",
                        "link": lambda request: reverse_lazy("admin:responder_telegrammessage_changelist"),
                    },
                    {
                        "title": "Группы",
                        "icon": "family_group",
                        "link": lambda request: reverse_lazy("admin:responder_telegramgroup_changelist"),
                    },
                    {
                        "title": "Аналитика",
                        "icon": "analytics",
                        "link": lambda request: reverse_lazy("admin:responder_faq_changelist"),
                    },
                    {
                        "title": "Настройки",
                        "icon": "settings",
                        "link": lambda request: reverse_lazy("admin:responder_data_changelist"),
                    },

                ],
            },
            {
                "title": "Верификации",
                "separator": True,
                "items": [
                    {
                        "title": "Все верификации",
                        "icon": "fingerprint",
                        "link": lambda request: reverse_lazy("admin:responder_allverification_changelist"),
                    },
                    # {
                    #     "title": "Верификациа",
                    #     "icon": "fingerprint",
                    #     "link": lambda request: reverse_lazy("admin:responder_verification_changelist"),
                    # },
                    {
                        "title": "Текущие верификации",
                        "icon": "fingerprint",
                        "link": lambda request: reverse_lazy("admin:responder_currentverification_changelist"),
                    },
                    {
                        "title": "Архив",
                        "icon": "fingerprint",
                        "link": lambda request: reverse_lazy("admin:responder_archivedverification_changelist"),
                    },
                    # {
                    #     "title": "Дополнительное поле",
                    #     "icon": "check_box",
                    #     "link": lambda request: reverse_lazy("admin:responder_verificationadminfield_changelist"),
                    # },
                ]
            },
            {
                "title": "Отчеты",
                "separator": True,
                "items": [
                    {
                        "title": "Страна",
                        "icon": "assignment_globe",
                        "link": lambda request: reverse_lazy("admin:responder_country_changelist"),
                    },
                    {
                        "title": "Статический текст",
                        "icon": "text_compare",
                        "link": lambda request: reverse_lazy("admin:responder_statictext_changelist"),
                    },
                    {
                        "title": "Профиль",
                        "icon": "account_circle",
                        "link": lambda request: reverse_lazy("admin:responder_profile_changelist"),
                    },
                    {
                        "title": "Смена сотрудника",
                        "icon": "data_array",
                        "link": lambda request: reverse_lazy("admin:responder_workerdata_changelist"),
                    },
                    {
                        "title": "Мерчанты",
                        "icon": "point_of_sale",
                        "link": lambda request: reverse_lazy("admin:responder_merchant_changelist"),
                    },
                    {
                        "title": "Статистика диспутов по мерчантам",
                        "icon": "analytics",
                        "link": lambda request: reverse_lazy("admin:responder_workermerchantstat_changelist"),
                    }
                ]
            },
            {
                "title": "Реклама",
                "separator": True,
                "items": [
                    {
                        "title": "Медиа",
                        "icon": "event_upcoming",
                        "link": lambda request: reverse_lazy("admin:broadcast_media_changelist"),
                    },
                    {
                        "title": "Рассылка",
                        "icon": "newsmode",
                        "link": lambda request: reverse_lazy("admin:broadcast_broadcast_changelist"),
                    },
                    {
                        "title": "Шаблоны рассылок",
                        "icon": "dynamic_feed",
                        "link": lambda request: reverse_lazy("admin:broadcast_broadcasttemplate_changelist"),
                    },
                ]
            },
            {
                "title": "Фоновые задачи",
                "separator": True,
                "items": [
                    {
                        "title": "Периодические задачи",
                        "icon": "task",
                        "link": lambda request: reverse_lazy("admin:django_celery_beat_periodictask_changelist")
                    },
                    {
                        "title": "Запланированное время",
                        "icon": "chronic",
                        "link": lambda request: reverse_lazy("admin:django_celery_beat_clockedschedule_changelist")
                    }
                ]
            },
            {
                "title": "Настройки",
                "separator": True,
                "items": [
                    {
                        "title": "Администраторы",
                        "icon": "admin_panel_settings",
                        "link": lambda request: reverse_lazy("admin:auth_user_changelist"),
                    },
                ],
            },
        ],
    },
}

JAZZMIN_SETTINGS = {
    # title of the window (Will default to current_admin_site.site_title if absent or None)
    "site_title": "EXOTIC",

    # Title on the login screen (19 chars max) (defaults to current_admin_site.site_header if absent or None)
    "site_header": "EXOTIC",

    # Title on the brand (19 chars max) (defaults to current_admin_site.site_header if absent or None)
    "site_brand": "EXOTIC",

    # Logo to use for your site, must be present in static files, used for brand on top left
    # "site_logo": "",

    # Logo to use for your site, must be present in static files, used for login form logo (defaults to site_logo)
    "login_logo": None,

    # Logo to use for login form in dark themes (defaults to login_logo)
    "login_logo_dark": None,

    # CSS classes that are applied to the logo above
    "site_logo_classes": "img-circle",

    # Relative path to a favicon for your site, will default to site_logo if absent (ideally 32x32 px)
    "site_icon": None,

    # Welcome text on the login screen
    "welcome_sign": "Welcome to the Autoresponder Bot Admin Panel",

    # Copyright on the footer
    "copyright": "Acme Library Ltd",

    # List of model admins to search from the search bar, search bar omitted if excluded
    # If you want to use a single search field you dont need to use a list, you can use a simple string
    "search_model": ["responder.TelegramUser", "responder.TelegramGroup"],

    # Field name on user model that contains avatar ImageField/URLField/Charfield or a callable that receives the user
    "user_avatar": None,

    ############
    # Top Menu #
    ############

    # Links to put along the top menu
    "topmenu_links": [

        # Url that gets reversed (Permissions can be added)
        {
            "name": "Главная",
            "url": "admin:index",
            "icon": "fas fa-chart-line",
            "permissions": ["auth.view_user"]
        },

        # external url that opens in a new window (Permissions can be added)
        {"name": "Аналитика", "url": "admin-analytics", "new_window": False},

        # model admin to link to (Permissions checked against model)
        # {"model": "auth.User"},

        # App with dropdown menu to all its models pages (Permissions checked against models)
        {"app": "responder"},
        {"app": "broadcast"},
    ],

    #############
    # User Menu #
    #############

    # Additional links to include in the user menu on the top right ("app" url type is not allowed)
    # "usermenu_links": [
    #     {"name": "Support", "url": "https://github.com/farridav/django-jazzmin/issues", "new_window": True},
    #     {"model": "responder.TelegramUser"}
    # ],

    #############
    # Side Menu #
    #############

    # Whether to display the side menu
    "show_sidebar": True,

    # Whether to aut expand the menu
    "navigation_expanded": True,

    # Hide these apps when generating side menu e.g (auth)
    # "hide_apps": ['django_celery_beat'],

    # Hide these models when generating side menu (e.g auth.user)
    "hide_models": [
        'django_celery_beat.SolarSchedule',
        'django_celery_beat.IntervalSchedule',
        'django_celery_beat.TzAwareCrontab',
        'django_celery_beat.ClockedSchedule',
    ],

    # List of apps (and/or models) to base side menu ordering off of (does not need to contain all apps/models)
    "order_with_respect_to": [
        "auth",

        "responder",
        "responder.Mask",
        "responder.TelegramCommand",
        "responder.TelegramUser",
        "responder.TelegramMessage",
        "responder.TelegramGroup",
        "responder.FAQ",
        "responder.Data",

        "broadcast",
        "broadcast.Media",
        "broadcast.Broadcast",
        "broadcast.BroadcastTemplate",

        # "commands",
        # "commands.CrontabScheduleProxy",
        # "commands.PeriodicTaskProxy",
        "django_celery_beat",
        "django_celery_beat.CrontabSchedule",
        "django_celery_beat.PeriodicTask",
    ],

    "icons": {
        "admin:index": "fas fa-gauge",

        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",

        "responder.Data": "fas fa-solid fa-sliders",
        "responder.Mask": "fas fa-book",
        "responder.TelegramUser": "fas fa-user-tie",
        "responder.TelegramGroup": "fas fa-people-group",
        "responder.TelegramMessage": "fas fa-comment-dots",
        "responder.TelegramCommand": "fas fa-terminal",
        "responder.FAQ": "fas fa-chart-bar",

        "broadcast.Media": "fas fa-paperclip",
        "broadcast.BroadcastTemplate": "fas fa-photo-film",
        "broadcast.Broadcast": "fas fa-newspaper",

        "django_celery_beat.PeriodicTask": "fas fa-list-check",
        "django_celery_beat.CrontabSchedule": "fas fa-calendar-days",

    },
    # Icons that are used when one is not manually specified
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",

    #################
    # Related Modal #
    #################
    # Use modals instead of popups
    "related_modal_active": True,

    #############
    # UI Tweaks #
    #############
    # Relative paths to custom CSS/JS scripts (must be present in static files)
    "custom_css": None,
    "custom_js": None,
    # Whether to link font from fonts.googleapis.com (use custom_css to supply font otherwise)
    "use_google_fonts_cdn": True,
    # Whether to show the UI customizer on the sidebar
    "show_ui_builder": False,

    ###############
    # Change view #
    ###############
    # Render out the change view as a single form, or in tabs, current options are
    # - single
    # - horizontal_tabs (default)
    # - vertical_tabs
    # - collapsible
    # - carousel
    "changeform_format": "horizontal_tabs",
    # override change forms on a per modeladmin basis
    # "changeform_format_overrides": {"auth.user": "collapsible", "auth.group": "vertical_tabs"},
    # Add a language dropdown into the admin
    "language_chooser": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": False,
    "accent": "accent-dark",
    "navbar": "navbar-white navbar-light",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-light",
    "sidebar_nav_small_text": True,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-dark",
        "secondary": "btn-secondary",
        "info": "btn-secondary",
        "warning": "btn-dark",
        "danger": "btn-danger",
        "success": "btn-outline-dark"
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs/django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'WARNING',
    },
}

# sentry_sdk.init(
#     dsn="https://09bbc66c6a6a0865740aea0db3187fce@o4509489682710528.ingest.de.sentry.io/4509489684349008",
#     integrations=[DjangoIntegration()],
#     traces_sample_rate=1.0,
#     send_default_pii=True
# )
