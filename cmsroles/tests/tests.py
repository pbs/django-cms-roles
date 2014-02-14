from django.test import TestCase
from django.contrib.auth.models import User, Group, Permission
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.utils import simplejson
from django.core.management import call_command

from cms.models.permissionmodels import GlobalPagePermission, PagePermission
from cms.models.pagemodel import Page
from cms.api import create_page

from cmsroles.models import Role
from cmsroles.siteadmin import (is_site_admin, get_administered_sites,
                                get_site_users,
                                get_site_admin_required_permission,
                                get_user_roles_on_sites_ids)
import cmsroles.management.commands.manage_page_permissions as manage_page_permissions

from cmsroles.views import _get_user_sites
from django.http import Http404


class HelpersMixin(object):
    def _create_site_admin_group(self):
        site_admin_group = Group.objects.create(name='site_admin')
        site_admin_group.permissions.add(get_site_admin_required_permission())
        return site_admin_group

    def _create_pages(self, site):
        master = create_page('master', 'cms_mock_template.html', language='en', site=site)
        news_page = create_page('news', 'cms_mock_template.html', language='en', site=site, parent=master)
        create_page('something happend', 'cms_mock_template.html', language='en', site=site, parent=news_page)
        create_page('blog', 'cms_mock_template.html', language='en', site=site, parent=master)
        return  master

    def _create_simple_setup(self):
        """Creates two sites, three roles and five users that have
        different roles within the two sites.

        Many tests depend on this particular setup. If you want to add
        more users, sites, roles, create a new method which calls this one...
        """
        foo_site = Site.objects.create(name='foo.site.com', domain='foo.site.com')
        bar_site = Site.objects.create(name='bar.site.com', domain='bar.site.com')
        base_site_admin_group = self._create_site_admin_group()
        admin_role = Role.objects.create(
            name='site admin', group=base_site_admin_group,
            is_site_wide=True)
        base_editor_group = Group.objects.create(name='editor')
        editor_role = Role.objects.create(
            name='editor', group=base_editor_group,
            is_site_wide=True)
        base_developer_group = Group.objects.create(name='developer')
        developer_role = Role.objects.create(
            name='developer', group=base_developer_group,
            is_site_wide=True)
        base_writer_group = Group.objects.create(name='writer')
        writer_role = Role.objects.create(
            name='writer', group=base_writer_group,
            is_site_wide=False)
        joe = User.objects.create(username='joe', is_staff=True)
        admin_role.grant_to_user(joe, foo_site)
        admin_role.grant_to_user(joe, bar_site)
        george = User.objects.create(username='george', is_staff=True)
        developer_role.grant_to_user(george, foo_site)
        robin = User.objects.create(username='robin', is_staff=True)
        editor_role.grant_to_user(robin, foo_site)
        developer_role.grant_to_user(robin, bar_site)
        jack = User.objects.create(username='jack', is_staff=True)
        admin_role.grant_to_user(jack, bar_site)
        criss = User.objects.create(username='criss', is_staff=True)
        editor_role.grant_to_user(criss, bar_site)
        vasile = User.objects.create(username='vasile', is_staff=True)
        editor_role.grant_to_user(vasile, bar_site)
        bob = User.objects.create(username='bob', is_staff=True)
        master_bar = self._create_pages(bar_site)
        self._create_pages(foo_site)
        writer_role.grant_to_user(bob, bar_site, [master_bar])

    def _create_site_with_page(self, domain):
        site = Site.objects.create(name='foo.site.com', domain='foo.site.com')
        create_page('master', 'cms_mock_template.html', language='en', site=site)
        return site

    def _create_non_site_wide_role(self):
        writer_group = Group.objects.create(name='writer')
        writer_role = Role.objects.create(
            name='writer', group=writer_group, is_site_wide=False,
            can_add=False)
        return writer_role


