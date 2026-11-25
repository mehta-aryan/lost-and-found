"""
items/views.py — View functions (the "V" in MVT)

All views except the login landing page require @login_required.
Ownership is always enforced on the server, never just hidden in the UI.
"""

from datetime import date

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Count, Max, OuterRef, Q, Subquery
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ItemReportForm, MessageForm
from .matching import find_matches
from .models import Conversation, ItemReport, Message


# ── Helpers ───────────────────────────────────────────────

def _display_name(user):
    return user.get_full_name() or user.username


def _conversation_or_404(request, pk):
    """Return the conversation if request.user is a participant or the item owner, else 404."""
    conv = get_object_or_404(
        Conversation.objects.select_related('item', 'item__posted_by', 'participant'),
        pk=pk,
    )
    me = request.user
    if me != conv.participant and me != conv.item.posted_by:
        from django.http import Http404
        raise Http404
    return conv


def _mark_incoming_read(conv, me):
    """Mark messages from the other person as read."""
    conv.messages.filter(read_at__isnull=True).exclude(sender=me).update(read_at=timezone.now())


# ── Public ────────────────────────────────────────────────

def login_view(request):
    """Landing page for signed-out visitors."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'items/login.html', {'next': request.GET.get('next', '')})


# ── Dashboard ─────────────────────────────────────────────

@login_required
def dashboard(request):
    """
    Lost / Found tabs with search, category + status filters and pagination.
    Filters: q (title, location, description), category, status (open|resolved|all).
    """
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    status = request.GET.get('status', 'open')

    if category not in dict(ItemReport.CATEGORY_CHOICES):
        category = ''
    if status not in ('open', 'resolved', 'all'):
        status = 'open'

    items = ItemReport.objects.select_related('posted_by')
    if query:
        items = items.filter(
            Q(title__icontains=query) | Q(location__icontains=query) | Q(description__icontains=query)
        )
    if category:
        items = items.filter(category=category)
    if status == 'open':
        items = items.filter(status=ItemReport.OPEN)
    elif status == 'resolved':
        items = items.filter(status=ItemReport.RESOLVED)

    per_page = getattr(settings, 'ITEMS_PER_PAGE', 9)
    lost_page = Paginator(items.filter(report_type=ItemReport.LOST), per_page).get_page(request.GET.get('lost_page'))
    found_page = Paginator(items.filter(report_type=ItemReport.FOUND), per_page).get_page(request.GET.get('found_page'))

    # Which tab is showing: an explicit ?tab=…, else Lost — unless Lost is empty and Found isn't.
    active_tab = request.GET.get('tab')
    tab_explicit = active_tab in ('lost', 'found')
    if not tab_explicit:
        active_tab = 'lost'
        if lost_page.paginator.count == 0 and found_page.paginator.count > 0:
            active_tab, tab_explicit = 'found', True

    stats = ItemReport.objects.aggregate(
        open_lost=Count('pk', filter=Q(status=ItemReport.OPEN, report_type=ItemReport.LOST)),
        open_found=Count('pk', filter=Q(status=ItemReport.OPEN, report_type=ItemReport.FOUND)),
        resolved=Count('pk', filter=Q(status=ItemReport.RESOLVED)),
    )

    return render(request, 'items/dashboard.html', {
        'lost_page': lost_page,
        'found_page': found_page,
        'query': query,
        'category': category,
        'status': status,
        'categories': ItemReport.CATEGORY_CHOICES,
        'filters_active': bool(query or category or status != 'open'),
        'active_tab': active_tab,
        'tab_explicit': tab_explicit,
        'stats': stats,
    })


# ── Item detail ───────────────────────────────────────────

@login_required
def item_detail(request, pk):
    item = get_object_or_404(ItemReport.objects.select_related('posted_by'), pk=pk)
    is_owner = item.posted_by_id == request.user.id
    can_resolve = is_owner or request.user.is_staff

    ctx = {
        'item': item,
        'is_owner': is_owner,
        'can_resolve': can_resolve,
        'matches': find_matches(item) if item.is_open else [],
    }
    if is_owner:
        # Show all conversations for this report with messages prefetched
        convs = item.conversations.select_related('participant').prefetch_related('messages')
        conv_data = []
        for conv in convs:
            msgs = list(conv.messages.all())
            last = msgs[-1] if msgs else None
            unread = sum(1 for m in msgs if m.read_at is None and m.sender != request.user)
            conv_data.append({'conv': conv, 'last': last, 'unread': unread})
        ctx['conv_data'] = conv_data
    else:
        # Check if visitor already has a conversation for this report
        ctx['my_conv'] = item.conversations.filter(participant=request.user).first()

    return render(request, 'items/item_detail.html', ctx)


# ── Create / Edit / Delete ────────────────────────────────

@login_required
def create_item(request):
    """GET shows the form (?type=LOST|FOUND pre-selects the type). POST saves."""
    if request.method == 'POST':
        form = ItemReportForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.posted_by = request.user
            item.save()
            messages.success(request, 'Report posted. Check below for possible matches.')
            return redirect('item_detail', pk=item.pk)
    else:
        initial_type = request.GET.get('type', '').upper()
        if initial_type not in (ItemReport.LOST, ItemReport.FOUND):
            initial_type = ItemReport.LOST
        form = ItemReportForm(initial={'report_type': initial_type, 'date': date.today()})

    return render(request, 'items/create_item.html', {'form': form})


@login_required
def edit_item(request, pk):
    item = get_object_or_404(ItemReport, pk=pk)
    if item.posted_by != request.user:
        messages.error(request, 'You can only edit your own reports.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = ItemReportForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Changes saved.')
            return redirect('item_detail', pk=item.pk)
    else:
        form = ItemReportForm(instance=item)

    return render(request, 'items/edit_item.html', {'form': form, 'item': item})


@login_required
def delete_item(request, pk):
    item = get_object_or_404(ItemReport, pk=pk)
    if item.posted_by != request.user:
        messages.error(request, 'You can only delete your own reports.')
        return redirect('dashboard')

    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Report deleted.')
        return redirect('dashboard')

    return render(request, 'items/confirm_delete.html', {'item': item})


# ── Resolve (AJAX) ────────────────────────────────────────

@login_required
def resolve_item(request, pk):
    """AJAX: mark a report resolved. Owner or staff only. Returns JSON."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    item = get_object_or_404(ItemReport, pk=pk)
    if item.posted_by != request.user and not request.user.is_staff:
        return JsonResponse({'error': 'Only the owner can resolve this report.'}, status=403)
    if item.status == ItemReport.RESOLVED:
        return JsonResponse({'error': 'This report is already resolved.'}, status=400)

    item.mark_resolved()
    return JsonResponse({'success': True, 'new_status': 'Resolved'})


