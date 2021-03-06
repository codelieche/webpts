# -*- coding:utf-8 -*-
from datetime import datetime

from django.shortcuts import get_object_or_404
from django.views.generic import View
from django.http import JsonResponse

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from utils.mixins import CsrfExemptMixin
from tcase.models import Execute
from tresult.models import Detail, Summary, StatsCSV, Log
from tresult.serializers import DetailSerializer, StatsCSVSerializer,\
    LogSerializer
from tresult.serializers import SummarySerializer


@api_view(['GET', 'POST'])
def execute_detail(request, pk):
    """
    获取execute的结果
    """
    execute = get_object_or_404(Execute, pk=pk)
    if request.method == 'GET':
        detail_list = Detail.objects.filter(execute=execute)
        serializer = DetailSerializer(detail_list, many=True)
        return Response(serializer.data)

    elif request.method == "POST":
        # 添加execute结果的detail
        data = request.data
        # data['execute'] = pk
        detail_obj = DetailSerializer(data=data)
        if detail_obj.is_valid():
            detail_obj.save()
            return Response(detail_obj.data)
        else:
            print(request.data)
            print(detail_obj)

            return Response(detail_obj.errors,
                            status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def execute_summary(request, pk):
    """
    获取执行摘要
    :param request:
    :param pk: 执行测试execute的id
    :return:
    """
    try:
        execute = Execute.objects.get(pk=pk)
    except Execute.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        summary_list = Summary.objects.filter(execute=execute)
        # 如果列表为空，也会返回个[]
        serializer = SummarySerializer(summary_list, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        summary_obj = SummarySerializer(data=request.data)
        if summary_obj.is_valid():
            summary_obj.save()
            return Response(summary_obj.data)
        else:
            print(summary_obj.errors)
            return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def execute_stats(request, pk, type_):
    """
    执行结果统计
    :param request:
    :param pk: execute的id
    :param type_: 统计结果的类型：request, response, exception
    :return:
    """
    try:
        execute = Execute.objects.get(pk=pk)
    except Execute.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        # stats_obj = StatsCSV.objects.get(execute=execute, csv_type=type_)
        stats_obj = get_object_or_404(StatsCSV, execute=execute, csv_type=type_)
        serializer = StatsCSVSerializer(stats_obj)
        print(serializer.data)
        return Response(serializer.data)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def execute_add_stats(request):
    if request.method == 'POST':
        """
        POST添加统计信息
        """
        serializer = StatsCSVSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, template_name=None)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def execute_log(request, pk):
    """
    获取request日志
    :param request: request的GET可以传递type字段：info, start, end
    :param pk: execute的id
    :return:
    """
    # 先对pk进行判断是否存在execute
    execute = get_object_or_404(Execute, pk=pk)
    log_type = request.GET.get('type', '')
    log_list = Log.objects.filter(execute=execute)
    if log_type:
        log_list = log_list.filter(log_type=log_type)
        if log_type in ['info', 'error']:
            # 如果log_type是info、error就返回列表
            serializer = LogSerializer(log_list, many=True)
            return Response(serializer.data)

        elif log_type in ['start', 'stop']:
            # 如果是 start 或者 stop就只返回一条
            if log_list:
                serializer = LogSerializer(log_list[0])
                return Response(serializer.data)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
    else:
        # 没传入type的话 就返回全部的数据
        serializer = LogSerializer(log_list, many=True)
        return Response(serializer.data)


@api_view(['POST'])
def execute_add_log(request):
    """
    添加用例执行的日志信息
    """
    if request.method == 'POST':
        serializer = LogSerializer(data=request.data)
        log_type = request.POST.get('log_type', '')
        if log_type == 'stop':
            execute_id = request.POST.get('execute', '')
            if execute_id:
                execute = Execute.objects.get(pk=execute_id)
                execute.status = 'stoped'
                execute.time_end = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                execute.save()
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "success"})
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)


class ExecuteGetSummary(CsrfExemptMixin, View):
    """
    Execute运行中，post获取最新的summary
    """
    def post(self, request):
        execute_id = request.POST.get('execute_id', '')
        if execute_id:
            # 需要判断execute是否已经是停止了
            execute = get_object_or_404(Execute, pk=execute_id)
            if execute.status != 'running':
                content = {
                    'status': 'stop'
                }
                # 前台js根据stop来刷新下页面
                return JsonResponse(content)
            detail = Detail.objects.order_by('-id').filter(
                execute_id=execute_id).first()
            if detail:
                summary_dic = {
                    'status': 'success',
                    'user_count': detail.user_count,
                    'num_failures': detail.num_failures,
                    'time_avg': detail.time_avg,
                    'total_rps': detail.total_rps
                }
                return JsonResponse(summary_dic)
            else:
                # 如果获取到的detail是空，一般是程序正在运行
                return JsonResponse({'status': 'null'})
        else:
            return JsonResponse({'status': 'failure'}, status=400)
