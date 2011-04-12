import re
import urllib
from datetime import datetime
from django.contrib.auth.forms import AdminPasswordChangeForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.views.decorators.http import require_POST
from corehq.apps.domain.user_registration_backend import register_user
from corehq.apps.domain.user_registration_backend.forms import AdminRegistersUserForm,\
    AdminInvitesUserForm, UserRegistersSelfForm
from corehq.apps.hqwebapp.views import password_change
from corehq.apps.sms.views import get_sms_autocomplete_context
from corehq.apps.domain.models import Domain
from corehq.apps.users.forms import UserForm, CommCareAccountForm
from corehq.apps.users.models import CouchUser, create_hq_user_from_commcare_registration_info, CommCareAccount, CommCareAccount,\
    Invitation
from django.contrib.admin.views.decorators import staff_member_required
from django_digest.decorators import httpdigest
from corehq.apps.groups.models import Group
from corehq.apps.domain.decorators import login_and_domain_required, require_superuser
from corehq.apps.users.util import couch_user_from_django_user
from dimagi.utils.web import render_to_response
from dimagi.utils.couch.database import get_db
from .util import doc_value_wrapper
import calendar
from corehq.apps.reports.schedule.config import SCHEDULABLE_REPORTS
from corehq.apps.reports.models import WeeklyReportNotification,\
    DailyReportNotification, ReportNotification
from django.contrib import messages
from corehq.apps.reports.tasks import send_report


def require_permission_to_edit_user(view_func):
    def _inner(request, domain, couch_user_id, *args, **kwargs):
        if hasattr(request, "couch_user") and (request.user.is_superuser or request.couch_user.is_domain_admin(domain) or request.couch_user._id == couch_user_id):
            return login_and_domain_required(view_func)(request, domain, couch_user_id, *args, **kwargs)
        else:
            raise Http404()
    return _inner

def require_domain_admin(view_func):
    def _inner(request, domain, *args, **kwargs):
        if hasattr(request, "couch_user") and (request.user.is_superuser or request.couch_user.is_domain_admin(domain)):
            return login_and_domain_required(view_func)(request, domain, *args, **kwargs)
        else:
            raise Http404()
    return _inner

def _users_context(request, domain):
    couch_user = request.couch_user
    couch_user.current_domain = domain
    web_users = CouchUser.view("users/web_users_by_domain", key=domain, include_docs=True, reduce=False)
    for web_user in web_users:
        web_user.current_domain = domain
    return {
        'web_users': web_users,
        'domain': domain,
        'couch_user': couch_user,
    }

def _get_user_commcare_account_tuples(domain):
    return get_db().view(
        "users/commcare_accounts_by_domain",
        key=domain,
        include_docs=True,
        # This wrapper returns tuples of (CouchUser, CommCareAccount)
        wrapper=doc_value_wrapper(CouchUser, CommCareAccount)
    )

@login_and_domain_required
def users(request, domain):
    return HttpResponseRedirect(reverse(
        "user_account",
        args=[domain, request.couch_user._id],
    ))

@require_domain_admin
def web_users(request, domain, template="users/web_users.html"):
    context = _users_context(request, domain)
    return render_to_response(request, template, context)

@require_domain_admin
@transaction.commit_on_success
def create_web_user(request, domain, template="users/create_web_user.html"):
    if request.method == "POST":
        form = AdminRegistersUserForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            assert(data['password_1'] == data['password_2'])
            data['password'] = data['password_1']
            del data['password_1']
            del data['password_2']
            new_user = register_user(domain, send_email=True, **data)
            return HttpResponseRedirect(reverse("web_users", args=[domain]))
    else:
        form = AdminRegistersUserForm()
    context = _users_context(request, domain)
    context.update(
        registration_form=form
    )
    return render_to_response(request, template, context)

