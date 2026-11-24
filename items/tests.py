"""
items/tests.py — Automated tests for the items app.

Real Google OAuth can't run in tests, so we use force_login() for views and
build SocialLogin objects by hand to test the email-domain adapter.

Run with:  python manage.py test items -v2
"""
import shutil
import tempfile
from datetime import date, timedelta
from io import BytesIO

from django.contrib.auth.models import AnonymousUser, User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.models import SocialAccount, SocialLogin

from .adapter import CollegeEmailAdapter
from .matching import find_matches, tokens
from .models import Claim, ItemReport, UserProfile

TEMP_MEDIA = tempfile.mkdtemp()
TODAY = date.today()
RECENT = (TODAY - timedelta(days=2)).isoformat()


def make_image(fmt='JPEG', name='photo.jpg', size=(100, 100), content_type=None):
    """A small in-memory image wrapped as an upload."""
    buf = BytesIO()
    Image.new('RGB', size, color='red').save(buf, format=fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type=content_type or f'image/{fmt.lower()}')


def tearDownModule():
    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)


# Password hashing is deliberately slow; a fast hasher keeps the suite quick.
@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class BaseTestCase(TestCase):
    """Shared setup: three users and one open lost item posted by alice."""

    def setUp(self):
        self.user1 = User.objects.create_user('alice', 'alice@gmail.com', 'testpass123',
                                              first_name='Alice', last_name='Mehta')
        self.user2 = User.objects.create_user('bob', 'bob@gmail.com', 'testpass123')
        self.user3 = User.objects.create_user('carol', 'carol@gmail.com', 'testpass123')
        self.client = Client()
        self.lost_item = ItemReport.objects.create(
            report_type=ItemReport.LOST, category=ItemReport.BAGS, title='Blue Backpack',
            description='A blue backpack with laptop inside', location='Library',
            date=TODAY, posted_by=self.user1,
        )

    def make_item(self, **kw):
        data = dict(report_type=ItemReport.FOUND, category=ItemReport.BAGS, title='Found Thing',
                    description='desc', location='Somewhere', date=TODAY, posted_by=self.user2)
        data.update(kw)
        return ItemReport.objects.create(**data)


# ─── Authentication & access control ─────────────────────

class AuthTests(BaseTestCase):

    def test_anonymous_redirected_to_our_landing_page(self):
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, f"{reverse('login')}?next=/", fetch_redirect_response=False)

    def test_landing_page_has_google_button(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, 'Continue with Google')

    def test_landing_redirects_when_logged_in(self):
        self.client.force_login(self.user1)
        self.assertRedirects(self.client.get(reverse('login')), reverse('dashboard'))

    def test_local_signup_is_closed(self):
        """The email-domain check can't be bypassed through /accounts/signup/."""
        self.client.post(reverse('account_signup'), {
            'email': 'intruder@evil.com', 'password1': 'S3cure-pass!word', 'password2': 'S3cure-pass!word',
        })
        self.assertFalse(User.objects.filter(email='intruder@evil.com').exists())

    def test_error_messages_use_bootstrap_danger_class(self):
        self.client.force_login(self.user2)
        response = self.client.get(reverse('edit_item', args=[self.lost_item.pk]), follow=True)
        self.assertContains(response, 'text-bg-danger')
        self.assertNotContains(response, 'text-bg-error')


