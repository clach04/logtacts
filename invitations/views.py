from braces.views import LoginRequiredMixin
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.utils.crypto import get_random_string
from django.shortcuts import (
    get_object_or_404,
    redirect,
)
from django.views.generic import (
    CreateView,
    FormView,
    View,
)

from contacts.models import (
    Book,
    BookOwner,
)

from .models import Invitation
from .forms import InvitationForm


class CreateInviteView(LoginRequiredMixin, CreateView):

    model = Invitation
    form_class = InvitationForm
    template_name = 'invite_edit.html'

    def get_success_url(self, **kwargs):
        return reverse('contacts-list')

    def form_valid(self, form):
        form.instance.sender = self.request.user
        if form.cleaned_data.get('share_book'):
            form.instance.book = BookOwner.objects.get(
                user=self.request.user,
            ).book
        messages.success(
            self.request,
            "Invited {}".format(form.cleaned_data.get('email')),
        )
        return super(CreateInviteView, self).form_valid(form)


class AcceptInviteView(FormView):

    form_class = SetPasswordForm
    template_name = "set_password.html"

    def get(self, request, *args, **kwargs):
        response = super(AcceptInviteView, self).get(request, *args, **kwargs)
        if request.user.is_authenticated():
            messages.warning(
                self.request,
                "Logged-in users can't accept invitations",
                )
            return redirect(reverse('contacts-list'))
        invite = get_object_or_404(
            Invitation.objects,
            key=kwargs.get('key'),
            status=Invitation.SENT,
        )
        # By this point we should have a good invite.
        password_plain = get_random_string(20)
        password = make_password(password_plain)
        user = User.objects.create(
            username=invite.email,
            email=invite.email,
            password=password,
        )
        user = authenticate(username=invite.email, password=password_plain)
        if invite.book:
            BookOwner.objects.create(user=user, book=invite.book)
        else:
            book = Book.objects.create(name="{}'s Book".format(user))
            BookOwner.objects.create(book=book,user=user)
        user.save()
        login(request, user)
        invite.status = invite.ACCEPTED
        invite.save()
        return response

    def get_success_url(self):
        return reverse('contacts-list')

    def get_form(self):
        return self.form_class(self.request.user, **self.get_form_kwargs())

    def form_valid(self, form):
        messages.success(
            self.request,
            "Welcome to ContactOtter!",
        )
        return super(AcceptInviteView, self).form_valid(form)
