#!/usr/bin/env python
#-*- encoding:utf-8 -*-

from __future__ import absolute_import, unicode_literals
from flask import Flask, request, abort, render_template
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.enterprise.exceptions import InvalidCorpIdException
from wechatpy.enterprise import parse_message, create_reply
from wechatpy.enterprise.replies import ImageReply
# import redis
import requests
import json
import config
from zabbix import ZabbixGraph
from wechatpy.enterprise.client.api.media import WeChatMedia
from wechatpy.enterprise import WeChatClient

client = WeChatClient(config.CorpId, config.Secret)


TOKEN = config.TOKEN
EncodingAESKey = config.EncodingAESKey
CorpId = config.CorpId

app = Flask(__name__)

#图灵机器人
def talks_robot(msg, ispuid=False):
    api_url = 'http://www.tuling123.com/openapi/api'
    apikey = config.turing_key
    if ispuid:
        data = {'key': apikey,
                'info': msg.content,
                'userid': msg.source
                }
    else:
        data = {'key': apikey,
                'info': msg.content,
                }
    req = requests.post(api_url, data=data).text
    replys = json.loads(req)['text']
    return replys


@app.route('/wechat', methods=['GET', 'POST'])
def wechat():
    signature = request.args.get('msg_signature', '')
    timestamp = request.args.get('timestamp', '')
    nonce = request.args.get('nonce', '')

    crypto = WeChatCrypto(TOKEN, EncodingAESKey, CorpId)
    if request.method == 'GET':
        echo_str = request.args.get('echostr', '')
        try:
            echo_str = crypto.check_signature(
                signature,
                timestamp,
                nonce,
                echo_str
            )
        except InvalidSignatureException:
            abort(403)
        return echo_str
    else:
        try:
            msg = crypto.decrypt_message(
                request.data,
                signature,
                timestamp,
                nonce
            )
        except (InvalidSignatureException, InvalidCorpIdException):
            abort(403)
        msg = parse_message(msg)
        user_name = msg.source
        help_message = """
未识别的命令.目前已支持的命令为: 
!问题   : 获取当前存在的问题列表
!监控信息,[获取主机名]/[获取监控项]/
!监控信息,主机名(datanode01),监控项
...
"""
        if msg.type == 'text':
            message = msg.content
            if message == 'help':
                reply = create_reply(help_message, msg).render()
                res = crypto.encrypt_message(reply, nonce, timestamp)
                return res
            if message.find('!') == 0:
                #这里进入到命令匹配模式
                if "!问题" in message or "!获取问题" in message:
                    import time
                    zabbix = ZabbixGraph()
                    events = zabbix.get_cur_problems()
                    evt_str = "\n".join(["{:<20}{:<25}{}".format(e['eventid'], str(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(e['clock'])))), e['name']) for e in events])
                    reply = create_reply(evt_str, msg).render()
                    res = crypto.encrypt_message(reply, nonce, timestamp)
                    return res
                else:

                    if "!监控信息" in message:
                        zabbix = ZabbixGraph()
                        message_list = message.split(',')
                        if len(message_list) == 2:
                            message_c = message_list[1]
                            if "获取主机名" == message_c:
                                hosts = zabbix.get_hosts()
                                message = "\n".join(hosts)
                            if "获取监控项" == message_c:
                                hosts = zabbix.get_graphs(10257)
                                message = "\n".join(hosts)
                        elif len(message_list) == 3:
                            hostname = message_list[1]
                            item = message_list[2]
                            hostids = zabbix.get_host_id(hostname)
                            for h in hostids:
                                gids = zabbix.get_graph_id(h, item)
                                for gid in gids:
                                    values = {"graphid": gid}
                                    fpath = zabbix.GetGraph(values, config.TMP_DIR)
                                    print(fpath)
                                    with open(fpath, 'rb') as ff:
                                        resp = WeChatMedia(client=client).upload("image", ff)
                                        media_id = resp["media_id"]
                                        reply = ImageReply(media_id=media_id).render()
                                        res = crypto.encrypt_message(reply, nonce, timestamp)
                                    return res
                        else:
                            message = help_message
                    reply = create_reply(message, msg).render()
                    res = crypto.encrypt_message(reply, nonce, timestamp)
                    return res
            else:
                rep = talks_robot(msg)
                reply = create_reply(rep, msg).render()
                res = crypto.encrypt_message(reply, nonce, timestamp)
                return res
        return ''


if __name__ == '__main__':
    app.run('0.0.0.0', 5001, debug=False)