@override_settings(ALLOWED_EMAIL_DOMAIN='college.edu')
class CollegeEmailAdapterTests(TestCase):

    def _login(self, extra):
        return SocialLogin(account=SocialAccount(provider='google', uid='123', extra_data=extra))

    def _request(self):
        request = RequestFactory().get('/')
        request.user = AnonymousUser()
        return request

    def test_allowed_domain_passes(self):
        CollegeEmailAdapter().pre_social_login(
            self._request(), self._login({'email': 'Sam@College.edu', 'email_verified': True}))

    def test_other_domain_rejected_with_403(self):
        with self.assertRaises(ImmediateHttpResponse) as ctx:
            CollegeEmailAdapter().pre_social_login(
                self._request(), self._login({'email': 'sam@gmail.com', 'email_verified': True}))
        self.assertEqual(ctx.exception.response.status_code, 403)
        self.assertIn(b"can't sign in", ctx.exception.response.content)

    def test_unverified_email_rejected(self):
        with self.assertRaises(ImmediateHttpResponse):
            CollegeEmailAdapter().pre_social_login(
                self._request(), self._login({'email': 'sam@college.edu', 'email_verified': False}))

    def test_lookalike_domain_rejected(self):
        with self.assertRaises(ImmediateHttpResponse):
            CollegeEmailAdapter().pre_social_login(
                self._request(), self._login({'email': 'sam@evilcollege.edu', 'email_verified': True}))

    def test_missing_email_rejected(self):
        with self.assertRaises(ImmediateHttpResponse):
            CollegeEmailAdapter().pre_social_login(self._request(), self._login({}))


# ─── Dashboard ────────────────────────────────────────────

class DashboardTests(BaseTestCase):

    def test_dashboard_loads_for_logged_in_user(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lost')
        self.assertContains(response, 'Found')

    def test_dashboard_shows_items(self):
        self.client.force_login(self.user1)
        self.assertContains(self.client.get(reverse('dashboard')), 'Blue Backpack')

    def test_resolved_hidden_by_default_but_filterable(self):
        done = self.make_item(title='Returned Umbrella', report_type=ItemReport.LOST, status=ItemReport.RESOLVED)
        self.client.force_login(self.user1)
        self.assertNotContains(self.client.get(reverse('dashboard')), 'Returned Umbrella')
        self.assertContains(self.client.get(reverse('dashboard'), {'status': 'resolved'}), 'Returned Umbrella')
        self.assertContains(self.client.get(reverse('dashboard'), {'status': 'all'}), 'Returned Umbrella')
        self.assertEqual(done.status, ItemReport.RESOLVED)

    def test_stats_count_resolved(self):
        self.make_item(status=ItemReport.RESOLVED)
        self.client.force_login(self.user1)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['stats']['resolved'], 1)
        self.assertEqual(response.context['stats']['open_lost'], 1)

    def test_pagination(self):
        for i in range(12):
            self.make_item(report_type=ItemReport.LOST, title=f'Lost thing {i}')
        self.client.force_login(self.user1)
        page1 = self.client.get(reverse('dashboard')).context['lost_page']
        self.assertEqual(page1.paginator.count, 13)
        self.assertEqual(page1.paginator.num_pages, 2)
        self.assertEqual(len(page1.object_list), 9)
        page2 = self.client.get(reverse('dashboard'), {'lost_page': 2, 'tab': 'lost'}).context['lost_page']
        self.assertEqual(len(page2.object_list), 4)

    def test_pagination_links_keep_filters(self):
        for i in range(10):
            self.make_item(report_type=ItemReport.LOST, title=f'Bag {i}', category=ItemReport.BAGS)
        self.client.force_login(self.user1)
        response = self.client.get(reverse('dashboard'), {'category': 'BAGS'})
        self.assertContains(response, 'category=BAGS')
        self.assertContains(response, 'lost_page=2')

    def test_garbage_page_number_does_not_crash(self):
        self.client.force_login(self.user1)
        for bad in ('abc', '-4', '9999'):
            self.assertEqual(self.client.get(reverse('dashboard'), {'lost_page': bad}).status_code, 200)

    def test_invalid_filters_fall_back(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('dashboard'), {'category': 'NOPE', 'status': 'weird'})
        self.assertEqual(response.context['category'], '')
        self.assertEqual(response.context['status'], 'open')

    def test_switches_to_found_tab_when_only_found_matches(self):
        self.make_item(title='Silver Watch', category=ItemReport.ACCESSORIES)
        self.client.force_login(self.user1)
        response = self.client.get(reverse('dashboard'), {'q': 'Watch'})
        self.assertEqual(response.context['active_tab'], 'found')


