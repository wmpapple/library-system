# backend/app/config.py

# admin registration secret
ADMIN_REGISTRATION_SECRET = "LMS_ADMIN_2025"

# Constants for system settings
OVERDUE_RESERVATION_CHECK_INTERVAL_KEY = "overdue_reservation_check_interval"
DEFAULT_OVERDUE_RESERVATION_CHECK_INTERVAL = 20 # seconds

OVERDUE_BORROW_GRACE_PERIOD_KEY = "overdue_borrow_grace_period"
DEFAULT_OVERDUE_BORROW_GRACE_PERIOD = 5 # seconds

# Fine calculation constants
FINE_PER_UNIT = 1.0  # 1 Yuan per unit
FINE_UNIT_MINUTES = 5 # Fine unit duration in minutes

# Email settings for conflict notification
EMAIL_ENABLED = True  # Set to False to disable email notifications
SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 587
SMTP_USER = "2482970191@qq.com"
SMTP_PASSWORD = "wlxjpathqqsoecgj" 
SMTP_TLS = True
SMTP_SSL = False