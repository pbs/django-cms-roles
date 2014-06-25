from django.contrib.auth.models import User, Group
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db import models, connection
from django.db.models import signals, Q
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

from cms.models.permissionmodels import (
    AbstractPagePermission, GlobalPagePermission, PagePermission)
from cms.models import ACCESS_PAGE_AND_DESCENDANTS
from cms.models.pagemodel import Page

import logging
logger = logging.getLogger(__name__)


def get_permission_fields():
    permission_keys = []
    for field in AbstractPagePermission._meta.fields:
        if isinstance(field, models.BooleanField) and field.name.startswith('can_'):
            permission_keys.append(field.name)
    return permission_keys


class Role(AbstractPagePermission):
    """
    A Role references a django group and adds cms specific permissions on top of it.

    A Role object can function in two modes:
    * site wide (is_site_wide = True)
    * on a page by page basis (is_site_wide = False)

    Being site wide means that users assigned to this Role on a particular site
    are able to access all of that site's pages.
    Otherwise, for roles functioning on a page by page basis you will need to
    explicitly specify the pages you will grant access on.

    When is_site_wide is True the role will maintain derived_global_permissions
    When is_site_wide is False this role will maintain derived_page_permissions

    Invariants:
    * one of derived_page_permissions or derived_global_permissions
      must always be empty
    """

    class Meta:
        abstract = False
        app_label = 'cmsroles'
        verbose_name = _('role')
        verbose_name_plural = _('roles')
        permissions = (('user_setup', 'Can access user setup'),)

    group_name_pattern = '%(role_name)s-%(site_domain)s'

    name = models.CharField(max_length=50, unique=True)

    is_site_wide = models.BooleanField(default=True)

    # used when is_site_wide is True
    derived_global_permissions = models.ManyToManyField(
        GlobalPagePermission, blank=True, null=True)

    # used when is_site_wide is False
    derived_page_permissions = models.ManyToManyField(
        PagePermission, blank=True, null=True)

    def __unicode__(self):
        return self.name

    def __init__(self, *args, **kwargs):
        super(Role, self).__init__(*args, **kwargs)
        self._old_group = self.group_id
        self._old_is_site_wide = self.is_site_wide
        self._old_name = self.name

    def clean(self):
        if self.group is not None:
            filter_clause = Q(group=self.group) | (
                Q(derived_global_permissions__group=self.group) &
                Q(is_site_wide=True))
            query = Role.objects.filter(filter_clause)
            if self.pk:
                query = query.exclude(pk=self.pk)
            if query.exists():
                raise ValidationError(u'A Role for group "%s" already exists' % self.group.name)

    def update_site_groups(self, update_names, update_permissions):
        if update_permissions:
            new_group_permissions = self.group.permissions.all()

        global_perm_q = self.derived_global_permissions.select_related(
            'group', 'sites')
        site_groups = [(global_perm.group, global_perm.sites.all()[0])
                       for global_perm in global_perm_q]
        for group, site in site_groups:
            if update_permissions:
                group.permissions = new_group_permissions

            if update_names:
                group.name = Role.group_name_pattern % {
                    'role_name': self.name,
                    'site_domain': site.domain}
                group.save()

    def _propagate_perm_changes(self, derived_perms):
        permissions = self._get_permissions_dict()
        for gp in derived_perms:
            for key, value in permissions.iteritems():
                setattr(gp, key, value)
            gp.save()

    def save(self, *args, **kwargs):
        super(Role, self).save(*args, **kwargs)
        if self.is_site_wide:
            group_changed = (self._old_group is not None and
                             self._old_group != self.group_id)
            role_name_changed = self._old_name != self.name
            if group_changed or role_name_changed:
                self.update_site_groups(
                    update_names=True,
                    update_permissions=group_changed)
            # TODO: improve performance by having less queries
            derived_global_permissions = self.derived_global_permissions.all()
            covered_sites = set(derived_global_permissions.values_list('sites', flat=True))
            for site in Site.objects.exclude(pk__in=covered_sites):
                self.add_site_specific_global_page_perm(site)
            self._propagate_perm_changes(derived_global_permissions)
        else:
            self._propagate_perm_changes(self.derived_page_permissions.all())

        if self.is_site_wide != self._old_is_site_wide:
            if self.is_site_wide:
                for page_perm in self.derived_page_permissions.all():
                    self.grant_to_user(page_perm.user, page_perm.page.site)
                    page_perm.delete()
            else:
                for global_page_perm in self.derived_global_permissions.all():
                    sites = global_page_perm.sites.all()
                    if len(sites) != 1:
                        logger.error(u'Auto generated global page permission was fiddled')
                        continue
                    site = sites[0]
                    users = global_page_perm.group.user_set.all()
                    try:
                        first_page = Page.objects.filter(site=site)\
                            .order_by('tree_id', 'lft')[0]
                    except IndexError:
                        if len(users) > 0:
                            users_str = ', '.join(list(users))
                            logger.error(u'Users %s lost role %s on site %s after '
                                           'making the site non site wide' % (
                                    users_str, self.name, site.domain))
                    else:
                        for user in users:
                            self.grant_to_user(user, site, [first_page])
                    global_page_perm.group.delete()

    def delete(self, *args, **kwargs):
        for global_perm in self.derived_global_permissions.all():
            # global_perm will also get deleted by cascading from global_perm.group
            global_perm.group.delete()
        for page_perm in self.derived_page_permissions.all():
            page_perm.delete()
        return super(Role, self).delete(*args, **kwargs)

    def _get_permissions_dict(self):
        return dict((key, getattr(self, key))
                    for key in get_permission_fields())

    def _get_group_permimssion_name_len(self):
        """Get the """
        site_perm_max_len = 80
        for meta_field in self.group.__class__._meta.fields:
            if meta_field.name == 'name':
                site_perm_max_len = meta_field.max_length
        return site_perm_max_len

    def add_site_specific_global_page_perm(self, site):
        if not self.is_site_wide:
            return
        site_group = Group.objects.get(pk=self.group.pk)
        permissions = self.group.permissions.all()
        site_group.pk = None

        # don't exceed the max length of the group name
        site_perm_max_len = self._get_group_permimssion_name_len()
        site_group.name = Role.group_name_pattern % {
            'role_name': self.name[:site_perm_max_len],
            'site_domain': site.domain[:site_perm_max_len - len(self.name)]}
        site_group.save()
        site_group.permissions = permissions
        kwargs = self._get_permissions_dict()
        kwargs['group'] = site_group
        gp = GlobalPagePermission.objects.create(**kwargs)
        gp.sites.add(site)
        self.derived_global_permissions.add(gp)

    def grant_to_user(self, user, site, pages=None):
        """Grant the given user this role for given site"""
        if self.is_site_wide:
            user.groups.add(self.get_site_specific_group(site))
        else:
            if pages is None or len(pages) == 0:
                raise ValidationError('At lest a page must be given')
            # delete the existing page perms
            self.get_user_page_perms(user, site).delete()
            # and assign the new ones
            for page in pages:
                page_permission = PagePermission(
                    page=page, user=user,
                    grant_on=ACCESS_PAGE_AND_DESCENDANTS)
                for key, value in self._get_permissions_dict()\
                        .iteritems():
                    setattr(page_permission, key, value)
                page_permission.save()
                self.derived_page_permissions.add(page_permission)
            user.groups.add(self.group)
        if not user.is_staff:
            user.is_staff = True
            user.save()

    def ungrant_from_user(self, user, site):
        """Remove the given user from this role from the given site"""
        # TODO: Extract some 'state' class that implements the
        #       is/isn't site wide differences or create two different
        #       Role classes
        if self.is_site_wide:
            user.groups.remove(self.get_site_specific_group(site))
        else:
            for perm in self.derived_page_permissions.filter(page__site=site, user=user):
                perm.delete()
            if self.derived_page_permissions.count() == 0:
                user.groups.remove(self.group)

    def all_users(self):
        """Returns all users having this role."""
        if self.is_site_wide:
            qs = User.objects.filter(groups__globalpagepermission__role=self)
        else:
            qs = User.objects.filter(groups=self.group)
        return qs.distinct()

    def users(self, site):
        """Returnes all users having this role in the given site."""
        if self.is_site_wide:
            global_page_perm = self.derived_global_permissions.filter(sites=site)
            users = list(
                User.objects.filter(groups__globalpagepermission=global_page_perm))
        else:
            page_perms = self.derived_page_permissions.filter(
                page__site=site).select_related('user')
            users = set(perm.user for perm in page_perms if perm.user is not None)
            users = list(users)
        return users

    def get_site_specific_group(self, site):
        # TODO: enforce there is one global page perm per site
        #       the derived global page permissions should always have
        #       a single site, but there's nothing stopping super-users
        #       from messing around with them
        return self.derived_global_permissions.get(sites=site).group

    def get_user_page_perms(self, user, site):
        """For a non site wide role, returns the pages that the given
        user has access to on the given site."""
        if self.is_site_wide:
            raise ValueError(
                'This makes sense only for non site wide roles')
        return self.derived_page_permissions.filter(page__site=site, user=user)