class SiteAdminTests(TestCase, HelpersMixin):

    def test_is_admin(self):
        self._create_simple_setup()
        joe = User.objects.get(username='joe')
        self.assertTrue(is_site_admin(joe))

    def test_get_user_roles_on_sites_ids(self):
        no_role_user = User.objects.create(
            username='portocala', is_staff=True)
        self.assertDictEqual(get_user_roles_on_sites_ids(no_role_user), {})

        self._create_simple_setup()
        bob = User.objects.get(username='bob')
        bar_site = Site.objects.get(name='bar.site.com')
        writer_role = Role.objects.get(name='writer')
        # bob is writer on bar_site
        self.assertDictEqual(get_user_roles_on_sites_ids(bob),
                             {writer_role.id: set([bar_site.id])})

        editor_role = Role.objects.get(name='editor')
        foo_site = Site.objects.get(name='foo.site.com')
        editor_role.grant_to_user(bob, foo_site)
        # bob is editor on foo_site and writer on bar_site
        self.assertDictEqual(get_user_roles_on_sites_ids(bob), {
            editor_role.id: set([foo_site.id]),
            writer_role.id: set([bar_site.id])})

        joe = User.objects.get(username='joe')
        admin_role = Role.objects.get(name='site admin')
        self.assertDictEqual(get_user_roles_on_sites_ids(joe), {
            admin_role.id: set([foo_site.id, bar_site.id]),
            })

        robin = User.objects.get(username='robin')
        developer_role = Role.objects.get(name='developer')
        # dev on bar
        self.assertDictEqual(get_user_roles_on_sites_ids(robin), {
            editor_role.id: set([foo_site.id]),
            developer_role.id: set([bar_site.id])})

    def test_get_administered_sites(self):
        self._create_simple_setup()
        joe = User.objects.get(username='joe')
        administered_sites = get_administered_sites(joe)
        self.assertItemsEqual(
            [s.domain for s in administered_sites],
            ['foo.site.com', 'bar.site.com'])
        jack = User.objects.get(username='jack')
        administered_sites = get_administered_sites(jack)
        self.assertItemsEqual(
            [s.domain for s in administered_sites],
            ['bar.site.com'])

    def test_get_administered_sites_with_user_referencing_glob_page_(self):
        foo_site = Site.objects.create(name='foo.site.com', domain='foo.site.com')
        admin_user = User.objects.create(username='gigi', password='baston')
        site_admin_perms = Permission.objects.filter(content_type__model='user')
        for perm in site_admin_perms:
            admin_user.user_permissions.add(perm)
        gpp = GlobalPagePermission.objects.create(user=admin_user)
        gpp.sites.add(foo_site)
        administered_sites = get_administered_sites(admin_user)
        self.assertEquals(len(administered_sites), 1)
        self.assertItemsEqual(
            [s.pk for s in administered_sites],
            [foo_site.pk])

    def test_not_accessible_for_non_siteadmins(self):
        joe = User.objects.create_user(
            username='joe', password='x', email='joe@mata.com')
        joe.is_staff = True
        joe.save()
        self.client.login(username='joe', password='x')
        response = self.client.get('/admin/cmsroles/usersetup/')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(any('/admin/?next=/admin/cmsroles/usersetup/' in value
                            for header, value in response.items()))

    def test_403_for_siteadmins_with_no_site(self):
        joe = User.objects.create_user(
            username='joe', password='x', email='joe@mata.com')
        joe.is_staff = True
        joe.user_permissions.add(get_site_admin_required_permission())
        joe.save()
        self.client.login(username='joe', password='x')
        response = self.client.get('/admin/cmsroles/usersetup/')
        self.assertEqual(response.status_code, 403)


