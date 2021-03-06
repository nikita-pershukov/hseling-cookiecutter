import os
from base64 import b64decode, b64encode

from django.shortcuts import render
from django.http import HttpResponseRedirect, JsonResponse
from django import forms

import requests
{% if not cookiecutter.rest %}
from jsonrpcclient import request as jsonrpcrequest
{% endif %}

HSE_API_ROOT = os.environ.get("HSELING_API_ROOT", "http://hse-api-web/")
{% if not cookiecutter.rest %}
HSE_RPC_ROOT = HSE_API_ROOT + 'rpc/'
{% endif %}
PROJECT_TITLE = "{{cookiecutter.application_name}}"


def web_index(request):
    return render(request, 'index.html',
                  context={"project_title": PROJECT_TITLE})


def web_main(request):
    return render(request, 'main.html',
                  context={"project_title": PROJECT_TITLE,
                           "status": request.GET.get('status')})


def web_status(request):
    task_id = request.GET.get('task_id')
    if task_id:
{% if cookiecutter.rest %}
        url = HSE_API_ROOT + "status/" + task_id
        content = requests.get(url)
        result = content.json()
        if result.get('status') == 'SUCCESS':
            content = requests.get(HSE_API_ROOT + 'files/' + result.get('result', [""])[0])
            result['raw_base64'] = b64encode(content.content).decode('utf-8')
{% else %}
        response = jsonrpcrequest(HSE_RPC_ROOT, "get_task_status", task_id)
        result = response.data.result
        if result.get('status') == 'SUCCESS':
            response = jsonrpcrequest(HSE_RPC_ROOT, "get_file", result.get('result', [""])[0])
            result['raw_base64'] = response.data.result.get("file_contents_base64", "")
{% endif %}
        return JsonResponse(result)
    return JsonResponse({"error": "No task id"})


def handle_uploaded_file(f):
{% if cookiecutter.rest %}
    files = {'file': f}
    url = HSE_API_ROOT + "upload"
    content = requests.post(url, files=files)
    file_id = content.json().get("file_id")

    if file_id:
        file_id = file_id[7:]
        url = HSE_API_ROOT + "process/" + file_id
        content = requests.get(url)

    else:
        raise Exception(content.json())

    return content.json().get('task_id')
{% else %}
    response = jsonrpcrequest(HSE_RPC_ROOT, "upload_file", f.name, b64encode(f.read()).decode('utf-8'))
    file_id = response.data.result.get("file_id")

    if file_id:
        file_id = file_id[7:]
        response = jsonrpcrequest(HSE_RPC_ROOT, "process_files", file_id)
        result = response.data.result

    else:
        raise Exception(response.data.messsage)
{% if cookiecutter.celery %}
    return result.get('task_id')
{%- else %}
    return result.get('result')
{%- endif %}
{% endif %}

class UploadFileForm(forms.Form):
    file = forms.FileField()


def web_upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
{%- if cookiecutter.celery or cookiecutter.rest %}
            task_id = handle_uploaded_file(request.FILES['file'])
            return HttpResponseRedirect('main?task_id=' + task_id)
{%- else %}
            file_ids = handle_uploaded_file(request.FILES['file'])
            response = jsonrpcrequest(HSE_RPC_ROOT, "get_file", file_ids[0])
            result = response.data.result
            return render(request, 'main.html', {"project_title": PROJECT_TITLE,
                                                 "filename": result.get("file_id"),
                                                 'result': b64decode(result.get('file_contents_base64')).decode('utf-8')})
{%- endif %}
    else:
        form = UploadFileForm()
    return render(request, 'main.html', {"project_title": PROJECT_TITLE,
                                         'form': form})
