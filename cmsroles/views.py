from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import transaction
from django import forms
from django.forms.formsets import formset_factory, BaseFormSet
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext, loader, Context
from django.utils.encoding import smart_unicode
from django.utils import simplejson

from cms.models.pagemodel import Page

from mptt.forms import TreeNodeChoiceField

from cmsroles.siteadmin import get_administered_sites, \
    get_site_users, is_site_admin
from cmsroles.models import Role


class UserChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        if obj.first_name and obj.last_name and obj.email:
            return u'%s %s (%s)' % (obj.first_name, obj.last_name, obj.email)
        elif obj.email:
            return obj.email
        else:
            return smart_unicode(obj)


class UserForm(forms.Form):
    user = UserChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False)
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        required=False)

    def clean(self):
        cleaned_data = super(UserForm, self).clean()
        user = cleaned_data.get('user', None)
        role = cleaned_data.get('role', None)
        if (user is None) != (role is None):
            raise forms.ValidationError('Both user and role need to be set')
        return cleaned_data


class BaseUserFormSet(BaseFormSet):

    def clean(self):
        if any(self.errors):
            return
        users = set()
        for form in self.forms:
            user = form.cleaned_data.get('user', None)
            if user is None:
                continue
            if user in users:
                raise forms.ValidationError(
                    "User %s has multiple roles. "
                    "A User can't have multiple roles in the same site"
                    % user.username)
            users.add(user)

class BasePageFormSet(BaseFormSet):

    def clean(self):
        if any(self.errors):
            return
        errors = []
        pages = set()
        for form in self.forms:
            page = form.cleaned_data.get('page', None)
            if page in pages:
                errors.append(u"Page '%s' is added multiple times" % page)
            if page is not None:
                pages.add(page)
        if len(pages) == 0:
            errors.append(u"At least a page needs to be selected")
        raise forms.ValidationError(errors)


def _get_user_sites(user, site_pk):
    administered_sites = get_administered_sites(user)
    if not administered_sites:
        raise PermissionDenied()

    if not site_pk:
        return (administered_sites[0], administered_sites)

    try:
        site_pk = int(site_pk)
    except ValueError:
        raise Http404()

    if all(site_pk != s.pk for s in administered_sites):
        raise PermissionDenied()
    else:
        return (next((s for s in administered_sites if site_pk == s.pk),
                     administered_sites[0]),
                administered_sites)


def _get_site_pk(request):
    """Get's the current site's pk by first checking for a
    GET request parameter. If that's unavailable it uses
    the current request's Host header
    """
    site_pk = request.GET.get('site', None)
    if site_pk is not None:
        return site_pk

    host = request.META.get('HTTP_HOST', None)
    if host is not None:
        try:
            site_pk = Site.objects.get(domain=host).pk
        except Site.DoesNotExist:
            pass
    return site_pk


def _update_site_users(request, site, assigned_users, submitted_users, user_pages):
    newly_assigned_users = {}
    existing_users = {}
    for user, role in submitted_users.iteritems():
        if user not in assigned_users:
            newly_assigned_users[user] = role
        else:
            existing_users[user] = role

    unassigned_users = dict(
        (user, role) for user, role in assigned_users.iteritems()
        if user not in existing_users.keys())

    for user, role in unassigned_users.iteritems():
        role.ungrant_from_user(user, site)
    for user, role in newly_assigned_users.iteritems():
        pages = user_pages.get(user, None)
        if not role.is_site_wide and pages is None:
            # this is very unlikely but can happen if someone changes the role
            # between the moment user setup page is rendered and the moment
            # the forms are submitted
            messages.error(
                request, "Role %s got changed and is no longer site wide. "
                "User %s didn't get the role because "
                "no pages were submitted. Try again" % (user, role))
        else:
            role.grant_to_user(user, site, pages)
    for user, new_role in existing_users.iteritems():
        previous_role = assigned_users[user]
        pages = user_pages.get(user, None)
        if previous_role != new_role or pages is not None:
            previous_role.ungrant_from_user(user, site)
            new_role.grant_to_user(user, site, pages)


def _get_user_pages(page_formset):
    pages = []
    for page_form in page_formset:
        page = page_form.cleaned_data.get('page', None)
        if page is not None:
            pages.append(page)
    return pages


def _get_redirect(request, site_pk):
    next_action = request.POST['next']
    if next_action == u'continue':
        if site_pk is not None:
            next_url = '%s?site=%s' % (reverse(user_setup), site_pk)
        else:
            next_url = reverse(user_setup)
        return HttpResponseRedirect(next_url)
    else:
        return HttpResponseRedirect('/admin/')

