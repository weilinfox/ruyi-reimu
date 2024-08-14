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
                    status.update({d.name: auto_load(reimu_config.check_cache_status(d.name))})
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
        <body>
            <h1>ruyi-reimu 自动化测试调度程序</h1>
    '''

    # status
    page += '''
            <h2>版本测试&nbsp;v{}</h2>
            <table>
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
            <h2>版本历史</h2>
            <ul>
    ''' + his + '''
            </ul>
    '''

    # tail
    page += '''
            <p></p>
            <p></p>
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

    check_reimu()

    if request_path not in reimu_status.keys():
        return flask.redirect('/404')

    return request_path


if __name__ == "__main__":
    reimu_config.load()

    reimu_server.run(debug=True, host="0.0.0.0", port=4646)
