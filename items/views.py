"""
items/views.py — View functions (the "V" in MVT)

All views except the login landing page require @login_required.
Ownership is always enforced on the server, never just hidden in the UI.
"""

from datetime import date

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import ClaimForm, ItemReportForm
from .matching import find_matches
from .models import Claim, ItemReport


# ── Helpers ───────────────────────────────────────────────

def _display_name(user):
    return user.get_full_name() or user.username


def _email(user, subject, body):
    """Best-effort notification; a mail failure must never break the request."""
    if user.email:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)


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

    ctx = {
        'item': item,
        'is_owner': is_owner,
        'matches': find_matches(item) if item.is_open else [],
    }
    if is_owner:
        ctx['claims'] = item.claims.select_related('claimant')
    else:
        ctx['my_claim'] = item.claims.filter(claimant=request.user).first()
        ctx['claim_form'] = ClaimForm()
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
    """AJAX: mark a report resolved. Owner only. Returns JSON."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    item = get_object_or_404(ItemReport, pk=pk)
    if item.posted_by != request.user:
        return JsonResponse({'error': 'Only the owner can resolve this report.'}, status=403)
    if item.status == ItemReport.RESOLVED:
        return JsonResponse({'error': 'This report is already resolved.'}, status=400)

    item.mark_resolved()
    return JsonResponse({'success': True, 'new_status': 'Resolved'})


# ── Claims ("I found this" / "This is mine") ──────────────

@login_required
@require_POST
def claim_item(request, pk):
    item = get_object_or_404(ItemReport.objects.select_related('posted_by'), pk=pk)

    if item.posted_by == request.user:
        messages.error(request, "You can't send a message to yourself.")
        return redirect('item_detail', pk=pk)
    if not item.is_open:
        messages.error(request, 'This report is already resolved.')
        return redirect('item_detail', pk=pk)
    if item.claims.filter(claimant=request.user).exists():
        messages.info(request, 'You have already sent a message about this report.')
        return redirect('item_detail', pk=pk)

    form = ClaimForm(request.POST)
    if not form.is_valid():
        for error in form.errors.get('message', []):
            messages.error(request, error)
        return redirect('item_detail', pk=pk)

    claim = form.save(commit=False)
    claim.item, claim.claimant = item, request.user
    claim.save()

    link = request.build_absolute_uri(reverse('item_detail', args=[item.pk]))
    _email(
        item.posted_by,
        f'New message about "{item.title}"',
        f'{_display_name(request.user)} ({request.user.email}) wrote about your '
        f'{item.get_report_type_display().lower()} report "{item.title}":\n\n'
        f'{claim.message}\n\nReply or respond here: {link}\n',
    )
    messages.success(request, f'Message sent to {_display_name(item.posted_by)}.')
    return redirect('item_detail', pk=pk)


@login_required
@require_POST
def respond_claim(request, pk, action):
    """Owner accepts or declines a message. Accepting resolves the report."""
    claim = get_object_or_404(Claim.objects.select_related('item', 'claimant'), pk=pk)
    item = claim.item

    if item.posted_by != request.user:
        messages.error(request, 'Only the person who posted this report can respond.')
        return redirect('dashboard')
    if claim.status != Claim.PENDING:
        messages.info(request, 'You have already responded to that message.')
        return redirect('item_detail', pk=item.pk)

    link = request.build_absolute_uri(reverse('item_detail', args=[item.pk]))
    if action == 'accept':
        with transaction.atomic():
            claim.status = Claim.ACCEPTED
            claim.save(update_fields=['status'])
            item.claims.filter(status=Claim.PENDING).exclude(pk=claim.pk).update(status=Claim.REJECTED)
            if item.is_open:
                item.mark_resolved()
        _email(
            claim.claimant,
            f'Your message about "{item.title}" was accepted',
            f'{_display_name(request.user)} accepted your message. You can reach them at '
            f'{request.user.email}.\n\n{link}\n',
        )
        messages.success(request, f'Accepted. The report is now resolved — you can reach {_display_name(claim.claimant)} at {claim.claimant.email}.')
    else:
        claim.status = Claim.REJECTED
        claim.save(update_fields=['status'])
        _email(
            claim.claimant,
            f'Update on "{item.title}"',
            f'{_display_name(request.user)} declined your message about "{item.title}".\n\n{link}\n',
        )
        messages.success(request, 'Message declined.')
    return redirect('item_detail', pk=item.pk)


# ── My Reports ────────────────────────────────────────────

@login_required
def my_reports(request):
    items = (
        ItemReport.objects
        .filter(posted_by=request.user)
        .select_related('posted_by')
        .annotate(pending_claims=Count('claims', filter=Q(claims__status=Claim.PENDING)))
    )
    claims = Claim.objects.filter(claimant=request.user).select_related('item', 'item__posted_by')
    return render(request, 'items/my_reports.html', {
        'items': items,
        'claims': claims,
        'tab': 'claims' if request.GET.get('tab') == 'claims' else 'reports',
    })