# ── Chat: start conversation ──────────────────────────────

@login_required
@require_POST
def start_chat(request, pk):
    """
    POST item/<pk>/chat/ → get_or_create Conversation for request.user, redirect to it.
    Rejects: own report, and NEW chats on resolved reports.
    """
    item = get_object_or_404(ItemReport.objects.select_related('posted_by'), pk=pk)

    if item.posted_by == request.user:
        messages.error(request, "You can't chat about your own report.")
        return redirect('item_detail', pk=pk)

    # Existing chats can always be re-opened; only block CREATING a new one on resolved
    existing = item.conversations.filter(participant=request.user).first()
    if existing:
        return redirect('chat_detail', pk=existing.pk)

    if not item.is_open:
        messages.info(request, 'This report is resolved. New chats cannot be started.')
        return redirect('item_detail', pk=pk)

    conv = Conversation.objects.create(item=item, participant=request.user)
    return redirect('chat_detail', pk=conv.pk)


# ── Chat: inbox ───────────────────────────────────────────

@login_required
def inbox(request):
    """
    My conversations — as participant OR as report owner — newest activity first.
    Shows report title/type, the other person's name, last-message preview,
    time, and unread count.
    """
    me = request.user

    # All conversations where I am involved
    convs = (
        Conversation.objects
        .filter(Q(participant=me) | Q(item__posted_by=me))
        .select_related('item', 'item__posted_by', 'participant')
        .prefetch_related('messages')
        .order_by('-updated_at')
    )

    inbox_data = []
    for conv in convs:
        msgs = list(conv.messages.all())
        last = msgs[-1] if msgs else None
        other = conv.other_user(me)
        unread = sum(1 for m in msgs if m.read_at is None and m.sender != me)
        inbox_data.append({
            'conv': conv,
            'other': other,
            'last': last,
            'unread': unread,
        })

    return render(request, 'items/inbox.html', {'inbox_data': inbox_data})


