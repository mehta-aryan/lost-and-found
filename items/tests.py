"""
items/tests.py — Automated tests for the items app.

Uses Django's TestCase and test client with force_login()
(since real Google OAuth can't be tested without API keys).

Run with: python manage.py test items -v2
"""
import tempfile
from datetime import date, timedelta

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from PIL import Image

from .models import ItemReport, UserProfile

# Use a temporary directory for media during tests
TEMP_MEDIA = tempfile.mkdtemp()


def _create_test_image(fmt='JPEG', suffix='.jpg'):
    """Create a small in-memory image file for upload tests."""
    img = Image.new('RGB', (100, 100), color='red')
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    img.save(tmp, format=fmt)
    tmp.seek(0)
    return tmp


class BaseTestCase(TestCase):
    """Shared setup: creates two users and a sample item."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='alice', password='testpass123', email='alice@gmail.com'
        )
        self.user2 = User.objects.create_user(
            username='bob', password='testpass123', email='bob@gmail.com'
        )
        self.client = Client()

        self.lost_item = ItemReport.objects.create(
            report_type=ItemReport.LOST,
            title='Blue Backpack',
            description='A blue backpack with laptop inside',
            location='Library',
            date=date.today(),
            posted_by=self.user1,
        )


# ─── Dashboard ────────────────────────────────────────────

class DashboardTests(BaseTestCase):

    def test_dashboard_requires_login(self):
        """Anonymous users should be redirected."""
        response = self.client.get(reverse('dashboard'))
        self.assertIn(response.status_code, [301, 302])

    def test_dashboard_loads_for_logged_in_user(self):
        """Authenticated users should see the dashboard (HTTP 200)."""
        self.client.force_login(self.user1)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lost Items')
        self.assertContains(response, 'Found Items')

    def test_dashboard_shows_items(self):
        """Dashboard should display existing items."""
        self.client.force_login(self.user1)
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Blue Backpack')


# ─── Create Item ──────────────────────────────────────────

class CreateItemTests(BaseTestCase):

    def test_create_lost_item(self):
        self.client.force_login(self.user1)
        response = self.client.post(reverse('create_item'), {
            'report_type': 'LOST',
            'title': 'Red Wallet',
            'description': 'Lost my red wallet near cafeteria',
            'location': 'Cafeteria',
            'date': '2026-10-15',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ItemReport.objects.filter(title='Red Wallet').exists())

    def test_create_found_item(self):
        self.client.force_login(self.user2)
        response = self.client.post(reverse('create_item'), {
            'report_type': 'FOUND',
            'title': 'USB Drive',
            'description': 'Found a USB drive in room 301',
            'location': 'Room 301',
            'date': '2026-10-20',
        })
        self.assertEqual(response.status_code, 302)
        item = ItemReport.objects.get(title='USB Drive')
        self.assertEqual(item.report_type, 'FOUND')
        self.assertEqual(item.posted_by, self.user2)

    @override_settings(MEDIA_ROOT=TEMP_MEDIA)
    def test_create_item_with_image(self):
        self.client.force_login(self.user1)
        img_file = _create_test_image()
        response = self.client.post(reverse('create_item'), {
            'report_type': 'LOST',
            'title': 'Laptop Charger',
            'description': 'Black Dell charger',
            'location': 'Lab A',
            'date': '2026-10-22',
            'image': img_file,
        })
        self.assertEqual(response.status_code, 302)
        item = ItemReport.objects.get(title='Laptop Charger')
        self.assertTrue(item.image)
        img_file.close()

    def test_future_date_rejected(self):
        """Form should reject dates in the future."""
        self.client.force_login(self.user1)
        future = date.today() + timedelta(days=30)
        response = self.client.post(reverse('create_item'), {
            'report_type': 'LOST',
            'title': 'Future Item',
            'description': 'This should fail',
            'location': 'Nowhere',
            'date': future.isoformat(),
        })
        # Should re-render the form (200), not redirect (302)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ItemReport.objects.filter(title='Future Item').exists())


# ─── Resolve Item (AJAX) ─────────────────────────────────

class ResolveItemTests(BaseTestCase):

    def test_owner_can_resolve(self):
        self.client.force_login(self.user1)
        response = self.client.post(
            reverse('resolve_item', args=[self.lost_item.pk]),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.lost_item.refresh_from_db()
        self.assertEqual(self.lost_item.status, ItemReport.RESOLVED)

    def test_non_owner_cannot_resolve(self):
        self.client.force_login(self.user2)
        response = self.client.post(
            reverse('resolve_item', args=[self.lost_item.pk]),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        self.lost_item.refresh_from_db()
        self.assertEqual(self.lost_item.status, ItemReport.OPEN)

    def test_resolve_requires_post(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('resolve_item', args=[self.lost_item.pk]))
        self.assertEqual(response.status_code, 405)

    def test_resolve_already_resolved(self):
        """Resolving an already-resolved item returns 400."""
        self.lost_item.status = ItemReport.RESOLVED
        self.lost_item.save()
        self.client.force_login(self.user1)
        response = self.client.post(
            reverse('resolve_item', args=[self.lost_item.pk]),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)


# ─── Search / Filter ─────────────────────────────────────

class SearchFilterTests(BaseTestCase):

    def test_search_by_title(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('dashboard'), {'q': 'Backpack'})
        self.assertContains(response, 'Blue Backpack')

    def test_search_by_location(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('dashboard'), {'q': 'Library'})
        self.assertContains(response, 'Blue Backpack')

    def test_search_no_results(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('dashboard'), {'q': 'xyznotfound'})
        self.assertNotContains(response, 'Blue Backpack')


# ─── My Reports ──────────────────────────────────────────

class MyReportsTests(BaseTestCase):

    def test_my_reports_shows_own_items(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('my_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Blue Backpack')

    def test_my_reports_hides_others_items(self):
        self.client.force_login(self.user2)
        response = self.client.get(reverse('my_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Blue Backpack')

    def test_my_reports_requires_login(self):
        response = self.client.get(reverse('my_reports'))
        self.assertIn(response.status_code, [301, 302])


# ─── UserProfile Signal ──────────────────────────────────

class UserProfileTests(BaseTestCase):

    def test_profile_auto_created(self):
        self.assertTrue(UserProfile.objects.filter(user=self.user1).exists())

    def test_profile_picture_fallback(self):
        profile = self.user1.profile
        url = profile.get_profile_picture_url()
        self.assertTrue(url.startswith('http'))
