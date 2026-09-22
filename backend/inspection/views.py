from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
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
    return render(
        request,
        "detail.html",
        {"row": row, "can_write": _can_write(request.user)},
    )


@login_required
@require_http_methods(["GET", "POST"])
def create_view(request):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可登记灯光巡检")
    error = ""
    if request.method == "POST":
        row = _save_inspection(request)
        if row is not None:
            return redirect("detail", pk=row.pk)
        error = "请填编号和三项数值"
    return render(request, "form.html", {"error": error})


@login_required
@require_http_methods(["GET", "POST"])
def retest_create_view(request, pk):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可开复测单")
    origin = get_object_or_404(Inspection, pk=pk)
    if origin.verdict != "不合格":
        return HttpResponseForbidden("仅不合格的记录可开复测单")
    error = ""
    if request.method == "POST":
        row = _save_inspection(request, origin=origin)
        if row is not None:
            return redirect("detail", pk=row.pk)
        error = "请填实测光强和方位偏差"
    return render(
        request,
        "retest_form.html",
        {"origin": origin, "error": error},
    )


@login_required
def chain_view(request):
    # 每条链以最早原单为根，复测单挂在其后，模板递归展开。
    roots = Inspection.objects.filter(origin__isnull=True).order_by("id")
    return render(request, "chain.html", {"roots": roots})


def _save_inspection(request, origin=None):
    """按提交的实测值当场判定并落单；origin 非空时开出的是复测单。"""
    try:
        measured = float(request.POST["measured_cd"])
        bearing = float(request.POST["bearing_error_deg"])
        if origin is None:
            required = float(request.POST["required_cd"])
            code = request.POST["aid_code"].strip()
            if not code:
                raise ValueError("empty")
        else:
            # 复测沿用所依原单的灯号与要求光强，主键记在 origin 上。
            required = origin.required_cd
            code = origin.aid_code
    except (KeyError, ValueError):
        return None
    verdict, note = judge(measured, required, bearing)
    return Inspection.objects.create(
        aid_code=code,
        measured_cd=measured,
        required_cd=required,
        bearing_error_deg=bearing,
        verdict=verdict,
        note=note,
        created_by=request.user.username,
        origin=origin,
    )