# ─── Search / filter ──────────────────────────────────────

class SearchFilterTests(BaseTestCase):

    def test_search_by_title(self):
        self.client.force_login(self.user1)
        self.assertContains(self.client.get(reverse('dashboard'), {'q': 'Backpack'}), 'Blue Backpack')

    def test_search_by_location(self):
        self.client.force_login(self.user1)
        self.assertContains(self.client.get(reverse('dashboard'), {'q': 'Library'}), 'Blue Backpack')

    def test_search_by_description(self):
        self.client.force_login(self.user1)
        self.assertContains(self.client.get(reverse('dashboard'), {'q': 'laptop'}), 'Blue Backpack')

    def test_search_no_results(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('dashboard'), {'q': 'xyznotfound'})
        self.assertNotContains(response, 'Blue Backpack')
        self.assertContains(response, 'Clear filters')

    def test_filter_by_category(self):
        self.make_item(report_type=ItemReport.LOST, title='Spare Keys', category=ItemReport.KEYS)
        self.client.force_login(self.user1)
        response = self.client.get(reverse('dashboard'), {'category': 'KEYS'})
        self.assertContains(response, 'Spare Keys')
        self.assertNotContains(response, 'Blue Backpack')


# ─── Create ───────────────────────────────────────────────

class CreateItemTests(BaseTestCase):

    def post_item(self, **overrides):
        data = {'report_type': 'LOST', 'category': 'OTHER', 'title': 'Red Wallet',
                'description': 'Lost my red wallet near cafeteria', 'location': 'Cafeteria', 'date': RECENT}
        data.update(overrides)
        return self.client.post(reverse('create_item'), data)

    def test_create_requires_login(self):
        self.assertEqual(self.client.get(reverse('create_item')).status_code, 302)

    def test_create_lost_item_redirects_to_detail(self):
        self.client.force_login(self.user1)
        response = self.post_item()
        item = ItemReport.objects.get(title='Red Wallet')
        self.assertRedirects(response, reverse('item_detail', args=[item.pk]))
        self.assertEqual(item.posted_by, self.user1)

    def test_create_found_item(self):
        self.client.force_login(self.user2)
        self.post_item(report_type='FOUND', title='USB Drive', category='ELECTRONICS')
        item = ItemReport.objects.get(title='USB Drive')
        self.assertEqual((item.report_type, item.category, item.posted_by), ('FOUND', 'ELECTRONICS', self.user2))

    def test_type_preselected_from_query_string(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('create_item'), {'type': 'FOUND'})
        self.assertEqual(response.context['form'].initial['report_type'], 'FOUND')

    def test_new_report_defaults_to_today(self):
        self.client.force_login(self.user1)
        form = self.client.get(reverse('create_item')).context['form']
        self.assertEqual(form.initial['date'], TODAY)

    def test_bad_type_defaults_to_lost(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('create_item'), {'type': 'junk'})
        self.assertEqual(response.context['form'].initial['report_type'], 'LOST')

    def test_form_has_no_blank_type_choice(self):
        self.client.force_login(self.user1)
        form = self.client.get(reverse('create_item')).context['form']
        self.assertEqual([c[0] for c in form.fields['report_type'].choices], ['LOST', 'FOUND'])

    def test_future_date_rejected(self):
        self.client.force_login(self.user1)
        response = self.post_item(title='Future Item', date=(TODAY + timedelta(days=30)).isoformat())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'cannot be in the future')
        self.assertFalse(ItemReport.objects.filter(title='Future Item').exists())

    @override_settings(MEDIA_ROOT=TEMP_MEDIA)
    def test_create_item_with_image(self):
        self.client.force_login(self.user1)
        self.post_item(title='Laptop Charger', image=make_image())
        self.assertTrue(ItemReport.objects.get(title='Laptop Charger').image)

    @override_settings(MEDIA_ROOT=TEMP_MEDIA)
    def test_non_image_file_rejected(self):
        self.client.force_login(self.user1)
        fake = SimpleUploadedFile('virus.jpg', b'not really an image', content_type='image/jpeg')
        response = self.post_item(title='Fake Photo', image=fake)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ItemReport.objects.filter(title='Fake Photo').exists())

    @override_settings(MEDIA_ROOT=TEMP_MEDIA)
    def test_disallowed_image_format_rejected(self):
        self.client.force_login(self.user1)
        response = self.post_item(title='Gif Photo', image=make_image('GIF', 'a.gif'))
        self.assertContains(response, 'Only JPEG, PNG, and WebP')

    @override_settings(MEDIA_ROOT=TEMP_MEDIA, MAX_UPLOAD_SIZE_MB=0.0001)
    def test_oversized_image_rejected(self):
        self.client.force_login(self.user1)
        response = self.post_item(title='Huge Photo', image=make_image(size=(400, 400)))
        self.assertContains(response, 'must be smaller than')


