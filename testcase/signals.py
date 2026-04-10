from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from project.models import ReleasePlan
from testcase.models import TestCase, TestCaseStep, TestCaseVersion


@receiver(post_save, sender=TestCase)
def testcase_post_save_rag(sender, instance, **kwargs):
    from assistant.rag_chroma import index_test_case

    index_test_case(instance.pk)


@receiver(post_save, sender=TestCaseStep)
def testcase_step_post_save_rag(sender, instance, **kwargs):
    from assistant.rag_chroma import index_test_case

    if instance.testcase_id:
        index_test_case(instance.testcase_id)


@receiver(post_delete, sender=TestCaseStep)
def testcase_step_post_delete_rag(sender, instance, **kwargs):
    from assistant.rag_chroma import index_test_case

    if instance.testcase_id:
        index_test_case(instance.testcase_id)


@receiver(post_delete, sender=TestCase)
def testcase_post_delete_rag(sender, instance, **kwargs):
    from assistant.rag_chroma import delete_test_case_embedding

    delete_test_case_embedding(instance.pk)


@receiver(m2m_changed, sender=ReleasePlan.test_cases.through)
def release_plan_case_snapshot(sender, instance, action, pk_set, **kwargs):
    """
    用例关联到发布计划时自动生成版本快照。
    """
    if action != "post_add" or not pk_set:
        return
    cases = TestCase.all_objects.filter(pk__in=pk_set)
    for case in cases:
        TestCaseVersion.create_version(test_case=case, release_plan=instance)
