#!/usr/bin/env python3

import flask
import time

from threading import Lock

from config.loader import reimu_config
from utils.auto_loader import auto_load

reimu_server = flask.Flask(__name__)

reimu_cache = {}
reimu_status = {}

last_check = 0.0
error_info = ""
on_check = Lock()
on_error = False


def check_reimu():
    global reimu_cache
    global reimu_status
    global last_check
    global error_info
    global on_check
    global on_error

    if time.time() - last_check > 10 and on_check.acquire(blocking=False):
        try:
            cache = {}
            status = auto_load(reimu_config.check_cache_status())
            for d in reimu_config.cache_dir.iterdir():
                if d.name == "0.0.0":
                    continue
                if d.is_dir() and reimu_config.check_cache_status(d.name).exists():
                    cache.update({d.name: auto_load(reimu_config.check_cache_status(d.name))})
            reimu_cache, reimu_status = cache, status
        except Exception as e:
            on_error = True
            error_info = str(e)
        else:
            on_error = False

        last_check = time.time()
        on_check.release()


@reimu_server.route("/")
def reimu_index():
    global reimu_cache
    global reimu_status

    check_reimu()

    page = '''
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8" />
            <meta http-equiv="refresh" content="30" />
            <title>ruyi-reimu 自动化测试调度程序</title>
        </head>
        <body>
            <h1>ruyi-reimu 自动化测试调度程序</h1>
    '''

    # status
    page += '''
            <h2>版本测试&nbsp;v{}</h2>
            <table border="1">
                <thead>
                    <tr>
                        <th>开始时间</th>
                        <th>测试状态</th>
                        <th>测试完成</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>{}</td>
                        <td>{}</td>
                        <td>{}</td>
                    </tr>
                </tbody>
            </table>
    '''.format(reimu_status["version"], reimu_status["date"],
               "Running" if reimu_status["testing"] else "Idle", reimu_status["tested"])

    # history
    his = ""
    for k in reimu_cache.keys():
        his += '<li><a href="/{0}" target="_blank">{0}</a></li>\n'.format(k)

    page += '''
            <h2>测试详情</h2>
            <ul>
    ''' + his + '''
            </ul>
    '''

    # tail
    page += '''
            <p>&nbsp;</p>
            <p>&nbsp;</p>
            <footer>
                <p>Copyright &copy; 2023-2024 桜風の狐</p>
            </footer>
        </body>
    </html>
    '''

    return page