# ─── Edit / delete / ownership ────────────────────────────

class EditDeleteTests(BaseTestCase):

    def test_owner_can_edit(self):
        self.client.force_login(self.user1)
        response = self.client.post(reverse('edit_item', args=[self.lost_item.pk]), {
            'report_type': 'LOST', 'category': 'BAGS', 'title': 'Navy Backpack',
            'description': 'updated', 'location': 'Library', 'date': RECENT,
        })
        self.assertRedirects(response, reverse('item_detail', args=[self.lost_item.pk]))
        self.lost_item.refresh_from_db()
        self.assertEqual(self.lost_item.title, 'Navy Backpack')

    def test_edit_form_prefills_date(self):
        self.client.force_login(self.user1)
        self.assertContains(self.client.get(reverse('edit_item', args=[self.lost_item.pk])),
                            f'value="{TODAY.isoformat()}"')

    def test_non_owner_cannot_edit(self):
        self.client.force_login(self.user2)
        response = self.client.post(reverse('edit_item', args=[self.lost_item.pk]), {
            'report_type': 'LOST', 'category': 'BAGS', 'title': 'Hacked', 'description': 'x',
            'location': 'x', 'date': RECENT,
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.lost_item.refresh_from_db()
        self.assertEqual(self.lost_item.title, 'Blue Backpack')

    def test_non_owner_cannot_delete(self):
        self.client.force_login(self.user2)
        self.client.post(reverse('delete_item', args=[self.lost_item.pk]))
        self.assertTrue(ItemReport.objects.filter(pk=self.lost_item.pk).exists())

    def test_delete_get_asks_for_confirmation(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('delete_item', args=[self.lost_item.pk]))
        self.assertContains(response, 'Delete this report?')
        self.assertTrue(ItemReport.objects.filter(pk=self.lost_item.pk).exists())

    def test_owner_can_delete(self):
        self.client.force_login(self.user1)
        self.client.post(reverse('delete_item', args=[self.lost_item.pk]))
        self.assertFalse(ItemReport.objects.filter(pk=self.lost_item.pk).exists())

    def test_missing_item_is_404(self):
        self.client.force_login(self.user1)
        self.assertEqual(self.client.get(reverse('item_detail', args=[99999])).status_code, 404)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ImageCleanupTests(BaseTestCase):

    def _with_image(self):
        item = self.make_item(posted_by=self.user1)
        item.image.save('one.jpg', make_image(), save=True)
        return item

    def test_file_deleted_with_report(self):
        item = self._with_image()
        path = item.image.path
        item.delete()
        with self.assertRaises(FileNotFoundError):
            open(path, 'rb')

    def test_replaced_photo_removes_old_file(self):
        item = self._with_image()
        old_path = item.image.path
        item.image.save('two.jpg', make_image(name='two.jpg'), save=True)
        with self.assertRaises(FileNotFoundError):
            open(old_path, 'rb')

    def test_remove_photo_checkbox(self):
        item = self._with_image()
        self.client.force_login(self.user1)
        self.client.post(reverse('edit_item', args=[item.pk]), {
            'report_type': 'FOUND', 'category': 'BAGS', 'title': item.title, 'description': 'd',
            'location': 'l', 'date': RECENT, 'remove_image': 'on',
        })
        item.refresh_from_db()
        self.assertFalse(item.image)


# ─── Detail page ──────────────────────────────────────────

class DetailTests(BaseTestCase):

    def test_owner_sees_manage_actions(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('item_detail', args=[self.lost_item.pk]))
        self.assertContains(response, 'Manage this report')
        self.assertContains(response, 'Mark resolved')
        self.assertNotContains(response, 'Send message')

    def test_visitor_sees_message_form_not_owner_actions(self):
        self.client.force_login(self.user2)
        response = self.client.get(reverse('item_detail', args=[self.lost_item.pk]))
        self.assertContains(response, 'Found this item?')
        self.assertContains(response, 'Send message')
        self.assertNotContains(response, 'Mark resolved')

    def test_found_report_asks_for_proof(self):
        found = self.make_item()
        self.client.force_login(self.user1)
        self.assertContains(self.client.get(reverse('item_detail', args=[found.pk])), 'Is this yours?')

    def test_resolved_item_closes_messages(self):
        self.lost_item.mark_resolved()
        self.client.force_login(self.user2)
        response = self.client.get(reverse('item_detail', args=[self.lost_item.pk]))
        self.assertContains(response, 'This report is resolved')
        self.assertNotContains(response, 'Send message')

    def test_detail_shows_possible_match(self):
        self.make_item(title='Backpack blue', location='Library entrance')
        self.client.force_login(self.user1)
        response = self.client.get(reverse('item_detail', args=[self.lost_item.pk]))
        self.assertContains(response, 'Possible matches')
        self.assertContains(response, 'Backpack blue')


# ─── Resolve (AJAX) ───────────────────────────────────────

class ResolveItemTests(BaseTestCase):

    def post(self):
        return self.client.post(reverse('resolve_item', args=[self.lost_item.pk]), content_type='application/json')

    def test_owner_can_resolve(self):
        self.client.force_login(self.user1)
        self.assertEqual(self.post().status_code, 200)
        self.lost_item.refresh_from_db()
        self.assertEqual(self.lost_item.status, ItemReport.RESOLVED)
        self.assertIsNotNone(self.lost_item.resolved_at)

    def test_non_owner_cannot_resolve(self):
        self.client.force_login(self.user2)
        self.assertEqual(self.post().status_code, 403)
        self.lost_item.refresh_from_db()
        self.assertEqual(self.lost_item.status, ItemReport.OPEN)

    def test_resolve_requires_post(self):
        self.client.force_login(self.user1)
        self.assertEqual(self.client.get(reverse('resolve_item', args=[self.lost_item.pk])).status_code, 405)

    def test_resolve_already_resolved(self):
        self.lost_item.mark_resolved()
        self.client.force_login(self.user1)
        self.assertEqual(self.post().status_code, 400)

    def test_csrf_cookie_is_set_on_pages_without_forms(self):
        """The Resolve button posts via fetch(); it needs the token even on form-less pages."""
        self.client.force_login(self.user1)
        response = self.client.get(reverse('dashboard'))
        self.assertIn('csrftoken', response.cookies)
        self.assertContains(response, 'name="csrf-token"')

    def test_resolve_works_with_token_from_page(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user1)
        csrf_client.get(reverse('dashboard'))                  # sets the cookie, like a real visit
        token = csrf_client.cookies['csrftoken'].value
        response = csrf_client.post(reverse('resolve_item', args=[self.lost_item.pk]), HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)

    def test_resolve_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user1)
        response = csrf_client.post(reverse('resolve_item', args=[self.lost_item.pk]))
        self.assertEqual(response.status_code, 403)


# ─── Messages / claims ────────────────────────────────────

class ClaimTests(BaseTestCase):
    MESSAGE = 'I found it near the library desk, it has a panda keychain.'

    def send(self, user=None, message=None, item=None):
        self.client.force_login(user or self.user2)
        return self.client.post(reverse('claim_item', args=[(item or self.lost_item).pk]),
                                {'message': message if message is not None else self.MESSAGE})

    def test_claim_is_saved_and_poster_emailed(self):
        response = self.send()
        self.assertRedirects(response, reverse('item_detail', args=[self.lost_item.pk]))
        claim = Claim.objects.get()
        self.assertEqual((claim.item, claim.claimant, claim.status), (self.lost_item, self.user2, Claim.PENDING))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['alice@gmail.com'])
        self.assertIn('panda keychain', mail.outbox[0].body)

    def test_cannot_message_yourself(self):
        self.send(user=self.user1)
        self.assertEqual(Claim.objects.count(), 0)

    def test_cannot_message_twice(self):
        self.send()
        self.send()
        self.assertEqual(Claim.objects.count(), 1)

    def test_cannot_message_resolved_report(self):
        self.lost_item.mark_resolved()
        self.send()
        self.assertEqual(Claim.objects.count(), 0)

    def test_short_message_rejected(self):
        self.send(message='hi')
        self.assertEqual(Claim.objects.count(), 0)

    def test_claim_requires_post(self):
        self.client.force_login(self.user2)
        self.assertEqual(self.client.get(reverse('claim_item', args=[self.lost_item.pk])).status_code, 405)

    def test_email_failure_does_not_break_request(self):
        """An unreachable SMTP server must not turn a saved message into a 500."""
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
                               EMAIL_HOST='127.0.0.1', EMAIL_PORT=1):
            response = self.send()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Claim.objects.filter(claimant=self.user2).exists())

    def test_database_enforces_one_claim_per_user(self):
        Claim.objects.create(item=self.lost_item, claimant=self.user2, message='x' * 12)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Claim.objects.create(item=self.lost_item, claimant=self.user2, message='y' * 12)

    def test_owner_sees_messages_with_email(self):
        self.send()
        self.client.force_login(self.user1)
        response = self.client.get(reverse('item_detail', args=[self.lost_item.pk]))
        self.assertContains(response, 'panda keychain')
        self.assertContains(response, 'bob@gmail.com')
        self.assertContains(response, 'Accept')

    def test_claimant_sees_pending_status(self):
        self.send()
        response = self.client.get(reverse('item_detail', args=[self.lost_item.pk]))
        self.assertContains(response, "You've written to")
        self.assertContains(response, 'Pending')

    def test_accept_resolves_report_and_declines_others(self):
        self.send(user=self.user2)
        self.send(user=self.user3)
        mail.outbox.clear()
        bob_claim = Claim.objects.get(claimant=self.user2)
        self.client.force_login(self.user1)
        response = self.client.post(reverse('accept_claim', args=[bob_claim.pk]))
        self.assertRedirects(response, reverse('item_detail', args=[self.lost_item.pk]))
        self.lost_item.refresh_from_db()
        bob_claim.refresh_from_db()
        self.assertEqual(self.lost_item.status, ItemReport.RESOLVED)
        self.assertEqual(bob_claim.status, Claim.ACCEPTED)
        self.assertEqual(Claim.objects.get(claimant=self.user3).status, Claim.REJECTED)
        self.assertEqual(mail.outbox[0].to, ['bob@gmail.com'])

    def test_decline_keeps_report_open(self):
        self.send()
        claim = Claim.objects.get()
        self.client.force_login(self.user1)
        self.client.post(reverse('decline_claim', args=[claim.pk]))
        claim.refresh_from_db()
        self.lost_item.refresh_from_db()
        self.assertEqual(claim.status, Claim.REJECTED)
        self.assertEqual(self.lost_item.status, ItemReport.OPEN)

    def test_only_owner_can_respond(self):
        self.send()
        claim = Claim.objects.get()
        self.client.force_login(self.user3)
        self.client.post(reverse('accept_claim', args=[claim.pk]))
        claim.refresh_from_db()
        self.assertEqual(claim.status, Claim.PENDING)

    def test_respond_requires_post(self):
        self.send()
        claim = Claim.objects.get()
        self.client.force_login(self.user1)
        self.assertEqual(self.client.get(reverse('accept_claim', args=[claim.pk])).status_code, 405)

    def test_cannot_respond_twice(self):
        self.send()
        claim = Claim.objects.get()
        self.client.force_login(self.user1)
        self.client.post(reverse('decline_claim', args=[claim.pk]))
        self.client.post(reverse('accept_claim', args=[claim.pk]))
        claim.refresh_from_db()
        self.assertEqual(claim.status, Claim.REJECTED)

    def test_navbar_badge_counts_unanswered_messages(self):
        self.send()
        self.client.force_login(self.user1)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['pending_claims'], 1)
        self.assertContains(response, 'nav-badge')


