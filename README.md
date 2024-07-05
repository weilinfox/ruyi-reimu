# ruyi-reimu

RuyiSDK 测试调度程序

## reimu_check_latest.py

[packages-index](https://github.com/ruyisdk/packages-index/) board image 上游版本跟踪。

+ [x] packages-index 版本列表获取
+ [x] 上游镜像版本列表获取
+ [ ] 上游版本排序
+ [x] 版本比对
+ [x] issue 提交

假设 packages-index 每个配置文件的 url 列表中，只有一个上游 url。维护一个上游 hostname 列表，从每个配置文件的 url 列表中找到这个上游链接，
从该上游 url 中获取版本，再从对应页面获取版本列表。

以 RevyOS 为例，在这个 url
 <https://mirror.iscas.ac.cn/revyos/extra/images/lpi4a/20240601/root-lpi4a-20240601_180941.ext4.zst> 中， 20240601 是版本，
故可以从 <https://mirror.iscas.ac.cn/revyos/extra/images/lpi4a/> 页面获取整个版本列表，使用正则过滤非版本路径。

获取到版本列表后，排序是个问题，当前没有进行二次排序。默认情况下，在 GitHub Release 中，以发布时间排序；在镜像源中，以字符串排序。

获取到最新版本号后，该版本 Release 中是否包含所需的镜像是另一个问题，当前在跟踪到新版本后，还需要人工二次验证。
在一些镜像中，所有版本的文件名相同；在一些镜像中，版本号被包含在文件名中，通过版本号可以推断文件名；而在另一些镜像中，文件名较随意，无法推断。

## reimu_mugen_test.py

ruyi 上游版本跟踪和自动化测试调度和报告汇总。

+ [x] Jenkins 配置
+ [ ] ruyi 版本获取
+ [ ] ruyi-mugen 测试版本更改
+ [ ] 测试调度
+ [ ] 自动重测
+ [ ] 报告汇总