class ObjectInteractionsTests(TestCase, HelpersMixin):
    """Test the way Role objects iteract with sites,
    auto generated groups and global page permissions
    """

    def test_global_page_permission_implicitly_created(self):
        site_admin_group = self._create_site_admin_group()
        site_admin = Role.objects.create(
            name='site admin', group=site_admin_group,
            is_site_wide=True)
        global_page_perms = GlobalPagePermission.objects.all()
        # a global page permissions obj implicitly got created on role creation
        # for the default example.com site
        self.assertEqual(len(global_page_perms), 1)

        # when a new site is being added, a global page permisison obj specific
        # for that site must be created for all existing roles
        Site.objects.create(name='new.site.com', domain='new.site.com')
        global_page_perms = GlobalPagePermission.objects.all()
        self.assertEqual(len(global_page_perms), 2)

        for global_perm in global_page_perms:
            site_specific_group = global_perm.group
            self.assertEqual(set(site_specific_group.permissions.all()),
                             set(site_admin_group.permissions.all()))

    def test_assign_user_to_non_site_wide_role(self):
        writer_role = self._create_non_site_wide_role()
        foo_site = self._create_site_with_page('foo.site.com')
        user = User.objects.create(username='gigi', is_staff=True)
        master_page = Page.objects.get(
            title_set__title='master',
            site=foo_site)
        writer_role.grant_to_user(user, foo_site, [master_page])

        page_perms = PagePermission.objects.filter(user=user)
        self.assertEqual(len(page_perms), 1)
        users = writer_role.users(foo_site)
        self.assertItemsEqual([u.pk for u in users], [user.pk])

    def test_switch_role_form_non_wide_to_site_wide(self):
        writer_role = self._create_non_site_wide_role()
        foo_site = self._create_site_with_page('foo.site.com')
        user = User.objects.create(username='gigi', is_staff=True)
        master_page = Page.objects.get(
            title_set__title='master',
            site=foo_site)
        writer_role.grant_to_user(user, foo_site, [master_page])

        writer_role.is_site_wide = True
        writer_role.save()
        self.assertFalse(writer_role.derived_page_permissions.exists())
        self.assertTrue(writer_role.derived_global_permissions.exists())
        users = writer_role.users(foo_site)
        self.assertItemsEqual([u.pk for u in users], [user.pk])
        self.assertTrue(writer_role.derived_global_permissions.filter(group__user=user).exists())

    def test_switch_role_form_site_wide_to_non_wide(self):
        base_site_admin_group = self._create_site_admin_group()
        admin_role = Role.objects.create(
            name='site admin', group=base_site_admin_group,
            is_site_wide=True)
        foo_site = self._create_site_with_page('foo.site.com')
        user = User.objects.create(username='gigi', is_staff=True)
        admin_role.grant_to_user(user, foo_site)

        admin_role.is_site_wide = False
        admin_role.save()
        self.assertTrue(admin_role.derived_page_permissions.exists())
        self.assertFalse(admin_role.derived_global_permissions.exists())
        users = admin_role.users(foo_site)
        self.assertItemsEqual([u.pk for u in users], [user.pk])
        self.assertTrue(admin_role.derived_page_permissions.filter(user=user).exists())

    def test_cant_create_two_roles_based_on_the_same_group(self):
        site_admin_group = self._create_site_admin_group()
        Role.objects.create(
            name='site admin', group=site_admin_group,
            is_site_wide=True)
        with self.assertRaises(ValidationError):
            role = Role(name='site admin', group=site_admin_group)
            role.full_clean()

    def test_user_role_site_assignments(self):
        self._create_simple_setup()
        developer_role = Role.objects.get(name='developer')
        all_developers = developer_role.all_users()
        self.assertSetEqual(set(u.username for u in all_developers), set(['george', 'robin']))
        editor_role = Role.objects.get(name='editor')
        bar_site = Site.objects.get(name='bar.site.com')
        bar_editors = editor_role.users(bar_site)
        self.assertSetEqual(set(u.username for u in bar_editors), set(['criss', 'vasile']))

    def test_role_deletion(self):
        self._create_simple_setup()
        group_count = Group.objects.count()
        site_count = Site.objects.count()
        developer_role = Role.objects.get(name='developer')
        developer_role.delete()
        after_deletion_group_count = Group.objects.count()
        # check that the groups that were implicitly
        # created for each site also got deleted
        self.assertEqual(after_deletion_group_count, group_count - site_count)

    def _setup_site_deletion(self, site_name):
        site = Site.objects.create(name=site_name, domain=site_name)
        base_site_admin_group = self._create_site_admin_group()
        admin_role = Role.objects.create(
            name='site admin', group=base_site_admin_group,
            is_site_wide=True)
        return site, admin_role

    def test_site_deletion_no_roles(self):
        # site delete must work even if there are no roles
        Site.objects.create(
            name='foo.site.com', domain='foo.site.com').delete()

    def test_site_deletion_with_roles(self):
        foo_site, role = self._setup_site_deletion('foo.site.com')
        generated_group = role.get_site_specific_group(foo_site)
        foo_site.delete()
        with self.assertRaises(GlobalPagePermission.DoesNotExist):
            role.get_site_specific_group(foo_site)
        with self.assertRaises(Group.DoesNotExist):
            Group.objects.get(id=generated_group.id)

    def test_site_deletion_with_deleted_site_specific_group(self):
        foo_site, role = self._setup_site_deletion('foo.site.com')
        role.get_site_specific_group(foo_site).delete()
        foo_site.delete()

    def test_site_deletion_with_deleted_site_specific_permission(self):
        foo_site, role = self._setup_site_deletion('foo.site.com')
        role.derived_global_permissions.filter(sites=foo_site).update(group=None)
        Site.objects.get(id=foo_site.id).delete()

    def test_generated_group_names(self):
        foo_site = Site.objects.create(name='foo.site.com', domain='foo.site.com')
        bar_site = Site.objects.create(name='bar.site.com', domain='bar.site.com')
        base_site_admin_group = self._create_site_admin_group()
        admin_role = Role.objects.create(name='site admin', group=base_site_admin_group,
                                         is_site_wide=True)
        generated_group = admin_role.get_site_specific_group(foo_site)
        self.assertEqual(generated_group.name, Role.group_name_pattern % {
                'role_name': admin_role.name,
                'site_domain': foo_site.domain})
        generated_group = admin_role.get_site_specific_group(bar_site)
        self.assertEqual(generated_group.name, Role.group_name_pattern % {
                'role_name': admin_role.name,
                'site_domain': bar_site.domain})

    def test_generated_group_names_on_role_name_change(self):
        foo_site = Site.objects.create(name='foo.site.com', domain='foo.site.com')
        base_site_admin_group = self._create_site_admin_group()
        admin_role = Role.objects.create(name='site admin', group=base_site_admin_group,
                                         is_site_wide=True)
        generated_group = admin_role.get_site_specific_group(foo_site)
        self.assertEqual(generated_group.name, Role.group_name_pattern % {
                'role_name': admin_role.name,
                'site_domain': foo_site.domain})
        admin_role.name = 'new site admin'
        admin_role.save()
        # re-fetch the generated group
        generated_group = admin_role.get_site_specific_group(foo_site)
        # and test that the generated group name is still in sync with the role name
        self.assertEqual(generated_group.name, Role.group_name_pattern % {
                'role_name': admin_role.name,
                'site_domain': foo_site.domain})

    def test_generated_group_names_on_site_domain_change(self):
        foo_site = Site.objects.create(name='foo.site.com', domain='foo.site.com')
        base_site_admin_group = self._create_site_admin_group()
        admin_role = Role.objects.create(name='site admin', group=base_site_admin_group,
                                         is_site_wide=True)
        generated_group = admin_role.get_site_specific_group(foo_site)
        self.assertEqual(generated_group.name, Role.group_name_pattern % {
                'role_name': admin_role.name,
                'site_domain': foo_site.domain})
        foo_site.domain = 'zanewfoo.com'
        foo_site.save()
        # re-fetch the generated group
        generated_group = admin_role.get_site_specific_group(foo_site)
        # and test that the generated group name is still in sync with the site domain
        self.assertEqual(generated_group.name, Role.group_name_pattern % {
                'role_name': admin_role.name,
                'site_domain': foo_site.domain})

    def test_site_group_perms_change_on_role_group_change(self):
        foo_site = Site.objects.create(
            name='foo.site.com', domain='foo.site.com')
        g1 = Group.objects.create(name='g1')
        g1.permissions = Permission.objects.filter(
            content_type__model='page')
        g2 = Group.objects.create(name='g2')
        g2.permissions = Permission.objects.filter(
            content_type__model='user')
        role = Role.objects.create(name='editor', group=g1)
        self.assertItemsEqual(
            role.group.permissions.values_list('id', flat=True),
            g1.permissions.values_list('id', flat=True))
        role.group = g2
        role.save()
        self.assertItemsEqual(
            Role.objects.get(
                id=role.id).group.permissions.values_list('id', flat=True),
            g2.permissions.values_list('id', flat=True))

    def test_changes_in_role_reflected_in_global_perms(self):
        self._create_simple_setup()
        developer_role = Role.objects.get(name='developer')
        can_add = developer_role.can_add
        for gp in developer_role.derived_global_permissions.all():
            self.assertEqual(gp.can_add, developer_role.can_add)
        developer_role.can_add = not can_add
        developer_role.save()
        for gp in developer_role.derived_global_permissions.all():
            self.assertEqual(gp.can_add, developer_role.can_add)

    def test_changes_in_role_relected_in_page_perms(self):
        writer_role = self._create_non_site_wide_role()
        foo_site = self._create_site_with_page('foo.site.com')
        user = User.objects.create(username='gigi', is_staff=True)
        master_page = Page.objects.get(
            title_set__title='master',
            site=foo_site)
        writer_role.grant_to_user(user, foo_site, [master_page])

        self.assertEqual(writer_role.derived_page_permissions.count(), 1)
        for page_perm in writer_role.derived_page_permissions.all():
            self.assertFalse(page_perm.can_add)
        writer_role.can_add = True
        writer_role.save()
        for page_perm in writer_role.derived_page_permissions.all():
            self.assertTrue(page_perm.can_add)

    def test_changes_in_base_group_reflected_in_generated_ones(self):

        def check_permissions(role, permission_set):
            for gp in role.derived_global_permissions.all():
                self.assertSetEqual(
                    set([perm.pk for perm in gp.group.permissions.all()]),
                    permission_set)

        self._create_simple_setup()
        site_admin_base_group = Group.objects.get(name='site_admin')
        perms = site_admin_base_group.permissions.all()
        self.assertTrue(len(perms) > 0)
        admin_role = Role.objects.get(name='site admin')
        check_permissions(admin_role, set(p.pk for p in perms))
        # remove all permissions
        site_admin_base_group.permissions = []
        site_admin_base_group = Group.objects.get(pk=site_admin_base_group.pk)
        self.assertEqual(list(site_admin_base_group.permissions.all()), [])
        admin_role = Role.objects.get(pk=admin_role.pk)
        check_permissions(admin_role, set())
        #and set them back again
        site_admin_base_group.permissions = perms
        self.assertTrue(len(perms) > 0)
        admin_role = Role.objects.get(name='site admin')
        check_permissions(admin_role, set(p.pk for p in perms))

    def test_delete_group(self):
        # we should have a site by default
        self.assertEqual(Site.objects.count(), 1)
        base_site_admin_group = self._create_site_admin_group()
        Role.objects.create(name='site admin', group=base_site_admin_group,
                                         is_site_wide=True)
        # we have two groups: base_site_admin_group and an auto generated
        # one for the default site
        self.assertEqual(Group.objects.count(), 2)
        base_site_admin_group.delete()
        # the auto generated one should also be deleted
        self.assertEqual(Group.objects.count(), 0)

    def test_ungrant_non_site_wide_role(self):
        foo_site = self._create_site_with_page('foo.site.com')
        bar_site = self._create_site_with_page('bar.site.com')
        writer_role = self._create_non_site_wide_role()
        user = User.objects.create(username='gigi', is_staff=True)
        master_foo = Page.objects.get(title_set__title='master', site=foo_site)
        master_bar = Page.objects.get(title_set__title='master', site=bar_site)
        writer_role.grant_to_user(user, foo_site, [master_foo])
        writer_role.grant_to_user(user, bar_site, [master_bar])

        users = writer_role.users(foo_site)
        self.assertItemsEqual([u.pk for u in users], [user.pk])
        users = writer_role.users(bar_site)
        self.assertItemsEqual([u.pk for u in users], [user.pk])

        writer_role.ungrant_from_user(user, foo_site)

        users = writer_role.users(foo_site)
        # no longer assigned to foo
        self.assertItemsEqual([u.pk for u in users], [])
        users = writer_role.users(bar_site)
        # but is still assigned to bar
        self.assertItemsEqual([u.pk for u in users], [user.pk])

    def test_user_belonging_to_more_sites(self):
        """This tests proper functioning of the unassignment
        of a role in the scenario:

        * user bob has writer_role on both foo_site and bar_site
        * user bob has a custom built PagePermssion (not managed
          through the writer_role)
          """
        self._create_simple_setup()
        foo_site = Site.objects.get(domain='foo.site.com')
        bar_site = Site.objects.get(domain='bar.site.com')
        writer_role = Role.objects.get(name='writer')
        bob = User.objects.get(username='bob')
        foo_master_page = Page.objects.get(
            title_set__title='master',
            site=foo_site)
        writer_role.grant_to_user(bob, foo_site, [foo_master_page])
        news_page = Page.objects.get(
            title_set__title='news',
            parent=foo_master_page)
        PagePermission.objects.create(user=bob, page=news_page)
        writer_role.ungrant_from_user(bob, foo_site)
        writer_users = writer_role.users(foo_site)
        self.assertNotIn(bob, writer_users)
        writer_users = writer_role.users(bar_site)
        self.assertIn(bob, writer_users)


