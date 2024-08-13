# ruyi-reimu

RuyiSDK 测试调度程序

## reimu_check_latest.py

[packages-index](https://github.com/ruyisdk/packages-index/) board image 上游版本跟踪。

+ [x] packages-index 版本列表获取
+ [x] 上游镜像版本列表获取
+ [ ] 上游版本排序
+ [x] 版本比对
+ [x] issue 提交

### 执行逻辑

假设 packages-index 每个配置文件的 url 列表中，只有一个上游 url。维护一个上游 hostname 列表，从每个配置文件的 url 列表中找到这个上游链接，
从该上游 url 中获取版本，再从对应页面获取版本列表。

以 RevyOS 为例，在这个 url
 <https://mirror.iscas.ac.cn/revyos/extra/images/lpi4a/20240601/root-lpi4a-20240601_180941.ext4.zst> 中， 20240601 是版本，
故可以从 <https://mirror.iscas.ac.cn/revyos/extra/images/lpi4a/> 页面获取整个版本列表，使用正则过滤非版本号路径。

上游 hostname 列表维护在 [mirrors.toml](./mirrors.toml) 中，还是以 RevyOS 为例：

```toml
[["mirror.iscas.ac.cn"]]
repo="1"
repo_name="revyos"
version="-2"
version_match = "^[0-9]+$"
```

从 url 得到一个 path 列表
``["mirror.iscas.ac.cn", "revyos", "extra", "images", "lpi4a", "20240601", "root-lpi4a-20240601_180941.ext4.zst"]``。
其中 ``repo=1``，故显然 ``repo_name`` 为 ``revyos``，这里由于同一 hostname 下还存在其他镜像（如 oErv），配置中指定了 ``repo_name``；
其中 ``version="-2"``，故 ``version_name`` 为 ``20240601``，该 ``version_name`` 显然符合 ``version_match`` 的定义。

注意 ``repo`` 和 ``version`` 这类字段还可以定义为切片，使用 ``..`` 操作符，如 ``repo="1..-2"`` 得到 ``repo_name`` 为
 ``revyos/extra/images/lpi4a/20240601``。

### 存在的问题

获取到版本列表后，排序是个问题。在 GitHub Release 中，已经以发布时间排序，没有进行二次排序；在镜像源中，则简单以字符串排序的方式做了排序；
而 packages-index 中的版本号符合 Semver 规范，故直接使用 semver 库进行比较排序。

获取到最新版本号后，该版本 Release 中是否包含所需的镜像是另一个问题。当前在跟踪到新版本后，还需要人工二次验证。
在一些镜像中，所有版本的文件名相同；在一些镜像中，版本号被包含在文件名中，通过版本号可以推断文件名；而在另一些镜像中，文件名变更随意，无法推断。

## reimu_mugen_test.py

ruyi 上游版本跟踪和自动化测试调度和报告汇总。

+ [x] Jenkins 配置
+ [x] ruyi 版本获取
+ [x] ruyi-mugen 测试版本更改
+ [x] 测试调度
+ [ ] 自动重测
+ [ ] 报告汇总

注意 jenkins.toml 中 test_platforms 字段的测试平台名称应当与 ruyi-mugen 对应，该名称将被传递给 ruyi-mugen 的脚本。

手动测试

```bash
./reimu_mugen_test.sh
```