@receiver(signals.pre_delete, sender=Group)
def delete_role(instance, **kwargs):
    """When group that a role uses gets deleted, that role also
    and all of the auto generated page permissions and groups
    also need to be deleted. Whithout this pre_delete signal the
    role would be deleted, but the deletion would happen without going
    through the role's delete method
    """
    for role in Role.objects.filter(group=instance):
        # Role.objects.filter(group=instance) should
        # return 0 or 1 roles objects, unless someone
        # created role objects without going through .clean
        role.delete()


@receiver(signals.post_save, sender=Site)
def create_role_groups(instance, **kwargs):
    site = instance
    if all((kwargs['created'],
            'cmsroles_role' in connection.introspection.table_names())):
        for role in Role.objects.all():
            role.add_site_specific_global_page_perm(site)


@receiver(signals.pre_save, sender=Site)
def attach_old_domain_attr(instance, **kwargs):
    """Attach a magic attribute named _old_domain that is then used
    by the update_site_group_names for updating all of the
    auto generated site groups' names
    """
    site = instance
    try:
        site._old_domain = Site.objects.get(pk=site.pk).domain
    except Site.DoesNotExist:
        pass


@receiver(signals.post_save, sender=Site)
def update_site_group_names(instance, **kwargs):
    """Update all of the auto generated site groups' names"""
    site = instance
    if  hasattr(site, '_old_domain') and site.domain != site._old_domain:
        for role in Role.objects.all():
            role.update_site_groups(
                update_names=True,
                update_permissions=False)