class RoleValidationTests(TestCase, HelpersMixin):

    def test_role_validation_two_roles_same_group(self):
        Site.objects.create(name='foo.site.com', domain='foo.site.com')
        base_site_admin_group = self._create_site_admin_group()
        Role.objects.create(name='site admin 1', group=base_site_admin_group)
        role_from_same_group = Role(name='site admin 2', group=base_site_admin_group)
        with self.assertRaises(ValidationError):
            role_from_same_group.clean()

    def test_role_validation_role_from_derived_group(self):
        Site.objects.create(name='foo.site.com', domain='foo.site.com')
        base_site_admin_group = self._create_site_admin_group()
        role = Role.objects.create(name='site admin 1', group=base_site_admin_group,
                                   is_site_wide=True)
        # there should be at least one derived group for
        # the foo.site.com created above
        derived_group = role.derived_global_permissions.all()[0].group
        role_from_derived_group = Role(name='site admin 2', group=derived_group)
        with self.assertRaises(ValidationError):
            role_from_derived_group.clean()


class ViewsTests(TestCase, HelpersMixin):

    def setUp(self):
        User.objects.create_superuser(
            username='root', password='root',
            email='root@roto.com')

    def _get_foo_site_objs(self):
        foo_site = Site.objects.get(name='foo.site.com', domain='foo.site.com')
        joe = User.objects.get(username='joe')
        admin = Role.objects.get(name='site admin')
        george = User.objects.get(username='george')
        developer = Role.objects.get(name='developer')
        robin = User.objects.get(username='robin')
        editor = Role.objects.get(name='editor')
        return foo_site, joe, admin, george, developer, robin, editor

    def test_change_roles(self):
        self._create_simple_setup()
        # users assigned to foo.site.com:
        # joe: site admin, george: developer, robin: editor
        foo_site, joe, _, george, developer, robin, editor = self._get_foo_site_objs()
        self.client.login(username='root', password='root')
        response = self.client.post('/admin/cmsroles/usersetup/?site=%s' % foo_site.pk, {
                # management form
                u'user-roles-MAX_NUM_FORMS': [u''],
                u'user-roles-TOTAL_FORMS': [u'3'],
                u'user-roles-INITIAL_FORMS': [u'3'],
                # change joe to a developer
                u'user-roles-0-user': [unicode(joe.pk)],
                u'user-roles-0-role': [unicode(developer.pk)],
                # george to an editor
                u'user-roles-1-user': [unicode(george.pk)],
                u'user-roles-1-role': [unicode(editor.pk)],
                # robin stays the same
                u'user-roles-2-user': [unicode(robin.pk)],
                u'user-roles-2-role': [unicode(editor.pk)],
                u'next': [u'continue']}
                )
        self.assertEqual(response.status_code, 302)
        users_to_roles = get_site_users(foo_site)
        user_pks_to_role_pks = dict((u.pk, r.pk) for u, r in users_to_roles.iteritems())
        self.assertEqual(len(user_pks_to_role_pks), 3)
        self.assertEqual(user_pks_to_role_pks[joe.pk], developer.pk)
        self.assertEqual(user_pks_to_role_pks[george.pk], editor.pk)
        self.assertEqual(user_pks_to_role_pks[robin.pk], editor.pk)

    def test_unassign_user(self):
        self._create_simple_setup()
        # users assigned to foo.site.com:
        # joe: site admin, george: developer, robin: editor
        foo_site, joe, admin, george, developer, _, _ = self._get_foo_site_objs()
        self.client.login(username='root', password='root')
        response = self.client.post('/admin/cmsroles/usersetup/?site=%s' % foo_site.pk, {
                # management form
                u'user-roles-MAX_NUM_FORMS': [u''],
                u'user-roles-TOTAL_FORMS': [u'2'],
                u'user-roles-INITIAL_FORMS': [u'2'],
                # joe remains an admin
                u'user-roles-0-user': [unicode(joe.pk)],
                u'user-roles-0-role': [unicode(admin.pk)],
                # george remains a developer
                u'user-roles-1-user': [unicode(george.pk)],
                u'user-roles-1-role': [unicode(developer.pk)],
                # but robin gets removed !!
                u'next': [u'continue']}
                )
        self.assertEqual(response.status_code, 302)
        users_to_roles = get_site_users(foo_site)
        user_pks_to_role_pks = dict((u.pk, r.pk) for u, r in users_to_roles.iteritems())
        self.assertEqual(len(user_pks_to_role_pks), 2)
        self.assertEqual(user_pks_to_role_pks[joe.pk], admin.pk)
        self.assertEqual(user_pks_to_role_pks[george.pk], developer.pk)

    def test_change_user_pages(self):
        self._create_simple_setup()
        # users assigned to foo.site.com:
        # joe: site admin, george: developer, robin: editor
        foo_site, joe, _, george, developer, robin, editor = self._get_foo_site_objs()
        master_page = self._create_pages(foo_site)
        news_page = Page.objects.get(title_set__title='news', parent=master_page)
        writer = Role.objects.get(name='writer')
        self.client.login(username='root', password='root')
        response = self.client.post('/admin/cmsroles/usersetup/?site=%s' % foo_site.pk, {
                # management form
                u'user-roles-MAX_NUM_FORMS': [u''],
                u'user-roles-TOTAL_FORMS': [u'1'],
                u'user-roles-INITIAL_FORMS': [u'1'],
                # make jow a writer
                u'user-roles-0-user': [unicode(joe.pk)],
                u'user-roles-0-role': [unicode(writer.pk)],
                (u'user-%d-MAX_NUM_FORMS' % joe.pk): u'',
                (u'user-%d-TOTAL_FORMS' % joe.pk): u'1',
                (u'user-%d-INITIAL_FORMS' % joe.pk): u'1',
                # and give him access to the news page
                (u'user-%d-0-page' % joe.pk): u'%d' % news_page.pk,
                u'next': [u'continue']}
                )
        self.assertEqual(response.status_code, 302)
        users_to_roles = get_site_users(foo_site)
        user_pks_to_role_pks = dict((u.pk, r.pk) for u, r in users_to_roles.iteritems())
        self.assertEqual(len(user_pks_to_role_pks), 1)
        self.assertEqual(user_pks_to_role_pks[joe.pk], writer.pk)
        page_perms = writer.get_user_page_perms(joe, foo_site)
        self.assertEqual(len(page_perms), 1)
        perm_to_news = page_perms[0]
        self.assertEqual(perm_to_news.page, news_page)

    def test_change_user_pages_no_pages_in_formset(self):
        self._create_simple_setup()
        # users assigned to foo.site.com:
        # joe: site admin, george: developer, robin: editor
        foo_site, joe, _, george, developer, robin, editor = self._get_foo_site_objs()
        master_page = self._create_pages(foo_site)
        news_page = Page.objects.get(title_set__title='news', parent=master_page)
        writer = Role.objects.get(name='writer')
        self.client.login(username='root', password='root')
        response = self.client.post('/admin/cmsroles/usersetup/?site=%s' % foo_site.pk, {
                # management form
                u'user-roles-MAX_NUM_FORMS': [u''],
                u'user-roles-TOTAL_FORMS': [u'1'],
                u'user-roles-INITIAL_FORMS': [u'1'],
                # make jow a writer
                u'user-roles-0-user': [unicode(joe.pk)],
                u'user-roles-0-role': [unicode(writer.pk)],
                (u'user-%d-MAX_NUM_FORMS' % joe.pk): u'',
                (u'user-%d-TOTAL_FORMS' % joe.pk): u'0',
                (u'user-%d-INITIAL_FORMS' % joe.pk): u'0',
                # we don't give him any page
                u'next': [u'continue']}
                )
        # we don't get a redirect => POST submition failed
        # we do get 200, but that's a page containing the form errors
        self.assertEqual(response.status_code, 200)
        formset_with_errors = response.context['page_formsets'][unicode(joe.pk)]
        self.assertEqual(len(formset_with_errors.non_form_errors()), 1)
        self.assertEqual(formset_with_errors.non_form_errors()[0],
                         u'At least a page needs to be selected')

    def test_change_user_pages_no_formset_given(self):
        self._create_simple_setup()
        # users assigned to foo.site.com:
        # joe: site admin, george: developer, robin: editor
        foo_site, joe, _, george, developer, robin, editor = self._get_foo_site_objs()
        writer = Role.objects.get(name='writer')
        self.client.login(username='root', password='root')
        with self.assertRaises(ValidationError):
            self.client.post('/admin/cmsroles/usersetup/?site=%s' % foo_site.pk, {
                    # management form
                    u'user-roles-MAX_NUM_FORMS': [u''],
                    u'user-roles-TOTAL_FORMS': [u'1'],
                    u'user-roles-INITIAL_FORMS': [u'1'],
                    #  developer
                    u'user-roles-0-user': [unicode(joe.pk)],
                    u'user-roles-0-role': [unicode(writer.pk)],
                    u'next': [u'continue']}
                    )

    def test_assign_new_user(self):
        self._create_simple_setup()
        # users assigned to foo.site.com:
        # joe: site admin, george: developer, robin: editor
        foo_site, joe, admin, george, developer, robin, editor = self._get_foo_site_objs()
        criss = User.objects.get(username='criss')
        self.client.login(username='root', password='root')
        response = self.client.post('/admin/cmsroles/usersetup/?site=%s' % foo_site.pk, {
                # management form
                u'user-roles-MAX_NUM_FORMS': [u''],
                u'user-roles-TOTAL_FORMS': [u'4'],
                u'user-roles-INITIAL_FORMS': [u'4'],
                # joe remains an admin
                u'user-roles-0-user': [unicode(joe.pk)],
                u'user-roles-0-role': [unicode(admin.pk)],
                # george remains a developer
                u'user-roles-1-user': [unicode(george.pk)],
                u'user-roles-1-role': [unicode(developer.pk)],
                # robin remains an editor
                u'user-roles-2-user': [unicode(robin.pk)],
                u'user-roles-2-role': [unicode(editor.pk)],
                # but we also add criss to foo_site
                u'user-roles-3-user': [unicode(criss.pk)],
                u'user-roles-3-role': [unicode(admin.pk)],
                u'next': [u'continue']}
                )
        self.assertEqual(response.status_code, 302)
        users_to_roles = get_site_users(foo_site)
        user_pks_to_role_pks = dict((u.pk, r.pk) for u, r in users_to_roles.iteritems())
        self.assertEqual(len(user_pks_to_role_pks), 4)
        self.assertEqual(user_pks_to_role_pks[joe.pk], admin.pk)
        self.assertEqual(user_pks_to_role_pks[george.pk], developer.pk)
        self.assertEqual(user_pks_to_role_pks[robin.pk], editor.pk)
        self.assertEqual(user_pks_to_role_pks[criss.pk], admin.pk)

    def test_get_page_formset(self):
        self._create_simple_setup()
        bar_site = Site.objects.get(domain='bar.site.com')
        bob = User.objects.get(username='bob')
        writer = Role.objects.get(name='writer')
        self.client.login(username='root', password='root')
        response = self.client.get(
            '/admin/cmsroles/get_page_formset/?site=%s' % bar_site.pk, {
                u'user': bob.pk,
                u'role': writer.pk,
                u'site': bar_site.pk}
            )
        content = simplejson.loads(response.content)
        page_formset = content[u'page_formset']
        # this assert is a bit ugly, but since the formset is already
        # rendered, I don't see any other way to verify that
        # the master page (wich bob has access to)
        # is in the returned formset
        self.assertTrue('selected="selected"> master' in page_formset)

    def test_no_duplicate_groups_in_the_group_admin(self):
        site_admin_group = self._create_site_admin_group()
        Role.objects.create(
            name='site admin', group=site_admin_group,
            is_site_wide=True)
        GlobalPagePermission.objects.create(
            group=site_admin_group)
        GlobalPagePermission.objects.create(
            group=site_admin_group)
        self.client.login(username='root', password='root')
        response = self.client.get('/admin/auth/group/')
        displayed_objects = response.context['cl'].result_list
        # before 'distinct()' was added, ExtendedGroupAdmin.get_filtered_queryset
        # used to return the same group object multiple times
        self.assertListEqual(list(displayed_objects), [site_admin_group])


