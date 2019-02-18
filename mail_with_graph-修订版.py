#!/usr/bin/python
# coding:utf-8
# author:zhangrongjie
# website:http://icoder.top/
# url:https://github.com/zhangrj/zabbix-email-with-graph/
#
# import needed modules.
# pyzabbix is needed, see https://github.com/lukecyca/pyzabbix
# 
# software sendEmail-v1.56 is also needed, see the github. 
# because my company's email server doesn't support python's email module
# you can also change the code and replace it with pure python. It depends.

from pyzabbix import ZabbixAPI
import os
import argparse
import requests
import tempfile
import re
import urllib3


class Zabbix_Graph(object):
    """ Zabbix_Graph """

    def __init__(self, url=None, user=None, pwd=None, timeout=None):
        urllib3.disable_warnings()
        if timeout == None:
            self.timeout = 1
        else:
            self.timeout = timeout
        self.url = url
        self.user = user
        self.pwd = pwd
        self.cookies = {}
        self.zapi = None

    def _do_login(self):
        """ do_login """
        if self.url == None or self.user == None or self.pwd == None:
            print "url or user or u_pwd can not None"
            return None
        if self.zapi is not None:
            return self.zapi
        try:
            zapi = ZabbixAPI(self.url)
            zapi.session.verify = False
            zapi.login(self.user, self.pwd)
            self.cookies["zbx_sessionid"] = str(zapi.auth)
            self.zapi = zapi
            return zapi
        except Exception as e:
            print "auth failed:\t%s " % (e)
            return None

    def _is_can_graph(self, itemid=None):
        self.zapi = self._do_login()
        if self.zapi is None:
            print "zabbix login fail, self.zapi is None:"
            return False
        if itemid is not None:
            """
            0 - numeric float; 
            1 - character; 
            2 - log; 
            3 - numeric unsigned; 
            4 - text.
            """
            item_info = self.zapi.item.get(
                filter={"itemid": itemid}, output=["value_type"])
            if len(item_info) > 0:
                if item_info[0]["value_type"] in [u'0', u'3']:
                    return True
            else:
                print "get itemid fail"
        return False

    def get_graph(self, itemid=None):
        """ get_graph """
        if itemid == None:
            print "itemid can not None"
            return "ERROR"

        if self._is_can_graph(itemid=itemid) is False or self.zapi is None:
            print "itemid can't graph"
            return "ERROR"

        if len(re.findall('4.0', self.zapi.api_version())) == 1:
                graph_url = "%s/chart.php?from=now-1h&to=now&itemids[]=%s" % (
                    zbx_url, itemid)
        else:
            graph_url = "%s/chart.php?period=3600&itemids[]=%s" % (
                zbx_url, itemid)

        try:
            rq = requests.get(graph_url, cookies=self.cookies,
                              timeout=self.timeout, stream=True, verify=False)
            if rq.status_code == 200:
                imgpath = tempfile.mktemp()
                with open(imgpath, 'wb') as f:
                    for chunk in rq.iter_content(1024):
                        f.write(chunk)
                    return imgpath
            rq.close()
        except:
            return "ERROR"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='send mail to user for zabbix alerting')
    parser.add_argument('receiver', action="store",
                        help='user of the mail to send')
    parser.add_argument('subject', action="store",
                        help='subject of the mail')
    parser.add_argument('content', action="store",
                        help='content of the mail')
    parser.add_argument('withgraph', action="store", nargs='?',
                        default='None', help='The Zabbix Graph for mail')

    args = parser.parse_args()
    receiver = args.receiver
    subject = args.subject
    content = args.content
    withgraph = args.withgraph
    img = "ERROR"
    itemid = "0"

    #-----------------------------------------------------------------------------------#
    # Mail Server Configuration
    smtp_server = 'ip'
    smtp_port = 25
    smtp_user = 'example@example.com.cn'
    smtp_pwd = 'passwd'

    # Zabbix API, you should set it
    zbx_url = 'http://127.0.0.1/zabbix'
    #zbx_url = 'http://127.0.0.1'
    zbx_user = 'Admin'
    zbx_pwd = 'zabbix'
    #-----------------------------------------------------------------------------------#

    #get itemid from action
    split_itemid = re.split("ItemID:\s\d", content)
    pattern = re.compile(r'ItemID:.*')
    str_itemid = pattern.findall(content)
    if len(str_itemid) > 0:
        itemid = str_itemid[0].replace(" ", "").replace("ItemID:", "")

    #get graph from zabbix web
    if withgraph != "None" and itemid != "0":
        down_graph = Zabbix_Graph(
            url=zbx_url, user=zbx_user, pwd=zbx_pwd, timeout=3)
        if down_graph is not None:
            img = down_graph.get_graph(itemid=itemid)

    #send mail
    if img == "ERROR":
        os.system("/usr/local/bin/sendEmail -f "+ smtp_user + 
            " -t " + receiver + " -s " + smtp_server + ":" + smtp_port + " -u " + subject + 
            " -o message-content-type=html -o message-charset=utf-8 -xu " + 
            smtp_user + " -xp "+ smtp_pwd + " -m " + content) 
    else:
        open_img = open(img,'rb')  
        read_img = open_img.read()  
        open_img.close()  
        img_base64 = read_img.encode('base64')
        html_img = '''<br/><img src="data:image/png;base64,''' + img_base64 + '''">'''
        content += html_img
	with open('/usr/lib/zabbix/alertscripts/email.html','w') as content_txt:
	    content_txt.write(content)
        os.system("/usr/local/bin/sendEmail -f "+ smtp_user + 
            " -t " + receiver + " -s " + smtp_server + ":" + smtp_port + " -u " + subject + 
            " -o message-content-type=html -o message-charset=utf-8 -xu " + 
            smtp_user + " -xp "+ smtp_pwd + " -o message-file=/usr/lib/zabbix/alertscripts/email.html") 
