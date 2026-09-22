from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from inspection.models import Inspection
from inspection.rules import judge


def _can_write(user) -> bool:
    return user.groups.filter(name="inspector").exists()


def health(_request):
    from django.http import JsonResponse

    return JsonResponse({"status": "ok", "service": "nav-aid-inspection"})


@require_http_methods(["GET", "POST"])
def login_view(request):
    from django.contrib.auth import authenticate, login

    error = ""
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", "").strip(),
            password=request.POST.get("password", ""),
        )
        if user is None:
            error = "用户名或密码错误"
        else:
            login(request, user)
            return redirect("list")
    return render(request, "login.html", {"error": error})


def logout_view(request):
    from django.contrib.auth import logout

    logout(request)
    return redirect("login")


@login_required
def list_view(request):
    rows = Inspection.objects.all()
    return render(request, "list.html", {"rows": rows, "can_write": _can_write(request.user)})


@login_required
def detail_view(request, pk):
    row = get_object_or_404(Inspection, pk=pk)
    retests = row.retests.order_by("id")
    return render(request, "detail.html", {"row": row, "retests": retests})


@login_required
@require_http_methods(["GET", "POST"])
def create_view(request):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可登记灯光巡检")
    error = ""
    if request.method == "POST":
        try:
            measured = float(request.POST["measured_cd"])
            required = float(request.POST["required_cd"])
            bearing = float(request.POST["bearing_error_deg"])
            code = request.POST["aid_code"].strip()
            if not code:
                raise ValueError("empty")
        except (KeyError, ValueError):
            error = "请填编号和三项数值"
        else:
            verdict, note = judge(measured, required, bearing)
            row = Inspection.objects.create(
                aid_code=code,
                measured_cd=measured,
                required_cd=required,
                bearing_error_deg=bearing,
                verdict=verdict,
                note=note,
                created_by=request.user.username,
            )
            return redirect("detail", pk=row.pk)
    return render(request, "form.html", {"error": error})


@login_required
@require_http_methods(["GET", "POST"])
def retest_create_view(request, pk):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可开复测")
    origin = get_object_or_404(Inspection, pk=pk)
    if origin.verdict != "不合格":
        return HttpResponseBadRequest("仅不合格记录可开复测")
    root = origin.retest_of or origin
    error = ""
    if request.method == "POST":
        try:
            measured = float(request.POST["measured_cd"])
            required = float(request.POST["required_cd"])
            bearing = float(request.POST["bearing_error_deg"])
        except (KeyError, ValueError):
            error = "请填三项数值"
        else:
            verdict, note = judge(measured, required, bearing)
            row = Inspection.objects.create(
                aid_code=root.aid_code,
                measured_cd=measured,
                required_cd=required,
                bearing_error_deg=bearing,
                verdict=verdict,
                note=note,
                retest_of=root,
                created_by=request.user.username,
            )
            return redirect("detail", pk=row.pk)
    return render(request, "retest_form.html", {"error": error, "root": root})


@login_required
def chain_view(request):
    roots = (
        Inspection.objects.filter(retest_of__isnull=True, retests__isnull=False)
        .distinct()
        .order_by("id")
    )
    chains = [(root, list(root.retests.order_by("id"))) for root in roots]
    return render(request, "chain.html", {"chains": chains})
