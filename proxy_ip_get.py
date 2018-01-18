import subprocess
import requests
import bs4
import random
import time
from threading import Thread
import datetime 
import threadpool


class proxy_ip:
    available_ip = {}
    check_ips = {}
    is_running = False
    handler_thread = None
    available_ip_check_handler_thread = None
    run_model = None
    unavailable_ip = {}
    max_check_count = 3

    def __init__(self, run_model='normal'):
        # ip 存储方法 ip[ip] = [port,0,0]
        # ip为key,分别把次数，成功检测次数,失败检测次数存放在数组中
        self.available_ip = {}  # 可用IP
        self.check_ips = {}  # 待检查IP
        self.unavailable_ip = {}  # 不可用IP
        self.is_running = False  # 是否运行
        self.handler_thread = None
        self.available_ip_check_handler_thread = None
        self.run_model = run_model
        self.max_check_count = 3

    def get_proxies(self):
        ips = self.get_proxy_ip_port()
        if ips is None:
            return None
        ip_str = "{0}:{1}".format(ips[0], ips[1])
        return {
            'http': 'http://' + ip_str,
            'https': 'http://' + ip_str,
        }

    def get_proxy_ip_port(self):
        if len(self.available_ip) is 0:
            return None
        ip = random.choice(list(self.available_ip.keys()))
        port_array = self.available_ip.get(ip)
        if port_array is None:
            return None
        return [ip, port_array[0]]

    def remove_available_ip(self, ip):
        '''
            从可用ip中删除不可用ip
        :param ip:
        :return:
        '''
        if self.available_ip.get(ip) is not None:
            del self.available_ip[ip]

    def add_avaliable_ip(self, ip, port):
        '''
            增加一个可用ip
        :param ip:
        :param port:
        :return:
        '''
        self.available_ip[ip] = [port, 1, 0]

    def check_ip_port(self, ip, port):
        '''
            查询IP、代理是否可用
        :param ip:
        :param port:
        :return:
        '''
        try:

            ips = "{0}:{1}".format(ip, port)
            proxies = {
                'http': 'http://' + ips,
                'https': 'http://' + ips,
            }
            requestHeader = {
                'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36"}
            text = requests.get("http://ip.chinaz.com/getip.aspx", timeout=3, proxies=proxies,
                                headers=requestHeader).text

            self.show_logs('检测结果:{0}'.format(text))

            if ip in text:
                self.show_logs('{0}:{1}检测访问成功'.format(ip, port))
                return True
            return False


        except Exception as e:
            self.show_logs('{0}:{1}检测访问失败'.format(ip, port))
            self.show_logs(e)
        return False

    def get_url_ips(self, url):
        '''
            获取url对应的ip
        :param url:
        :return:
        '''
        try:
            requestHeader = {
                'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36"}
            ips = []
            html = requests.get(url, headers=requestHeader).text
            bs = bs4.BeautifulSoup(html, 'html5lib')
            all_tr = bs.select("table tr")
            for tr in all_tr:
                if tr.select_one(".country .fast") != None:
                    all_td = tr.select('td')
                    ips.append((all_td[1].text, all_td[2].text))

            self.show_logs('代理ip获取成功：{0}'.format(ips))
            return ips
        except Exception as e:
            print(e)
            return []

    def __handler_check_single_ip(self, ip):
        port_array = self.check_ips.get(ip)
        if port_array is not None:
            port = self.check_ips[ip][0]
            if self.check_ip_port(ip, port):
                self.add_avaliable_ip(ip, port)  # 增加到可用的IP列表
                del self.check_ips[ip]  # 从待检查IP进行查询
            else:
                old_ip_info = self.check_ips[ip]
                old_ip_info[2] = old_ip_info[2] + 1
                if old_ip_info[2] >= self.max_check_count:
                    self.unavailable_ip[ip] = old_ip_info
                    del self.check_ips[ip]
                else:
                    self.check_ips[ip] = old_ip_info

    def __get_check_ips(self):

        if len(self.check_ips) < 20:
            for index in range(1, 20):
                url = "http://www.xicidaili.com/nn/{0}".format(index)
                ips = self.get_url_ips(url)
                for ip_item in ips:
                    ip = ip_item[0]
                    port = ip_item[1]
                    # 只有未增加到ip的列表和检测不可用的才增加到待检测列表中
                    if self.check_ips.get(ip) is None and self.unavailable_ip.get(ip) is None and self.available_ip.get(
                            ip) is None:
                        self.check_ips[ip] = [port, 0, 0]
                        # check_ip_index = self.__ip_index(ip_item[0], self.check_ips)
                        # if check_ip_index is None:
                        #     self.check_ips.append([ip_item[0], ip_item[1], 0])
                    if len(self.check_ips) > 40:
                        return

    def __check_avaliable_ip(self):
        '''
            检测可用IP是否仍然是可用的
        :return:
        '''

        try:
            while True:
                keys = list(self.available_ip.keys())
                for ip in keys:
                    port_array = self.available_ip.get(ip)
                    if port_array is not None:
                        port = port_array[0]
                        if self.check_ip_port(ip, port) is True:
                            port_array[1] += 1
                            self.available_ip[ip] = port_array
                        else:
                            port_array[2] += 1
                            if port_array[2] > 3 and port_array[2] > port_array[1]:
                                self.unavailable_ip[ip] = port_array
                                del self.available_ip[ip]
                            else:
                                self.available_ip[ip] = port_array
                time.sleep(10)  # 10秒后再检测
        except Exception as e:
            self.show_logs('检测可用IP失败'.format(ip, port))
            self.show_logs(e)

    def __hander(self):
        '''
            开始处理，每15秒处理一次。
            1.先获取原始ip数
            2.对原始ip进行检查记数,如果原始ip可用则进行增加到可用ip中去，如果不可用则标记数+1
            3.清除原始ip中标记数超过指定次数的ip,同时在可用ip中也清除该ip
        :return:
        '''
        while True:
            self.show_logs('start handing...')
            self.__get_check_ips()
            self.show_logs('current check ip count:{0}'.format(len(self.check_ips)))
            keys = list(self.check_ips.keys())
            pool = threadpool.ThreadPool(10)
            pool_requests = threadpool.makeRequests(self.__handler_check_single_ip, keys)
            [pool.putRequest(req) for req in pool_requests]
            pool.wait()
            self.show_logs("{0}检测完成成功".format(datetime.datetime.now()))

            time.sleep(10)  # 10秒后再进行检测

    def show_logs(self, log):
        if self.run_model == 'debug':
            print('[{0}]—{1}'.format(datetime.datetime.now(), log))

    def start_hander(self):
        if self.is_running is True:
            self.show_logs('当前处理运行中...')
            return;
        self.handler_thread = Thread(target=self.__hander)
        self.handler_thread.setDaemon(True)
        self.handler_thread.start()

        self.available_ip_check_handler_thread = Thread(target=self.__check_avaliable_ip)
        self.available_ip_check_handler_thread.setDaemon(True)
        self.available_ip_check_handler_thread.start()  # start check 线程

        self.is_running = True

    def show_current_info(self):
        '''
        显示当前信息
        :return:
        '''
        print("可用IP:{0},{3},待检测ip:{1},{4},已经失效IP:{2},{5}".format(len(self.available_ip), len(self.check_ips),
                                                                 len(self.unavailable_ip), self.available_ip,
                                                                 self.check_ips, self.unavailable_ip))
        pass


if __name__ == "__main__":

    # lists = [[1, 2, 3], [3, 5, 5], [12, 3, 4]]
    # for item in lists:
    #     if item[2] < 5:
    #         del item
    # print(lists)
    # ip = proxy_ip(run_model='debug')
    ip = proxy_ip(run_model='release')
    # ips = ip.get_url_ips("http://www.xicidaili.com/nn")
    # for item in ips:
    #     print("{0}:{1}".format(item[0],item[1]))
    ip.start_hander()

    check_count = 0
    avaliable_count = 0
    while True:
        input('press any key contiune')
        ip.show_current_info()
        proxies_ip = ip.get_proxies()
        print("获取代理IP信息为：{0}".format(proxies_ip))
        try:
            requestHeader = {
                'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36"}
            text = requests.get("http://ip.chinaz.com/getip.aspx", timeout=5, proxies=proxies_ip,
                                headers=requestHeader).text
            print(text)
        except Exception as e:
            print(e)
            # ip = proxy_ip()
            # ips = ip.get_ips("http://www.xicidaili.com/nn")
            # print(ips)
            # # ips = [("122.72.32.72", 80), ("222.194.14.130", 808), ]
            # for item in ips:
            #     print(ip.check_ip_port(item[0], item[1]))
            # th = Thread(target=ip.loop_hander)
            # th.setDaemon(True)
            # th.start()
            # proxies = {
            #     'http': 'http://111.155.116.247:8123',
            #     'https': 'http://111.155.116.247:8123',
            # }
            # requestHeader = {
            #     'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36"}
            # text = requests.get("http://ip.chinaz.com", timeout=5, proxies=proxies, headers=requestHeader).text
            # bs = bs4.BeautifulSoup(text, 'html5lib')
            # print(text)
            # print(bs.select_one(".IpMRig-tit").text)
            # time.sleep(10)
            #
            # while True:
            #     print(ip.available_ip)
            #     remove_ip = input('input ips:')
            #     ip.remove_unavailable_ip(remove_ip)
            #     print(ip)
# proxies = {
#     'http': 'http://111.155.116.247:8123',
#     'https': 'http://111.155.116.247:8123',
# }
# requestHeader = {
#     'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36"}
# text = requests.get("http://ip.chinaz.com", timeout=5, proxies=proxies, headers=requestHeader).text
# bs = bs4.BeautifulSoup(text, 'html5lib')
# print(text)
# print(bs.select_one(".IpMRig-tit").text)
