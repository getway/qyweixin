#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" 
@author:xiaomao 
@license: Kxl
@file: zabbixV2.py 
@time: 2019/1/28 6:25 PM
@software: PyCharm 

# code is far away from bugs with the god animal protecting
    I love animals. They taste delicious.
              ┏┓      ┏┓
            ┏┛┻━━━┛┻┓
            ┃      ☃      ┃
            ┃  ┳┛  ┗┳  ┃
            ┃      ┻      ┃
            ┗━┓      ┏━┛
                ┃      ┗━━━┓
                ┃  神兽保佑    ┣┓
                ┃　永无BUG！   ┏┛
                ┗┓┓┏━┳┓┏┛
                  ┃┫┫  ┃┫┫
                  ┗┻┛  ┗┻┛ 
"""

import requests
import json
import sys
import os
import config


class ZabbixGraph(object):

    def __init__(self):
        self.headers = {"Content-Type": "application/json-rpc"}
        self.url = config.ZABBIX_URL
        self.name = config.ZABBIX_USERNAME
        self.password = config.ZABBIX_PASSWD
        self.session = requests.Session()
        values = {"name": self.name, 'password': self.password, 'autologin': 1, "enter": 'Sign in'}
        self.session.post(self.url+'/index.php', values)
        self.api_url = "{}/api_jsonrpc.php".format(config.ZABBIX_URL)
        self.token = self.get_token()

    def GetGraph(self, values, image_dir):
        gr_url = "{}/chart2.php".format(self.url)
        key=values.keys()
        if "graphid" not in key:
            print(u"请确认是否输入graphid")
            sys.exit(1)
        #以下if 是给定默认值
        if "from" not in key:
            #默认为当前时间开始
            values["from"] = "now-30m"
        if "to" not in key:
            values['to'] = 'now'
        if "width" not in key:
            values["width"] = 400
        if "height" not in key:
            values["height"] = 100

        fname = os.path.join(image_dir, "%s.png" % (values["graphid"]))
        res = self.session.request('get', gr_url, values)
        with open(fname, 'wb') as f:
            f.write(res.content)
        return fname

    def get_cur_problems(self):
        """
        获取当前有哪些问题
        :return:
        """
        data = {
            "jsonrpc": "2.0",
            "method": "problem.get",
            "params": {
                "output": "extend",
                "selectAcknowledges": "extend",
                "selectTags": "extend",
                "recent": "true",
                "sortfield": ["eventid"],
                "sortorder": "DESC"
            },
            "id": 1,
            "auth": self.token
        }
        res = requests.post(self.api_url, json.dumps(data), headers=self.headers)
        res_data = json.loads(res.content)
        return res_data.get('result')

    def set_ack_event(self, eid, message="Problem resolved."):
        """
        确认问题
        :param eid: event_id
        :param message: 备注信息
        :return: true/false
        """
        data = {
            "jsonrpc": "2.0",
            "method": "event.acknowledge",
            "params": {
                "eventids": str(eid),
                "message": message,
                "action": 1
            },
            "id": 1,
            "auth": self.token
        }
        res = requests.post(self.api_url, json.dumps(data), headers=self.headers)
        res_data = json.loads(res.content)
        if res_data.get('result'):
            return True
        else:
            return False

    def get_token(self):
        data = {
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {
                "user": self.name,
                "password": self.password,
            },
            "id": 1,
            "auth": None
        }
        import json
        res = requests.post(self.api_url, json.dumps(data), headers=self.headers)
        res_data = json.loads(res.content)
        return res_data.get('result')

    def get_hosts(self):
        data = {
            "jsonrpc": "2.0",
            "method": "host.get",
            "params": {
                "output": [
                    "hostid",
                    "host",
                ],
                "selectInterfaces": [
                    "ip"
                ]
            },
            "id": 2,
            "auth": self.token
        }
        res = requests.post(self.api_url, json.dumps(data), headers=self.headers)
        res_data = json.loads(res.content)
        return [host['host'] for host in res_data['result']]

    def get_graphs(self, hostid):
        data = {
            "jsonrpc": "2.0",
            "method": "graph.get",
            "params": {
                "output": "extend",
                "hostids": hostid,
                "sortfield": "name"
            },
            "id": 1,
            "auth": self.token
        }
        res = requests.post(self.api_url, json.dumps(data), headers=self.headers)
        res_data = json.loads(res.content)
        return [graph['name'] for graph in res_data['result']]

    def get_host_id(self, name=""):
        data = {
            "jsonrpc": "2.0",
            "method": "host.get",
            "params": {
                "output": [
                    "hostid",
                    "host"
                ],
                "selectInterfaces": [
                    "interfaceid",
                    "ip"
                ]
            },
            "id": 2,
            "auth": self.token
        }
        res = requests.post(self.api_url, json.dumps(data), headers=self.headers)
        res_data = json.loads(res.content)
        ret = []
        if name:
            hosts_list = res_data["result"]
            ret = [host['hostid'] for host in hosts_list if name.lower() in host['host'].lower() or name == host["interfaces"][0]['ip']]
        return ret

    def get_graph_id(self, hostid, name=""):
        data = {
            "jsonrpc": "2.0",
            "method": "graph.get",
            "params": {
                "output": "extend",
                "hostids": hostid,
                "sortfield": "name"
            },
            "id": 1,
            "auth": self.token
        }
        res = requests.post(self.api_url, json.dumps(data), headers=self.headers)
        res_data = json.loads(res.content)
        ret = []
        if res_data['result']:
            graph_list = res_data['result']

            if name:
                ret = [graph['graphid'] for graph in graph_list if name.lower() in graph['name'].lower()]
        return ret


if __name__ == '__main__':
    #用于图片存放的目录
    image_dir="/tmp"

    b = ZabbixGraph()
    events = b.get_cur_problems()
    print(events)
