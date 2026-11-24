"""
python manage.py seed_demo           # add demo users, reports and conversations
python manage.py seed_demo --reset   # remove the demo data first

Demo users use the prefix "demo_" and cannot log in (no password). Sign in
with your own account — or the superuser via /admin/ — to browse the data.
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from items.models import Conversation, ItemReport, Message

L, F = ItemReport.LOST, ItemReport.FOUND

# (type, category, title, description, location, days_ago, status, poster_index)
REPORTS = [
    (L, 'BAGS', 'Blue Nike backpack', 'Navy blue Nike backpack with a keychain shaped like a panda. Has a laptop and a notebook inside.', 'Central Library, 2nd floor', 2, 'OPEN', 0),
    (F, 'BAGS', 'Blue backpack', 'Found a blue backpack under a table near the window. Contains books, no ID.', 'Central Library', 1, 'OPEN', 1),
    (L, 'ELECTRONICS', 'Black boAt earbuds case', 'Black charging case, left earbud is missing. Small scratch on the lid.', 'Canteen', 3, 'OPEN', 2),
    (F, 'ELECTRONICS', 'iPhone with green case', 'Found a phone with a green silicone case. Locked, lock screen shows a dog.', 'Block C, Room 301', 4, 'OPEN', 3),
    (L, 'WALLET_ID', 'Brown leather wallet', 'Brown wallet with college ID and two bank cards. Name on the ID starts with R.', 'Sports ground', 5, 'OPEN', 1),
    (F, 'WALLET_ID', 'College ID card', 'Found an ID card near the bus stop. Will hand it over to the owner.', 'Main gate bus stop', 2, 'OPEN', 0),
    (L, 'KEYS', 'Hostel room keys', 'Three keys on a red lanyard with a Yamaha tag.', 'Hostel B corridor', 6, 'OPEN', 4),
    (F, 'KEYS', 'Bike key with blue cap', 'Single bike key with a blue rubber cap.', 'Parking lot', 7, 'OPEN', 2),
    (L, 'BOOKS', 'Data Structures textbook', 'Thick blue textbook, name written on the first page and sticky notes inside.', 'Lecture Hall 4', 8, 'OPEN', 3),
    (F, 'ACCESSORIES', 'Silver wrist watch', 'Silver analog watch with a brown strap, found on a bench.', 'Garden near admin block', 3, 'OPEN', 4),
    (L, 'ACCESSORIES', 'Grey hoodie', 'Plain grey hoodie, size M, left on a chair after the seminar.', 'Auditorium', 10, 'RESOLVED', 0),
    (F, 'OTHER', 'Steel water bottle', 'Silver steel bottle with stickers on it.', 'Cafeteria', 9, 'RESOLVED', 1),
    (L, 'ELECTRONICS', 'Scientific calculator', 'Casio fx-991EX with initials scratched on the back.', 'Exam hall 2', 1, 'OPEN', 2),
    (F, 'BOOKS', 'Spiral notebook', 'Red spiral notebook with circuit diagrams.', 'Electronics lab', 2, 'OPEN', 3),
]

PEOPLE = [
    ('Aanya', 'Sharma'), ('Rohan', 'Verma'), ('Priya', 'Nair'), ('Kabir', 'Singh'), ('Meera', 'Iyer'),
]


class Command(BaseCommand):
    help = 'Create demo users, lost/found reports and conversations so the UI has something to show.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete existing demo data first.')

    def handle(self, *args, **opts):
        if opts['reset']:
            User.objects.filter(username__startswith='demo_').delete()
            self.stdout.write('Removed previous demo data.')

        domain = getattr(settings, 'ALLOWED_EMAIL_DOMAIN', '') or 'example.edu'
        users = []
        for first, last in PEOPLE:
            username = f'demo_{first.lower()}'
            user, created = User.objects.get_or_create(username=username, defaults={
                'first_name': first, 'last_name': last, 'email': f'{first.lower()}.{last.lower()}@{domain}',
            })
            if created:
                user.set_unusable_password()
                user.save()
            users.append(user)

        today = timezone.localdate()
        made = 0
        items = []
        for kind, cat, title, desc, loc, ago, status, who in REPORTS:
            item, created = ItemReport.objects.get_or_create(
                title=title, posted_by=users[who], report_type=kind,
                defaults={'category': cat, 'description': desc, 'location': loc,
                          'date': today - timedelta(days=ago), 'status': status,
                          'resolved_at': timezone.now() if status == 'RESOLVED' else None},
            )
            made += created
            items.append(item)

        # Sample conversations so the chat UI has something to show
        def seed_conv(item, participant, msgs):
            conv, _ = Conversation.objects.get_or_create(item=item, participant=participant)
            for sender, body in msgs:
                if not conv.messages.filter(sender=sender, body=body).exists():
                    Message.objects.create(conversation=conv, sender=sender, body=body)
            conv.touch()

        seed_conv(items[1], users[0], [
            (users[0], 'That sounds like mine! It has a panda keychain on the front zip and a Dell laptop inside.'),
            (users[1], 'That matches — there is a panda keychain and a Dell sticker on the lid. Where can we meet?'),
            (users[0], 'I can be at the library lobby tomorrow at 11 am.'),
        ])
        seed_conv(items[3], users[2], [
            (users[2], 'I think this is my phone. The lock screen shows a golden retriever called Bruno.'),
            (users[3], 'Yes! That is exactly the lock screen. DM me to arrange handover.'),
        ])

        self.stdout.write(self.style.SUCCESS(
            f'Done: {len(users)} demo users, {made} new reports. '
            f'Sign in and open the dashboard to see them.'))