@receiver(signals.pre_delete, sender=Site)
def attach_role_groups_attr(instance, **kwargs):
    """Attach a magic attribute amed _role_groups that is then
    used by delete_role_groups for deleting all of the
    auto generated site groups that 'belonged' to this site
    and any role
    """
    instance._role_groups = []
    for role in Role.objects.all():
        try:
            role_site_group = role.get_site_specific_group(instance)
        except GlobalPagePermission.DoesNotExist:
            # this might happen if site specific global page
            #   permission got deleted
            pass
        else:
            if role_site_group:
                instance._role_groups.append(role_site_group)


@receiver(signals.post_delete, sender=Site)
def delete_role_groups(instance, **kwargs):
    """Delete all of the auto generated site groups that 'belonged' to
    this site and any role.
    """
    for site_group in getattr(instance, '_role_groups', []):
        site_group.delete()


@receiver(signals.m2m_changed, sender=Group.permissions.through)
def update_site_specific_groups(instance, **kwargs):
    """This signal handler updates all auto generated groups
    that are being managed by a role when the base group on which
    the role is built gets updated
    """
    action = kwargs['action']
    if not action.startswith('post_'):
        return
    group = instance
    try:
        role = Role.objects.get(group=group)
    except Role.DoesNotExist:
        return
    else:
        role.update_site_groups(
            update_names=False,
            update_permissions=True)


@receiver(signals.post_save, sender=User)
def clear_roles_for_inactive_user(instance, **kwargs):
    if instance.is_active:
        return
    from cmsroles.siteadmin import get_user_roles_on_sites_ids
    roles_on_sites = get_user_roles_on_sites_ids(instance)
    for role in Role.objects.filter(id__in=roles_on_sites.keys()):
        for site in Site.objects.filter(id__in=roles_on_sites[role.id]):
            role.ungrant_from_user(instance, site)