@transaction.commit_on_success
def accept_invitation(request, domain, invitation_id):
    invitation = Invitation.get(invitation_id)
    assert(invitation.domain == domain)
    if invitation.is_accepted:
        messages.error(request, "Sorry that invitation has already been used up. "
                       "If you feel this is a mistake please ask the inviter for "
                       "another invitation.")
        return HttpResponseRedirect(reverse("homepage"))
    if request.user.is_authenticated():
        # if you are already authenticated, just add the domain to your 
        # list of domains
        couch_user = couch_user_from_django_user(request.user)
        couch_user.add_domain_membership(domain=domain, is_admin=invitation.is_domain_admin)
        couch_user.save()
        invitation.is_accepted = True
        invitation.save()
        messages.success(request, "You have been added to the %s domain" % domain)
        return HttpResponseRedirect(reverse("domain_homepage", args=[domain,]))
    else:
        # if you're not authenticated we need you to fill out your information
        if request.method == "POST":
            form = UserRegistersSelfForm(request.POST)
            if form.is_valid():
                data = form.cleaned_data
                assert(data['password_1'] == data['password_2'])
                data['password'] = data['password_1']
                del data['password_1']
                del data['password_2']
                del data["tos_confirmed"]  
                user = register_user(invitation.domain, send_email=False, 
                                     is_domain_admin=invitation.is_domain_admin, **data)
                messages.success(request, "User account for %s created! You may now login." % data["email"])
                invitation.is_accepted = True
                invitation.save()
                return HttpResponseRedirect(reverse("homepage"))
        else: 
            form = UserRegistersSelfForm(initial={'email': invitation.email})    
        
        return render_to_response(request, "users/accept_invite.html", {"form": form})


@require_domain_admin
def invite_web_user(request, domain, template="users/invite_web_user.html"):
    if request.method == "POST":
        form = AdminInvitesUserForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            # create invitation record
            data["invited_by"] = request.couch_user.get_id
            data["invited_on"] = datetime.utcnow()
            data["domain"] = domain
            invite = Invitation(**data)
            invite.save()
            invite.send_activation_email()
            messages.success(request, "Invitation sent to %s" % invite.email)
            return HttpResponseRedirect(reverse("web_users", args=[domain]))
    else:
        form = AdminInvitesUserForm()
    context = _users_context(request, domain)
    context.update(
        registration_form=form
    )
    return render_to_response(request, template, context)

@require_domain_admin
def commcare_users(request, domain, template="users/commcare_users.html"):
    context = _users_context(request, domain)
    users = _get_user_commcare_account_tuples(domain)
#    for user, account in users:
#        user.current_domain = domain
    context.update({
        'commcare_users': users,
    })
    return render_to_response(request, template, context)

@require_permission_to_edit_user
def account(request, domain, couch_user_id, template="users/account.html"):
    context = _users_context(request, domain)
    couch_user = CouchUser.get(couch_user_id)

    # phone-numbers tab
    if request.method == "POST" and request.POST['form_type'] == "phone-numbers":
        phone_number = request.POST['phone_number']
        if re.match(r'\d+', phone_number):
            couch_user.add_phone_number(phone_number)
            couch_user.save()
            #context['status'] = 'phone number added'
        else:
            context['status'] = "please enter digits only"


    # commcare-accounts tab
    my_commcare_login_ids = set([c.login_id for c in couch_user.commcare_accounts])

    all_commcare_accounts = list(_get_user_commcare_account_tuples(domain))

    other_commcare_accounts = []
    for user, account in all_commcare_accounts:
        # we don't bother showing the duplicate commcare users.
        # these need to be resolved elsewhere.
        if hasattr(account,'is_duplicate') and account.is_duplicate == True:
            continue
        if account.login_id not in my_commcare_login_ids:
            other_commcare_accounts.append((user, account))

    # domain-accounts tab
    if request.user.is_superuser:
        my_domains = [dm.domain for dm in couch_user.web_account.domain_memberships]
        context.update({"user": request.user,
                        "domains": my_domains
                        })
    # scheduled reports tab
    context.update({
        'couch_user': couch_user,
        # for phone-number tab
        'phone_numbers': couch_user.phone_numbers,

        # for commcare-accounts tab
        "other_commcare_accounts": other_commcare_accounts,
    })
    context.update(_handle_user_form(request, domain, couch_user))
    return render_to_response(request, template, context)

@require_permission_to_edit_user
def delete_phone_number(request, domain, couch_user_id):
    """
    phone_number cannot be passed in the url due to special characters
    but it can be passed as %-encoded GET parameters
    """
    if 'phone_number' not in request.GET:
        return Http404('Must include phone number in request.')
    phone_number = urllib.unquote(request.GET['phone_number'])
    user = CouchUser.get(couch_user_id)
    for i in range(0,len(user.phone_numbers)):
        if user.phone_numbers[i] == phone_number:
            del user.phone_numbers[i]
            break
    user.save()
    return HttpResponseRedirect(reverse("user_account", args=(domain, couch_user_id )))

@require_POST
@require_permission_to_edit_user
def link_commcare_account_to_user(request, domain, couch_user_id, commcare_login_id):
    user = CouchUser.get(couch_user_id)
    if 'commcare_couch_user_id' not in request.POST: 
        return Http404("Poorly formed link request")
    user.link_commcare_account(domain, 
                               request.POST['commcare_couch_user_id'], 
                               commcare_login_id)
    return HttpResponseRedirect(reverse("user_account", args=(domain, couch_user_id)))

