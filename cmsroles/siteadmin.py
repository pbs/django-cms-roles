from django.contrib.auth.models import Permission
from django.contrib.sites.models import Site
from django.db.models import Q
from collections import defaultdict
from cmsroles.models import Role


def get_site_admin_required_permission():
    return Permission.objects.get(content_type__model='role', codename='user_setup')


def is_site_admin(user):
    """Returns whether user is a site admin. A user is a site admin
    if he is a super user or has the 'has access to user setup' permission.
    """
    if user.is_superuser:
        return True
    req_perm_obj = get_site_admin_required_permission()
    req_perm = '%s.%s' % (req_perm_obj.content_type.app_label,
                          req_perm_obj.codename)
    return user.is_staff and req_perm in user.get_all_permissions()


def is_site_admin_group(group):
    """Returns whether group gives site admin rights to the users
    that belong to it.
    """
    return get_site_admin_required_permission() in group.permissions.all()


def get_administered_sites(user):
    """Returns a list of sites on which user has administrative rights"""
    if user.is_superuser:
        return [s for s in Site.objects.all()]
    sites = []

    def lookup_sites(auth_obj):
        for global_perm in auth_obj.globalpagepermission_set.\
                prefetch_related('sites').all():
            sites.extend(global_perm.sites.all())

    for group in user.groups.all():
        if is_site_admin_group(group):
            lookup_sites(group)
    lookup_sites(user)

    return sites


def get_site_users(site):
    """Returns a dictionary containing all users mapped to their role
    that belong to site.
    """
    users_to_roles = {}
    for role in Role.objects.all():
        for user in role.users(site):
            users_to_roles[user] = role
    return users_to_roles


def get_user_roles_on_sites_ids(user):
    """
        Returns a dictionary with all roles that a user has, mapped to the
        site where the user has that specific role.
    """
    qry = Q(Q(derived_page_permissions__user=user) |
            Q(derived_global_permissions__group__user=user))
    roles_with_sites = Role.objects.filter(qry).values_list(
        'id',
        'derived_global_permissions__sites',
        'derived_page_permissions__page__site').distinct()

    result_data = defaultdict(set)
    for role_id, global_perm_site, page_perm_site in roles_with_sites:
        result_data[role_id].add(global_perm_site or page_perm_site)
    return result_data
