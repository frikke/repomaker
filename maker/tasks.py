import json
import logging

from background_task import background
from background_task.signals import task_failed
from django.core.exceptions import ObjectDoesNotExist
from django.dispatch import receiver
from django.utils import timezone

import maker.models


@background(schedule=timezone.now())
def update_repo(repo_id):
    try:
        repo = maker.models.repository.Repository.objects.get(pk=repo_id)
    except ObjectDoesNotExist as e:
        logging.warning('Repository does not exist anymore, dropping task. (%s)', e)
        return

    if repo.is_updating:
        return  # don't update the same repo concurrently
    repo.update_scheduled = False
    repo.is_updating = True
    repo.save()

    try:
        repo.update()
        repo.publish()
    finally:
        repo.is_updating = False
        repo.save()


@background(schedule=timezone.now())
def update_remote_repo(remote_repo_id):
    try:
        remote_repo = maker.models.remoterepository.RemoteRepository.objects.get(pk=remote_repo_id)
    except ObjectDoesNotExist as e:
        logging.warning('Remote Repository does not exist anymore, dropping task. (%s)', e)
        # TODO cancel repeating task
        return

    if remote_repo.is_updating:
        return  # don't update the same repo concurrently
    remote_repo.update_scheduled = False
    remote_repo.is_updating = True
    remote_repo.save()

    try:
        remote_repo.update_index()
    finally:
        remote_repo.is_updating = False
        remote_repo.save()


@background(schedule=timezone.now())
def download_apk(apk_id, url):
    try:
        apk = maker.models.apk.Apk.objects.get(pk=apk_id)
    except ObjectDoesNotExist as e:
        logging.warning('APK does not exist anymore, dropping task. (%s)', e)
        return

    if apk.is_downloading:
        return  # don't download the same apk concurrently
    apk.is_downloading = True
    apk.save()

    try:
        apk.download(url)
    finally:
        apk.is_downloading = False
        apk.save()


@background(schedule=timezone.now())
def download_remote_graphic_assets(app_id, remote_app_id):
    try:
        app = maker.models.app.App.objects.get(pk=app_id)
    except ObjectDoesNotExist as e:
        logging.warning('App does not exist anymore, dropping task. (%s)', e)
        return
    try:
        remote_app = maker.models.app.RemoteApp.objects.get(pk=remote_app_id)
    except ObjectDoesNotExist as e:
        logging.warning('Remote App does not exist anymore, dropping task. (%s)', e)
        return
    app.download_graphic_assets_from_remote_app(remote_app)


@background(schedule=timezone.now())
def download_remote_screenshot(screenshot_id, app_id):
    try:
        screenshot = maker.models.screenshot.RemoteScreenshot.objects.get(pk=screenshot_id)
    except ObjectDoesNotExist as e:
        logging.warning('Remote Screenshot does not exist anymore, dropping task. (%s)', e)
        return
    screenshot.download(app_id)


@receiver(task_failed)
def task_failed_receiver(**kwargs):
    task = kwargs['completed_task']

    if task.task_name == 'maker.tasks.update_remote_repo':
        # extract task parameters
        task_params = json.loads(task.task_params)
        params = task_params[0]
        remote_repo_id = params[0]

        # fetch and disable remote repository
        remote_repo = maker.models.remoterepository.RemoteRepository.objects.get(pk=remote_repo_id)
        remote_repo.disabled = True
        remote_repo.save()