class ManagePagePermissionsCommandTests(TestCase, HelpersMixin):

    def test_site_already_writer_on(self):
        self._create_simple_setup()
        bar_site = Site.objects.get(domain='bar.site.com')
        writer_role = Role.objects.get(name='writer')
        bob = User.objects.get(username='bob')
        bar_news = Page.objects.get(title_set__title='news', site=bar_site)
        unmanaged_perm = PagePermission.objects.create(user=bob, page=bar_news)
        call_command('manage_page_permissions', role='writer')
        self.assertIn(unmanaged_perm, writer_role.derived_page_permissions.all())

    def test_site_not_writer_on(self):
        self._create_simple_setup()
        foo_site = Site.objects.get(domain='foo.site.com')
        writer_role = Role.objects.get(name='writer')
        bob = User.objects.get(username='bob')
        foo_news = Page.objects.get(title_set__title='news', site=foo_site)
        unmanaged_perm = PagePermission.objects.create(user=bob, page=foo_news)
        call_command('manage_page_permissions', role='writer')
        self.assertIn(unmanaged_perm, writer_role.derived_page_permissions.all())
        self.assertIn(bob, writer_role.users(foo_site))

    def test_on_site_already_having_other_role(self):
        self._create_simple_setup()
        foo_site = Site.objects.get(domain='foo.site.com')
        bob = User.objects.get(username='bob')
        writer_role = Role.objects.get(name='writer')
        admin_role = Role.objects.get(name='site admin')
        admin_role.grant_to_user(bob, foo_site)
        foo_news = Page.objects.get(title_set__title='news', site=foo_site)
        unmanaged_perm = PagePermission.objects.create(user=bob, page=foo_news)
        command = manage_page_permissions.Command()
        command.execute(role='writer')
        self.assertEqual(len(command.errors), 1)
        self.assertNotIn(bob, writer_role.users(foo_site))
        self.assertNotIn(unmanaged_perm, writer_role.derived_page_permissions.all())


class InvalidSiteParamTests(TestCase):
    def setUp(self):
        User.objects.create_superuser(
            username='gigi', password='gigi', email='gigi@roto.com')
        self.client.login(username='gigi', password='gigi')

    def test_get_user_sites(self):
        gigi = User.objects.get(username="gigi")
        self.assertRaises(Http404, _get_user_sites, gigi, "1)")

    def test_404_on_invalid_site(self):
        response = self.client.get("/admin/cmsroles/usersetup/?site=1?")
        self.assertEqual(response.status_code, 404)