@require_POST
@require_permission_to_edit_user
def unlink_commcare_account(request, domain, couch_user_id, commcare_user_index):
    user = CouchUser.get(couch_user_id)
    if commcare_user_index:
        user.unlink_commcare_account(domain, commcare_user_index)
        user.save()
    return HttpResponseRedirect(reverse("user_account", args=(domain, couch_user_id )))

#@login_and_domain_required
#def my_domains(request, domain):
#    return HttpResponseRedirect(reverse("domain_accounts", args=(domain, request.couch_user._id)))

@require_superuser
@login_and_domain_required
def domain_accounts(request, domain, couch_user_id, template="users/domain_accounts.html"):
    context = _users_context(request, domain)
    couch_user = CouchUser.get(couch_user_id)
    if request.method == "POST" and 'domain' in request.POST:
        domain = request.POST['domain']
        couch_user.add_domain_membership(domain)
        couch_user.save()
        #context['status'] = 'domain added'
    my_domains = [dm.domain for dm in couch_user.web_account.domain_memberships]
    context['other_domains'] = [d.name for d in Domain.objects.exclude(name__in=my_domains)]
    context.update({"user": request.user,
                    "domains": [dm.domain for dm in couch_user.web_account.domain_memberships],
                    })
    return render_to_response(request, template, context)

@require_POST
@require_superuser
def add_domain_membership(request, domain, couch_user_id, domain_name):
    user = CouchUser.get(couch_user_id)
    if domain_name:
        user.add_domain_membership(domain_name)
        user.save()
    return HttpResponseRedirect(reverse("user_account", args=(domain, couch_user_id)))

@require_POST
@require_superuser
def delete_domain_membership(request, domain, couch_user_id, domain_name):
    user = CouchUser.get(couch_user_id)
    for i in range(0,len(user.web_account.domain_memberships)):
        if user.web_account.domain_memberships[i].domain == domain_name:
            del user.web_account.domain_memberships[i]
            break
    user.save()
    return HttpResponseRedirect(reverse("user_account", args=(domain, couch_user_id )))

# this view can only change the current user's password
@login_and_domain_required
def change_my_password(request, domain, template="users/change_my_password.html"):
    # copied from auth's password_change
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('user_account', args=[domain, request.couch_user._id]))
    else:
        form = PasswordChangeForm(user=request.user)
    context = _users_context(request, domain)
    context.update({
        'form': form,
    })
    return render_to_response(request, template, context)



def _handle_user_form(request, domain, couch_user=None):
    context = {}
    if couch_user:
        create_user = False
    else:
        create_user = True
    can_change_admin_status = \
        (request.user.is_superuser or request.couch_user.is_domain_admin(domain))\
        and request.couch_user._id != couch_user._id
    if request.method == "POST" and request.POST['form_type'] == "basic-info":
        form = UserForm(request.POST)
        if form.is_valid():
            if create_user:
                django_user = User()
                django_user.username = form.cleaned_data['email']
                django_user.save()
                couch_user = couch_user_from_django_user(django_user)
            couch_user.first_name = form.cleaned_data['first_name']
            couch_user.last_name = form.cleaned_data['last_name']
            couch_user.email = form.cleaned_data['email']
            if can_change_admin_status:
                for dm in couch_user.web_account.domain_memberships:
                    if dm.domain == domain:
                        dm.is_admin = form.cleaned_data['is_admin']
                        break
            couch_user.save()
            context['status'] = 'changes saved'
    else:
        form = UserForm()
        if not create_user:
            form.initial['first_name'] = couch_user.first_name
            form.initial['last_name'] = couch_user.last_name
            form.initial['email'] = couch_user.email
            print request.couch_user
            if can_change_admin_status:
                form.initial['is_admin'] = couch_user.is_domain_admin(domain)
            else:
                del form.fields['is_admin']

    context.update({"form": form})
    return context

@httpdigest
@login_and_domain_required
def httpdigest(request, domain):
    return HttpResponse("ok")

