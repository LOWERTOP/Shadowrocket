# 策略组版的保守广告拦截

`lazy_group.conf` 在现有服务分流之前增加三条 `DOMAIN,完整域名,REJECT` 规则。仅在全局路由为「配置」且请求进入规则匹配时生效，无需新增证书或开启 HTTPS 解密。`lazy.conf`、原有策略组、DNS、重写、MITM 设置和原有分流规则保持不变；其他流量继续使用原有规则。

## 范围与依据

为控制误杀，初始列表仅包含下列广告专用主机，不自动订阅大型第三方广告列表。以下 Google 官方说明用于确认广告用途（核对日期：2026-11-02），规则由本项目手工维护，不是复制的完整过滤列表。

| 精确域名 | 广告用途与依据 |
| --- | --- |
| `googleads.g.doubleclick.net` | [Google 广告请求端点](https://developers.google.com/publisher-ads-audits/reference/audits/ad-request-from-page-start) |
| `pagead2.googlesyndication.com` | [AdSense 广告脚本](https://support.google.com/adsense/answer/9183243?hl=en) |
| `securepubads.g.doubleclick.net` | [Google Publisher Tag 广告请求端点](https://developers.google.com/publisher-ads-audits/reference/audits/ad-request-from-page-start) |

只匹配完整主机名，不扩展到子域名。不使用关键词、通配符、IP 拦截或 `google.com`、`gstatic.com`、`googleapis.com`、`googleusercontent.com` 等共享域名，也不整体拒绝 `doubleclick.net`。没有新增远程资源依赖，因此无需处理新列表下载失败、格式变化或静默扩张。

覆盖范围有意保持较小：不能去除所有开屏广告、同域广告、YouTube 视频广告或页面空白，也不能提供浏览器元素隐藏。广告拦截可能触发反广告拦截检测、影响激励广告及依赖广告的页面流程；“低误杀”不等于没有误杀。

## 使用、更新与恢复

1. 导入包含此修改的 `lazy_group.conf`，选择「使用配置」，全局路由选择「配置」。PR 合并之前，上游发布地址仍为原版。
2. 本地列表随配置文件版本更新。仅更新远程规则集不会更新这些内联规则；使用远程配置的「更新配置」会覆盖本地修改，请先备份自己的调整。
3. 若出现页面或应用异常，在代理日志中确认具体命中的 `DOMAIN` 规则，注释该行（行首加 `#`），再「使用配置」/「编译配置」。请求随后恢复原有分流，不要简单改为 `DIRECT`，以免绕过原服务策略。
4. 临时关闭全部广告拦截：注释 `BEGIN CONSERVATIVE ADBLOCK` 与 `END CONSERVATIVE ADBLOCK` 之间的三条 `DOMAIN` 行，然后重新使用配置。模块规则的优先级高于配置文件规则，应同时检查已安装模块。

## 维护约定

新增域名前应提供广告专用用途的可核查来源及复现请求，排除登录、支付、媒体播放、共享 CDN 等用途。优先增加完整域名；不要因覆盖率而扩大成后缀、关键词或 IP 规则。更新上表和测试样例，保留块标记。收到误杀反馈时记录客户端版本、命中规则和最小复现步骤，优先移除存在争议的主机。

本仓库当前未提供 CONTRIBUTING、PR 模板或 CI；此修改沿用中文注释及手册风格，只修改策略组版。规则直接维护在配置内，便于导入和审阅，无需依赖 fork 的发布地址。

## 验证

在仓库根目录运行（只需 Python 3 和 Git，无第三方依赖）：

```sh
python3 -m unittest discover -s tests -v
```

测试固定比较本次修改的上游基线 `9ff0cc1`：移除新增块后配置应与基线逐字相同，普通版保持不变；同时检查规则格式、去重、位置、完整域名边界和关键服务的未命中样例。这是针对新增规则的静态回归检查，不是完整 Shadowrocket 解析器，也不下载或验证原有第三方远程规则集。以后同步上游时，应审阅差异后更新测试基线。

发布前还应在真实 Shadowrocket 上：

1. 导入配置并编译，确认无格式错误、原有策略组选项仍正常。
2. 使用「测试规则」检查表中三个广告主机命中 `REJECT`，检查 `www.google.com`、`accounts.google.com`、`www.gstatic.com`、`api.openai.com`、`www.youtube.com`、`www.paypal.com` 等仍使用原有策略；远程规则集内容和用户模块会影响实际结果。
3. 验证登录、支付及媒体播放，并对比关闭拦截前后的代理日志。
4. 注释三条规则，重新使用配置，确认广告主机恢复按原配置匹配。

本次提交仅完成自动化静态检查，尚未进行真实客户端编译或实际流量测试。
