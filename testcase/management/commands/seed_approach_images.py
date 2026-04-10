from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile

from testcase.models import TestApproach, TestApproachImage


class Command(BaseCommand):
    help = "Seed initial TestApproachImage placeholders"

    def handle(self, *args, **options):
        approaches = list(TestApproach.objects.order_by("id")[:3])
        if not approaches:
            self.stdout.write(self.style.WARNING("No TestApproach records found; skip seeding."))
            return

        # 如果已经有图片则不重复创建（避免每次运行都刷数据）
        total_images = TestApproachImage.objects.count()
        if total_images > 0:
            self.stdout.write(self.style.SUCCESS(f"TestApproachImage already exists: {total_images}, skip."))
            return

        # 动态生成几张简单占位图
        from PIL import Image, ImageDraw
        import io

        colors = [
            ("#1677ff", "#69b1ff", "A"),
            ("#13c2c2", "#36cfc9", "B"),
            ("#faad14", "#ffd666", "C"),
            ("#ff4d4f", "#ff7875", "D"),
        ]

        for app in approaches:
            for idx in range(2):  # 每个方案 2 张
                c1, c2, text = colors[(app.id + idx) % len(colors)]
                img = Image.new("RGBA", (720, 360), c1)
                draw = ImageDraw.Draw(img)
                # 顶部透明渐变条
                draw.rectangle([0, 0, 720, 64], fill=c2)
                # 文字
                draw.text((30, 110), f"{app.scheme_name[:10]}...", fill="white")
                draw.text((30, 210), f"Seed {text}", fill="white")

                buf = io.BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)

                filename = f"seed_{app.id}_{idx}.png"
                created = TestApproachImage.objects.create(
                    approach=app,
                    image=ContentFile(buf.read(), name=filename),
                    sort_order=idx + 1,
                )

            # 兼容 cover_image
            first = app.images.all().order_by("sort_order", "-create_time").first()
            if first and first.image and not app.cover_image:
                app.cover_image = first.image.url
                app.save(update_fields=["cover_image"])

        self.stdout.write(self.style.SUCCESS("Seed TestApproachImage finished."))