@reimu_server.route("/<path:request_path>")
def reimu_sub(request_path: str):
    global reimu_status
    global reimu_cache

    check_reimu()

    # 404
    if request_path not in reimu_cache.keys():
        return '''
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8">
            <title>404</title>
        </head>
        <body>
            <h1>404</h1>
            <h2>咱也不知道怎么说，反正就是没找到</h2>
        </body>
    </html>''', 404

    # make page
    headers = ""
    if reimu_status["version"] == request_path and (reimu_status["testing"] or not reimu_status["tested"]):
        headers += '''
            <meta http-equiv="refresh" content="30" />
        '''

    page = '''
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8" />
            <title>ruyi-reimu 测试详情 v{0}</title>
            {1}
        </head>
        <body>
            <h1>测试详情 v{0}</h1>
    '''.format(request_path, headers)

    # testing
    if reimu_status["version"] == request_path:
        page += '''
            <h2>测试状态</h2>
            <table border="1">
                <thead>
                    <tr>
                        <th>开始时间</th>
                        <th>测试状态</th>
                        <th>测试完成</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>{}</td>
                        <td>{}</td>
                        <td>{}</td>
                    </tr>
                </tbody>
            </table>
        '''.format(reimu_status["date"], "Running" if reimu_status["testing"] else "Idle", reimu_status["tested"])

    # tested info
    show_tested_info = {}
    for it in reimu_cache[request_path]['test_platforms'].items():
        # agent_label
        agent_label = ""
        for lb in it[1]["labels"]:
            agent_label += lb + ",&nbsp;"
        show_tested_info[it[0]] = {"agent_label": agent_label[:-7], "reimu_label": "",
                                   "jobs": [{"url": "", "status": "-"}]}
        # reimu_label
    for pl in reimu_cache[request_path]['queued_platforms']:
        show_tested_info[pl]["reimu_label"] += "QUEUED,&nbsp;"
    for pl in reimu_cache[request_path]['configured_platforms']:
        show_tested_info[pl[0]]["reimu_label"] += "CONFIGURED,&nbsp;"
    for pl in reimu_cache[request_path]['testing_platforms']:
        show_tested_info[pl]["reimu_label"] += "TESTING,&nbsp;"
    for pl in reimu_cache[request_path]['tested_platforms']:
        show_tested_info[pl]["reimu_label"] += "TESTED,&nbsp;"
    for pv in show_tested_info.items():
        if pv[1]["reimu_label"] == "" and pv[0] in reimu_cache[request_path]["retest_info"]:
            pv[1]["reimu_label"] = "BLOCKED,&nbsp;"
        pv[1]["reimu_label"] = pv[1]["reimu_label"][:-7]
    for it in reimu_cache[request_path]["tested_info"].items():
        # tested_info
        show_tested_info[it[0]]["jobs"] = it[1]

    # gen tested info html
    status_body = ""
    for it in show_tested_info.items():
        reimu_label_style = ""
        if it[1]["reimu_label"] == "TESTED":
            reimu_label_style = ' style="color:green"'
        elif it[1]["reimu_label"] == "TESTING":
            reimu_label_style = ' style="color:grey"'
        elif it[1]["reimu_label"] == "CONFIGURED":
            reimu_label_style = ' style="color:grey"'
        elif it[1]["reimu_label"] == "QUEUED":
            reimu_label_style = ' style="color:burlywood"'
        elif it[1]["reimu_label"] == "BLOCKED":
            reimu_label_style = ' style="color:red"'
        status_single = ""
        status_body += '''
                    <tr>
                        <td rowspan="{0}">{1}</td>
                        <td rowspan="{0}">{2}</td>
                        <td rowspan="{0}"{4}>{3}</td>
        '''.format(len(it[1]["jobs"]), it[0], it[1]["agent_label"], it[1]["reimu_label"], reimu_label_style)
        for job in it[1]["jobs"]:
            if status_single:
                status_single = '''
                    <tr>
                        <td><a href="{0}" target="_blank">{0}</a></td>
                        <td{2}>{1}</td>
                    </tr>
                '''
            else:
                status_single = '''
                        <td><a href="{0}" target="_blank">{0}</a></td>
                        <td{2}>{1}</td>
                    </tr>
                '''
            style = ""
            if job["status"] == "SUCCESS":
                style = ' style="color:green"'
            elif job["status"] == "TESTING":
                style = ' style="color:gray"'
            elif job["status"] == "FAILURE":
                style = ' style="color:red"'
            status_body += status_single.format(job["url"], job["status"], style)

    page += '''
            <h2>详细信息</h2>
            <table border="1">
                <thead>
                    <tr>
                        <th>测试平台</th>
                        <th>测试平台标志</th>
                        <th>测试过程标志</th>
                        <th>进程</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody>
    ''' + status_body + '''
                </tbody>
            </table>
    '''
    page += '''
            <p>共计&nbsp;{}&nbsp;个测试平台</p>
    '''.format(len(show_tested_info))

    # tail
    page += '''
            <p>&nbsp;</p>
            <p><a href="/">←回到首页</a></p>
            <p>&nbsp;</p>
            <footer>
                <p>Copyright &copy; 2023-2024 桜風の狐</p>
            </footer>
        </body>
    </html>
    '''

    return page


if __name__ == "__main__":
    reimu_config.load()

    reimu_server.run(debug=True, host="0.0.0.0", port=4646)