def _get_page_form_class(current_site):

    class PageForm(forms.Form):
        page = TreeNodeChoiceField(
            queryset=Page.objects.filter(site=current_site),
            required=False)

    return PageForm


@user_passes_test(is_site_admin, login_url='/admin/')
def get_page_formset(request):
    """Returns the page formset for a given user. This is meant to
    be called via AJAX.

    This is a kind of 'lazy loading' for page formsets. The page 
    formset generation logic isn't added in the user_setup view
    because it would take to long to render all of the page formsets
    upfront.
    """
    site_pk = _get_site_pk(request)
    # this is requred for making sure the pages formset is properly built
    assert site_pk is not None
    current_site, administered_sites = _get_user_sites(request.user, site_pk)
    PageFormSet = formset_factory(
        _get_page_form_class(current_site),
        formset=BasePageFormSet, extra=1)
    user_pk = request.GET.get('user')
    role_pk = request.GET.get('role')
    role = Role.objects.get(pk=role_pk)
    user = User.objects.get(pk=user_pk)
    if role.is_site_wide:
        return HttpResponse(simplejson.dumps({
                    'success': False,
                    'error_msg': 'This role was changed to being site '\
                        'wide in the meanwhile. The assign pages link is '\
                        'obsolete'}),
                            content_type="application/json")
    page_perms = role.get_user_page_perms(user, current_site)
    page_formset = PageFormSet(
        initial=[{'page': page_perm.page} for page_perm in page_perms],
        prefix='user-%d' % user.pk)
    rendered_formset = loader.get_template(
        'admin/cmsroles/page_formset.html').render(
        Context({'page_formset': page_formset}))
    response = {'page_formset': rendered_formset,
                'success': True}
    return HttpResponse(simplejson.dumps(response),
                        content_type="application/json")


def _formset_available(request, user):
    return 'user-%d-INITIAL_FORMS' % user.pk in request.POST.keys()


def _get_page_formset_prefix(user):
    return 'user-%d' % user.pk


@user_passes_test(is_site_admin, login_url='/admin/')
@transaction.commit_on_success
def user_setup(request):
    site_pk = _get_site_pk(request)
    current_site, administered_sites = _get_user_sites(request.user, site_pk)
    UserFormSet = formset_factory(UserForm, formset=BaseUserFormSet, extra=1)
    assigned_users = get_site_users(current_site)
    PageFormSet = formset_factory(
        _get_page_form_class(current_site),
        formset=BasePageFormSet, extra=1)
    page_formsets = {}
    if request.method == 'POST':
        user_formset = UserFormSet(request.POST, request.FILES,
                                   prefix='user-roles')
        user_pages = {}
        if user_formset.is_valid():
            submitted_users = {}
            page_formsets_have_errors = False
            for user_form in user_formset.forms:
                user = user_form.cleaned_data.get('user', None)
                role = user_form.cleaned_data.get('role', None)
                if user is None and role is None:
                    continue
                submitted_users[user] = role
                if not role.is_site_wide and _formset_available(request, user):
                    page_formset = PageFormSet(
                        request.POST, request.FILES,
                        prefix=_get_page_formset_prefix(user))
                    if page_formset.is_valid():
                        user_pages[user] = _get_user_pages(page_formset)
                    else:
                        page_formsets[unicode(user.pk)] = page_formset
                        page_formsets_have_errors = True
            if not page_formsets_have_errors:
                _update_site_users(request, current_site, assigned_users,
                                   submitted_users, user_pages)
                return _get_redirect(request, site_pk)

    else:
        initial_data = [
            {'user': user, 'role': role, 'current_site': current_site}
            for user, role in assigned_users.iteritems()]
        user_formset = UserFormSet(initial=initial_data, prefix='user-roles')

    all_roles = Role.objects.all()
    role_pk_to_site_wide = dict((role.pk, role.is_site_wide) for role in all_roles)
    # so that the empty form template doesn't have an 'assign pages' link
    role_pk_to_site_wide[None] = True
    context = {
        'opts': {'app_label': 'cmsroles'},
        'app_label': 'Cmsroles',
        'administered_sites': administered_sites,
        'current_site': current_site,
        'user_formset': user_formset,
        'page_formsets': page_formsets,
        'user': request.user,
        'role_pk_to_site_wide_js': [
            (role.pk, 'true' if role.is_site_wide else 'false')
            for role in all_roles],
        'role_pk_to_site_wide': role_pk_to_site_wide}
    return render_to_response('admin/cmsroles/user_setup.html', context,
                              context_instance=RequestContext(request))
