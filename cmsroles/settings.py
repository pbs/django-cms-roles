from django.conf import settings

# Note: This works only if admin base templates include Bootstrap 
# 	Ace resources
USE_BOOTSTRAP_ACE = getattr(
    settings, 'CMSROLES_USE_BOOTSTRAP_ACE', False)