# ── Chat: detail (read) ───────────────────────────────────

@login_required
def chat_detail(request, pk):
    conv = _conversation_or_404(request, pk)
    _mark_incoming_read(conv, request.user)

    other = conv.other_user(request.user)
    msgs = list(conv.messages.select_related('sender').all())
    form = MessageForm()

    return render(request, 'items/chat.html', {
        'conv': conv,
        'other': other,
        'msgs': msgs,
        'form': form,
        'closed': not conv.item.is_open,
    })


# ── Chat: send message ────────────────────────────────────

@login_required
@require_POST
def send_message(request, pk):
    """
    POST chat/<pk>/send/ → save message, return JSON (or redirect if no JS).
    Throttled: max 30 messages/minute per user via Django cache.
    """
    conv = _conversation_or_404(request, pk)

    if not conv.item.is_open:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'This report is resolved. Chat is closed.'}, status=403)
        messages.error(request, 'This report is resolved. Chat is closed.')
        return redirect('chat_detail', pk=conv.pk)

    # Simple per-user rate limit: 30 messages per minute (atomic add, TTL set once)
    rate_key = f'chat_rate_{request.user.pk}'
    cache.add(rate_key, 0, 60)   # only sets if key absent — preserves existing TTL
    count = cache.incr(rate_key)
    if count > 30:
        err = 'You are sending messages too quickly. Please wait a moment.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': err}, status=429)
        messages.error(request, err)
        return redirect('chat_detail', pk=conv.pk)

    form = MessageForm(request.POST)
    if not form.is_valid():
        errors = '; '.join(e for field_errs in form.errors.values() for e in field_errs)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': errors}, status=400)
        for field_errs in form.errors.values():
            for e in field_errs:
                messages.error(request, e)
        return redirect('chat_detail', pk=conv.pk)

    msg = Message.objects.create(
        conversation=conv,
        sender=request.user,
        body=form.cleaned_data['body'],
    )
    conv.touch()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'id': msg.pk,
            'body': msg.body,
            'sender_id': msg.sender_id,
            'sender_name': _display_name(msg.sender),
            'ts': msg.created_at.isoformat(),
            'mine': True,
            'read': msg.read_at is not None,
        })

    return redirect('chat_detail', pk=conv.pk)


# ── Chat: poll for new messages ───────────────────────────

@login_required
def poll_chat(request, pk):
    """
    GET chat/<pk>/poll/?after=<last_message_id>
    Returns JSON with messages newer than `after` and a `closed` flag.
    Marks incoming messages as read.
    """
    conv = _conversation_or_404(request, pk)

    try:
        after_id = int(request.GET.get('after', 0))
    except (TypeError, ValueError):
        after_id = 0

    new_msgs = conv.messages.filter(pk__gt=after_id).select_related('sender')
    # Mark the other person's messages as read
    new_msgs.exclude(sender=request.user).filter(read_at__isnull=True).update(read_at=timezone.now())

    data = []
    for m in new_msgs:
        data.append({
            'id': m.pk,
            'body': m.body,
            'sender_id': m.sender_id,
            'sender_name': _display_name(m.sender),
            'ts': m.created_at.isoformat(),
            'mine': m.sender_id == request.user.id,
            'read': m.read_at is not None,
        })

    # Also tell the sender if their last message was read by the other side
    # (used for the "Seen" indicator in the UI)
    last_mine = conv.messages.filter(sender=request.user).order_by('-pk').first()
    seen = last_mine.read_at is not None if last_mine else False

    return JsonResponse({'messages': data, 'closed': not conv.item.is_open, 'seen': seen})


# ── My Reports ────────────────────────────────────────────

@login_required
def my_reports(request):
    # Annotate each item with its unread message count (messages FROM others in its conversations)
    me = request.user
    unread_sub = (
        Message.objects
        .filter(conversation__item=OuterRef('pk'), read_at__isnull=True)
        .exclude(sender=me)
        .values('conversation__item')
        .annotate(n=Count('pk'))
        .values('n')
    )
    items = (
        ItemReport.objects
        .filter(posted_by=me)
        .select_related('posted_by')
        .annotate(unread_messages=Subquery(unread_sub[:1]))
    )
    return render(request, 'items/my_reports.html', {'items': items})
