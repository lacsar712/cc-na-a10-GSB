from django.db import models


class Inspection(models.Model):
    aid_code = models.CharField("航标编号", max_length=40)
    measured_cd = models.FloatField("实测光强")
    required_cd = models.FloatField("要求光强")
    bearing_error_deg = models.FloatField("方位偏差")
    verdict = models.CharField("结论", max_length=20)
    note = models.CharField("说明", max_length=200)
    created_by = models.CharField("登记人", max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    origin = models.ForeignKey(
        "self",
        verbose_name="所依原单",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="retests",
    )

    class Meta:
        ordering = ["-id"]

    @property
    def is_retest(self) -> bool:
        return self.origin_id is not None

    @property
    def retests_chronological(self):
        # 链页按开单时间从旧到新展开
        return self.retests.order_by("id")