# ─── Matching ─────────────────────────────────────────────

class MatchingTests(BaseTestCase):

    def test_tokens_drop_stop_words_and_plurals(self):
        self.assertEqual(tokens('The Blue Backpacks near Library'), {'blue', 'backpack', 'library'})

    def test_finds_similar_found_report(self):
        found = self.make_item(title='Blue backpack', location='Library entrance')
        self.assertIn(found, find_matches(self.lost_item))

    def test_works_in_both_directions(self):
        found = self.make_item(title='Blue backpack', location='Library entrance')
        self.assertIn(self.lost_item, find_matches(found))

    def test_ignores_other_category(self):
        self.make_item(title='Blue backpack', category=ItemReport.KEYS)
        self.assertEqual(find_matches(self.lost_item), [])

    def test_other_category_can_match_anything(self):
        found = self.make_item(title='Blue backpack', category=ItemReport.OTHER)
        self.assertIn(found, find_matches(self.lost_item))

    def test_ignores_far_dates(self):
        self.make_item(title='Blue backpack', date=TODAY - timedelta(days=40))
        self.assertEqual(find_matches(self.lost_item), [])

    def test_ignores_resolved_and_same_type_and_same_poster(self):
        self.make_item(title='Blue backpack', status=ItemReport.RESOLVED)
        self.make_item(title='Blue backpack', report_type=ItemReport.LOST)
        self.make_item(title='Blue backpack', posted_by=self.user1)
        self.assertEqual(find_matches(self.lost_item), [])

    def test_one_generic_shared_word_is_not_a_match(self):
        earbuds = self.make_item(report_type=ItemReport.LOST, category=ItemReport.ELECTRONICS,
                                 title='Black earbuds case', description='Black charging case, left earbud missing',
                                 location='Canteen', posted_by=self.user1)
        self.make_item(category=ItemReport.ELECTRONICS, title='iPhone with green case',
                       description='Green silicone case, lock screen shows a dog', location='Block C')
        self.assertEqual(find_matches(earbuds), [])

    def test_title_word_plus_same_place_is_a_match(self):
        found = self.make_item(title='Backpack', location='Library')
        self.assertIn(found, find_matches(self.lost_item))

    def test_needs_something_in_common(self):
        self.make_item(title='Umbrella', location='Parking')
        self.assertEqual(find_matches(self.lost_item), [])

    def test_best_match_first_and_limited(self):
        weak = self.make_item(title='Backpack', location='Canteen')
        strong = self.make_item(title='Blue backpack', location='Library')
        for i in range(4):
            self.make_item(title=f'Blue backpack {i}', location='Library')
        result = find_matches(self.lost_item, limit=3)
        self.assertEqual(len(result), 3)
        self.assertNotIn(weak, result)
        self.assertGreaterEqual(result[0].match_score, result[-1].match_score)
        self.assertIn(strong, find_matches(self.lost_item, limit=10))


