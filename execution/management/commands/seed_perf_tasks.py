from django.core.management.base import BaseCommand

from execution.models import PerfTask


class Command(BaseCommand):
    help = "若性能任务表为空，则插入若干条演示数据（可重复执行，已有数据则跳过）。"

    def handle(self, *args, **options):
        if PerfTask.objects.filter(is_deleted=False).exists():
            self.stdout.write(self.style.WARNING("已有性能任务，跳过种子数据。"))
            return

        demos = [
            {
                "task_id": "PT-1001",
                "task_name": "登录接口压测",
                "scenario": PerfTask.SCENARIO_JMETER,
                "concurrency": 200,
                "duration": "15m",
                "status": PerfTask.STATUS_RUNNING,
                "executor": "张三",
            },
            {
                "task_id": "PT-1002",
                "task_name": "订单创建峰值测试",
                "scenario": PerfTask.SCENARIO_LOCUST,
                "concurrency": 500,
                "duration": "30m",
                "status": PerfTask.STATUS_COMPLETED,
                "executor": "李四",
            },
            {
                "task_id": "PT-1003",
                "task_name": "商品查询稳定性测试",
                "scenario": PerfTask.SCENARIO_JMETER,
                "concurrency": 300,
                "duration": "20m",
                "status": PerfTask.STATUS_FAILED,
                "executor": "王五",
            },
            {
                "task_id": "PT-1004",
                "task_name": "支付回调并发测试",
                "scenario": PerfTask.SCENARIO_LOCUST,
                "concurrency": 150,
                "duration": "10m",
                "status": PerfTask.STATUS_COMPLETED,
                "executor": "赵六",
            },
            {
                "task_id": "PT-1005",
                "task_name": "秒杀活动压测",
                "scenario": PerfTask.SCENARIO_JMETER,
                "concurrency": 1000,
                "duration": "45m",
                "status": PerfTask.STATUS_RUNNING,
                "executor": "陈晨",
            },
            {
                "task_id": "PT-1006",
                "task_name": "用户中心接口回归压测",
                "scenario": PerfTask.SCENARIO_LOCUST,
                "concurrency": 250,
                "duration": "18m",
                "status": PerfTask.STATUS_FAILED,
                "executor": "周宁",
            },
        ]
        for row in demos:
            PerfTask.objects.create(**row)
        self.stdout.write(self.style.SUCCESS(f"已创建 {len(demos)} 条性能任务演示数据。"))
