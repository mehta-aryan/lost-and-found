"""
items/views.py — View functions (the "V" in MVT)

Each view handles a specific URL, processes data, and renders a template.
All views (except the login landing) require @login_required.

Performance: queries use select_related('posted_by') to avoid N+1 queries.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q

from .models import ItemReport
from .forms import ItemReportForm


# ── Public ────────────────────────────────────────────────

def login_view(request):
    """
    Landing page shown to unauthenticated users.
    If already logged in, redirect straight to the dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'items/login.html')


# ── Dashboard ─────────────────────────────────────────────

@login_required
def dashboard(request):
    """
    Main dashboard with two tabs: Lost Items and Found Items.
    Supports search filtering via GET parameter 'q'.
    Items are ordered: open first, then newest first (set in model Meta).
    select_related avoids extra DB queries for the posted_by user.
    """
    query = request.GET.get('q', '').strip()

    lost_items = (
        ItemReport.objects
        .filter(report_type=ItemReport.LOST)
        .select_related('posted_by')
    )
    found_items = (
        ItemReport.objects
        .filter(report_type=ItemReport.FOUND)
        .select_related('posted_by')
    )

    # Apply search filter if a query is provided
    if query:
        search_filter = Q(title__icontains=query) | Q(location__icontains=query)
        lost_items = lost_items.filter(search_filter)
        found_items = found_items.filter(search_filter)

    context = {
        'lost_items': lost_items,
        'found_items': found_items,
        'query': query,
    }
    return render(request, 'items/dashboard.html', context)


# ── Item Detail ───────────────────────────────────────────

@login_required
def item_detail(request, pk):
    """Display full details of a single item report."""
    item = get_object_or_404(
        ItemReport.objects.select_related('posted_by'), pk=pk
    )
    return render(request, 'items/item_detail.html', {'item': item})


# ── Create ────────────────────────────────────────────────

@login_required
def create_item(request):
    """
    Handle the item submission form.
    GET  → show the form (report_type can be pre-selected via ?type=LOST)
    POST → validate, set posted_by = current user, save, redirect
    """
    if request.method == 'POST':
        form = ItemReportForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)      # Don't save to DB yet
            item.posted_by = request.user       # Assign logged-in user as owner
            item.save()
            messages.success(request, 'Item reported successfully!')
            return redirect('dashboard')
    else:
        # Pre-select report type from the quick-add modal link
        initial_type = request.GET.get('type', '')
        form = ItemReportForm(initial={'report_type': initial_type})

    return render(request, 'items/create_item.html', {'form': form})


# ── Edit ──────────────────────────────────────────────────

@login_required
def edit_item(request, pk):
    """Allow the owner to edit their own item report."""
    item = get_object_or_404(ItemReport, pk=pk)

    # Server-side ownership check
    if item.posted_by != request.user:
        messages.error(request, 'You can only edit your own items.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = ItemReportForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Item updated successfully!')
            return redirect('item_detail', pk=item.pk)
    else:
        form = ItemReportForm(instance=item)

    return render(request, 'items/edit_item.html', {'form': form, 'item': item})


# ── Delete ────────────────────────────────────────────────

@login_required
def delete_item(request, pk):
    """Allow the owner to delete their own item report (POST only)."""
    item = get_object_or_404(ItemReport, pk=pk)

    # Server-side ownership check
    if item.posted_by != request.user:
        messages.error(request, 'You can only delete your own items.')
        return redirect('dashboard')

    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Item deleted successfully.')
        return redirect('dashboard')

    return render(request, 'items/confirm_delete.html', {'item': item})


# ── Resolve (AJAX) ────────────────────────────────────────

@login_required
def resolve_item(request, pk):
    """
    AJAX endpoint: mark an item as resolved.
    Only the owner can resolve their own item.
    Returns JSON so the frontend can update the badge without a page reload.
    Protected by @login_required + CSRF middleware.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    item = get_object_or_404(ItemReport, pk=pk)

    # Server-side ownership enforcement
    if item.posted_by != request.user:
        return JsonResponse(
            {'error': 'Only the owner can resolve this item.'}, status=403
        )

    if item.status == ItemReport.RESOLVED:
        return JsonResponse(
            {'error': 'This item is already resolved.'}, status=400
        )

    item.status = ItemReport.RESOLVED
    item.save(update_fields=['status'])   # Only update the status column
    return JsonResponse({'success': True, 'new_status': 'Resolved'})


# ── My Reports ────────────────────────────────────────────

@login_required
def my_reports(request):
    """Display all item reports created by the logged-in user."""
    items = (
        ItemReport.objects
        .filter(posted_by=request.user)
        .select_related('posted_by')
    )
    return render(request, 'items/my_reports.html', {'items': items})