# ─── My Reports ───────────────────────────────────────────

class MyReportsTests(BaseTestCase):

    def test_my_reports_shows_own_items(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('my_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Blue Backpack')

    def test_my_reports_hides_others_items(self):
        self.client.force_login(self.user2)
        self.assertNotContains(self.client.get(reverse('my_reports')), 'Blue Backpack')

    def test_my_reports_requires_login(self):
        self.assertIn(self.client.get(reverse('my_reports')).status_code, [301, 302])

    def test_messages_sent_tab_lists_my_claims(self):
        Claim.objects.create(item=self.lost_item, claimant=self.user2, message='I have it, message me!')
        self.client.force_login(self.user2)
        response = self.client.get(reverse('my_reports'), {'tab': 'claims'})
        self.assertEqual(response.context['tab'], 'claims')
        self.assertContains(response, 'I have it, message me!')

    def test_new_messages_chip_on_card(self):
        Claim.objects.create(item=self.lost_item, claimant=self.user2, message='I have it, message me!')
        self.client.force_login(self.user1)
        self.assertContains(self.client.get(reverse('my_reports')), '1 new')


# ─── Models / profile / commands ──────────────────────────

class TemplateFilterTests(TestCase):

    def test_ago_uses_largest_unit_only(self):
        from django.utils import timezone
        from .templatetags.items_extras import ago
        self.assertEqual(ago(timezone.now() - timedelta(hours=12, minutes=18)), '12 hours ago')
        self.assertEqual(ago(timezone.now() - timedelta(days=3, hours=5)), '3 days ago')
        self.assertEqual(ago(timezone.now()), 'just now')


class ModelTests(BaseTestCase):

    def test_ticket_number_and_icon(self):
        self.assertEqual(self.lost_item.ticket_number, f'{self.lost_item.pk:04d}')
        self.assertEqual(self.lost_item.category_icon, 'bi-backpack2')

    def test_mark_resolved_sets_timestamp(self):
        self.lost_item.mark_resolved()
        self.lost_item.refresh_from_db()
        self.assertEqual(self.lost_item.status, ItemReport.RESOLVED)
        self.assertIsNotNone(self.lost_item.resolved_at)

    def test_open_items_sort_before_resolved(self):
        self.make_item(title='Done', status=ItemReport.RESOLVED)
        self.make_item(title='Newer open')
        statuses = list(ItemReport.objects.values_list('status', flat=True))
        self.assertEqual(statuses, sorted(statuses))


class UserProfileTests(BaseTestCase):

    def test_profile_auto_created_once(self):
        self.assertEqual(UserProfile.objects.filter(user=self.user1).count(), 1)
        self.user1.save()
        self.assertEqual(UserProfile.objects.filter(user=self.user1).count(), 1)

    def test_profile_picture_fallback_is_url_encoded(self):
        url = self.user1.profile.get_profile_picture_url()
        self.assertTrue(url.startswith('http'))
        self.assertIn('Alice%20Mehta', url)


class SeedDemoTests(TestCase):

    def test_seed_is_idempotent_and_resettable(self):
        call_command('seed_demo', verbosity=0)
        first = ItemReport.objects.count()
        self.assertGreater(first, 10)
        call_command('seed_demo', verbosity=0)
        self.assertEqual(ItemReport.objects.count(), first)
        call_command('seed_demo', '--reset', verbosity=0)
        self.assertEqual(ItemReport.objects.count(), first)
        self.assertTrue(Claim.objects.exists())