@login_and_domain_required
def add_scheduled_report(request, domain, couch_user_id):
    if request.method == "POST":
        report_type = request.POST["report_type"]
        hour = request.POST["hour"]
        day = request.POST["day"]
        if day=="all":
            report = DailyReportNotification()
        else:
            report = WeeklyReportNotification()
            report.day_of_week = int(day)
        report.hours = int(hour)
        report.domain = domain
        report.report_slug = report_type
        report.user_ids = [couch_user_id]
        report.save()
        messages.success(request, "New scheduled report added!")
        return HttpResponseRedirect(reverse("user_account", args=(domain, couch_user_id )))
    
    context = _users_context(request, domain)
    context.update({"hours": [(val, "%s:00" % val) for val in range(24)],
                    "days":  [(val, calendar.day_name[val]) for val in range(7)],
                    "reports": SCHEDULABLE_REPORTS})
    return render_to_response(request, "users/add_scheduled_report.html", context)

@login_and_domain_required
@require_POST
def drop_scheduled_report(request, domain, couch_user_id, report_id):
    rep = ReportNotification.get(report_id)
    try:
        rep.user_ids.remove(couch_user_id)
    except ValueError:
        pass # odd, the user wasn't there in the first place
    if len(rep.user_ids) == 0:
        rep.delete()
    else:
        rep.save()
    messages.success(request, "Scheduled report dropped!")
    return HttpResponseRedirect(reverse("user_account", args=(domain, couch_user_id )))

@login_and_domain_required
@require_POST
def test_scheduled_report(request, domain, couch_user_id, report_id):
    rep = ReportNotification.get(report_id)
    user = CouchUser.get(couch_user_id)
    send_report(rep, user)
    messages.success(request, "Test message sent to %s" % user.default_django_user.email)
    return HttpResponseRedirect(reverse("user_account", args=(domain, couch_user_id )))

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
GROUP VIEWS
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


def _get_groups(domain):
    groups = Group.view("groups/by_domain", key=domain)
    for group in groups:
        name = re.sub(r'[^\w-]', '-', group.name)
        if group.name != name:
            group.name = name
            group.save()
    return groups


@require_domain_admin
def all_groups(request, domain, template="groups/all_groups.html"):
    context = _users_context(request, domain)
    all_groups = _get_groups(domain)
    context.update({
        'domain': domain,
        'all_groups': all_groups
    })
    return render_to_response(request, template, context)

@require_domain_admin
def group_members(request, domain, group_name, template="groups/group_members.html"):
    context = _users_context(request, domain)
    group = Group.view("groups/by_name", key=group_name).one()
    if group is None:
        raise Http404("Group %s does not exist" % group_name)
    members = CouchUser.view("users/by_group", key=[domain, group.name], include_docs=True).all()
    member_ids = set([member._id for member in members])
    all_users = CouchUser.view("users/by_domain", key=domain, include_docs=True, reduce=False).all()
    nonmembers = [user for user in all_users if user._id not in member_ids]

    context.update({"domain": domain,
                    "group": group,
                    "members": members,
                    "nonmembers": nonmembers,
                    })
    return render_to_response(request, template, context)

#@require_domain_admin
#def my_groups(request, domain, template="groups/groups.html"):
#    return group_membership(request, domain, request.couch_user._id, template)

@require_domain_admin
def group_membership(request, domain, couch_user_id, template="groups/groups.html"):
    context = _users_context(request, domain)
    couch_user = CouchUser.get(couch_user_id)
    if request.method == "POST" and 'group' in request.POST:
        group = request.POST['group']
        group.add_user(couch_user)
        group.save()
        #context['status'] = '%s joined group %s' % (couch_user._id, group.name)
    my_groups = Group.view("groups/by_user", key=couch_user_id).all()
    all_groups = Group.view("groups/by_domain", key=domain).all()
    other_groups = []
    for group in all_groups:
        if group.name not in [g.name for g in my_groups]:
            other_groups.append(group)
    #other_groups = [group for group in all_groups if group not in my_groups]
    context.update({"domain": domain,
                    "groups": my_groups, 
                    "other_groups": other_groups,
                    "couch_user":couch_user })
    return render_to_response(request, template, context)

@require_domain_admin
def add_commcare_account(request, domain, template="users/add_commcare_account.html"):
    """
    Create a new commcare account
    """
    context = _users_context(request, domain)
    if request.method == "POST":
        form = CommCareAccountForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            #username = format_username(username, domain)
            couch_user = create_hq_user_from_commcare_registration_info(domain, username, password, 
                                                                        device_id='Generated from HQ')
            couch_user.save()
            return HttpResponseRedirect(reverse("commcare_users", args=[domain]))
    else:
        form = CommCareAccountForm()
    context.update(form=form)
    return render_to_response(request, template, context)

@login_and_domain_required
def test_autocomplete(request, domain, template="users/test_autocomplete.html"):
    context = _users_context(request, domain)
    context.update(get_sms_autocomplete_context(request, domain))
    return render_to_response(request, template, context)