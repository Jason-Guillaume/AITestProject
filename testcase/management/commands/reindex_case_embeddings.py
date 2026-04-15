from django.core.management.base import BaseCommand

from testcase.models import TestCase


class Command(BaseCommand):
    help = (
        "为所有未删除的测试用例重建 Chroma 向量索引（需已安装 chromadb 且配置智谱 Key）"
    )

    def handle(self, *args, **options):
        from assistant.rag_chroma import CHROMADB_AVAILABLE, index_test_case

        if not CHROMADB_AVAILABLE:
            self.stderr.write(
                self.style.ERROR("未安装 chromadb，请执行: pip install chromadb")
            )
            return

        qs = TestCase.objects.filter(is_deleted=False)
        n = qs.count()
        self.stdout.write(f"共 {n} 条用例，开始索引…")
        ok = 0
        for tc in qs.iterator():
            if index_test_case(tc.pk):
                ok += 1
        self.stdout.write(
            self.style.SUCCESS(f"完成：成功写入/更新 {ok} 条（部分可能因无文本被跳过）")
        )
