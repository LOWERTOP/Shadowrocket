# iPhone：国内、国外广告拦截与 App 可选模块

此方案分为基础域名拦截和按 App 安装的实验性开屏模块。基础配置可以减少独立广告请求；原生信息流中与正常内容混合返回的广告，不能靠域名规则安全地全部移除。未进行真实 iPhone / 当前 App 版本的编译和流量验证，不宣称达到浏览器内容拦截器的效果。

## 能处理哪些广告

| 场景 | 本次提供的处理 | 边界 |
| --- | --- | --- |
| 国内广告联盟开屏、插屏、信息流 | 精确拒绝两个广告 SDK 主机 | 仅影响使用这些主机且未缓存的广告，也可能影响激励广告；不保证移除界面占位 |
| 淘宝开屏 | 可选模块：两个历史广告/启动营销接口 | 未验证当前版本；不处理所有营销弹窗或商品推荐 |
| 京东开屏 | 可选模块：`home_launchConfig` 请求 | 未验证当前版本；不处理所有红包、活动弹窗 |
| 美团外卖开屏 | 可选模块：`startpicture` 请求 | 不等于美团主 App 全部弹窗；不阻断综合初始化接口 |
| 淘宝、京东、美团瀑布流 | 默认不修改内容 | 广告与商品混合时需要当前版本的响应结构与脱敏样本，不能整段拒绝推荐流 |
| 国外普通网页广告 | 精确拒绝三个 Google 广告主机 | 小范围基础拦截，不承诺完整覆盖 |
| YouTube 视频广告、X 推广帖：原生 App | 未提供去广告规则 | 不阻断 `googlevideo.com`、`youtubei.googleapis.com`、`api.x.com` 等内容接口 |
| YouTube / X：Safari 网页版 | 配合浏览器内容拦截扩展 | 属于浏览器层能力，不由此 Shadowrocket 配置提供；效果随站点更新变化 |

Dia 的[官方说明](https://www.diabrowser.com/security)介绍了浏览器内置广告拦截。这不能等同于 iPhone 原生 App 去广告。AdGuard 的 [iOS App 说明](https://adguard.com/en/support/adguard_for_ios/doesnt_block_ads/in_apps.html)也区分了 App 的域名拦截和 Safari 网页过滤；[YouTube 说明](https://adguard.com/en/article/how-to-block-ads-on-youtube.html)指出域名级过滤无法可靠移除视频广告。[X 广告说明](https://adguard.com/fc/tr/blog/twitter-x-ads-unlabelled-musk.html)说明其 iOS 过滤限于 Safari。

iPhone 上若目标是接近 Dia 的网页去广告，可在 Safari 使用支持内容过滤的扩展，例如 AdGuard 的 Safari 过滤及高级保护，使用网页版 YouTube/X。它与 Shadowrocket 的分流各司其职；此方案不要求同时开启另一个本地 VPN/DNS 过滤服务。原生 App 则需要逐版本验证，不能保证无广告。

## 基础规则：国内与国外分开维护

`lazy_group.conf` 的两个区块均在服务分流前执行，不需要 HTTPS 解密。这里的国内/国外指广告服务类别，不按服务器 IP 判断，也不意味着可以按发起请求的 App 区分广告。

| 区块 | 精确域名 | 可核查依据 |
| --- | --- | --- |
| 国内 `DOMESTIC ADS` | `api-access.pangolin-sdk-toutiao.com` | [社区广告请求端点记录](https://github.com/blackmatrix7/ios_rule_script/blob/0b6897dc17e0c513d25449c935a9694818e32f0c/rewrite/Shadowrocket/AdvertisingLite/AdvertisingLite.sgmodule)、[集成方的穿山甲广告服务披露](https://gateway.laolai.com/web/static/agreement/lldUserprivacy.html) |
| 国内 `DOMESTIC ADS` | `mi.gdt.qq.com` | [社区广点通广告接口记录](https://github.com/blackmatrix7/ios_rule_script/blob/0b6897dc17e0c513d25449c935a9694818e32f0c/rewrite/Shadowrocket/AdvertisingLite/AdvertisingLite.sgmodule) |
| 国外 `OVERSEAS ADS` | `googleads.g.doubleclick.net` | [Google 广告请求端点](https://developers.google.com/publisher-ads-audits/reference/audits/ad-request-from-page-start) |
| 国外 `OVERSEAS ADS` | `pagead2.googlesyndication.com` | [AdSense 广告脚本](https://support.google.com/adsense/answer/9183243?hl=en) |
| 国外 `OVERSEAS ADS` | `securepubads.g.doubleclick.net` | [Google Publisher Tag 广告请求端点](https://developers.google.com/publisher-ads-audits/reference/audits/ad-request-from-page-start) |

核对日期：2026-11-02。基础规则仅匹配完整主机名，不扩大到子域名，不使用关键词、通配符或 IP。国内 SDK 主机是多个 App 共用的广告服务；未对所有 SDK 功能做动态验证，异常时可单独注释对应规则。所有规则均本地维护，不自动订阅大型列表或远程执行脚本。

广告过滤之后，`DOMESTIC APP ROUTING` 为 `taobao.com`、`jd.com`、`360buyimg.com`、`meituan.com`、`meituan.net` 及其子域名设置 `DIRECT`。这是明确的业务域名直连规则，不是按进程代理，也不保证这些 App 使用的每个第三方域名都走直连。其他流量沿用现有服务分流。`lazy.conf`、原有策略组、DNS、重写和 MITM 设置均不变。

## 三个实验性 App 开屏模块

模块文件位于 [`modules/adblocking/`](../modules/adblocking/)，基础配置不自动加载它们，只有手动安装后才可能生效。请按需一次启用一个，以便确认效果和回退。

| 模块 | 允许匹配的接口 | 解密主机 |
| --- | --- | --- |
| [淘宝](../modules/adblocking/taobao-startup.sgmodule) | `/gw/mtop.alibaba.advertisementservice.getadv/版本/`、`/gw/mtop.alibaba.mos.app.homepage.launch/版本/` | `acs.m.taobao.com` |
| [京东](../modules/adblocking/jd-startup.sgmodule) | `/client.action`，查询参数 `functionId=home_launchConfig` | `api.m.jd.com` |
| [美团外卖](../modules/adblocking/meituan-startup.sgmodule) | `/api/v数字/startpicture` | `wmapi.meituan.com` |

端点事实参考 blackmatrix7 的 [Shadowrocket 广告模块](https://github.com/blackmatrix7/ios_rule_script/blob/0b6897dc17e0c513d25449c935a9694818e32f0c/rewrite/Shadowrocket/AdvertisingLite/AdvertisingLite.sgmodule)。参考模块文件自报更新时间为 2025-07-12，故仅作为历史端点线索，不能作为当前 App 仍有效的证据。本次重新限定了完整主机、路径与参数边界，不包含其大列表或远程脚本。返回策略沿用这些端点已记录的 `reject` / `reject-dict` / `reject-200`，但当前客户端是否容忍这些返回仍需实测。

特意不拦截美团 `loadInfo`、`recommends`，也不拦截电商整个首页、商品图 CDN 或支付接口。京东规则允许查询参数调整顺序，但不解析 POST 请求体、编码后的参数名或新版接口；未匹配时保持原行为。没有处理混合信息流的响应脚本，避免用猜测字段删除正常商品。

### iPhone 安装与关闭

1. 保存自己的现有配置备份，导入本分支的 `lazy_group.conf`，选择「使用配置」，全局路由设为「配置」。PR 未合并前，上游发布地址仍是原版。
2. 基础规则无需证书。只需要基础拦截时，到这里即可。
3. 如愿意试验某个 App 的开屏模块：配置 > 模块 > 添加模块（也可新建模块粘贴对应文件）。从本分支下载文件；已有模块与此模块重叠时先关闭重叠项。
4. 这些模块需要针对当前配置[开启 HTTPS 解密](../README.md#https解密)，自行生成、安装和信任自己的证书。文件不包含证书、密钥、自动启用解密或 `skip-cert-verify`。每个模块只追加一个完整主机名；不使用 `*.taobao.com` 等通配符。
5. 解密会覆盖指定主机的 HTTPS 请求，而不只是匹配到的广告 URL。这些主机也承载业务请求；证书固定等机制可能导致 App 连接失败。如登录、下单、支付或浏览异常，先禁用该模块并重新使用配置。不要通过关闭证书校验来绕过问题。

分区关闭基础拦截：注释对应 `BEGIN DOMESTIC ADS` 或 `BEGIN OVERSEAS ADS` 与 END 标记之间的 `DOMAIN` 行，然后重新使用配置。单项误杀只注释对应一行。不要直接改成 `DIRECT`，以免国外广告主机绕过原有分流；注释后会恢复原有匹配。

关闭 App 模块：在「配置 > 模块」禁用对应模块并重新使用配置；不要通过整域放行登录/订单主机覆盖问题。模块规则优先于配置文件规则，排查时同时检查其他已安装模块。

## 维护与更新

- 基础规则和模块随文件版本更新；只刷新原有远程规则集不会更新本地内联规则。远程配置更新会覆盖本地编辑，请保留备份。
- 新增域名需提供广告用途依据、最小复现请求及业务未受影响的记录。共享 API 优先按接口处理；不增加整域、关键词或 IP 拦截来追求覆盖率。
- 信息流响应处理需脱敏样本，明确广告标记、请求路径和 App 版本后再设计；禁止递归删除任何名为 `ad` 的字段、删除整段推荐数据或未经审阅加载远程脚本。
- 版本记录至少包括 iOS、Shadowrocket、App 版本、接口是否命中、冷启动/瀑布流表现、登录与浏览回归、订单/支付页是否正常（无需为测试真实付款）。广告缓存和账号/地区差异可能影响结果。
- 当前版本记录：用户设备为 iPhone；iOS、Shadowrocket 和 App 版本未知；真实请求样本及实机测试均待补充。三个 App 模块保持实验性。不能把静态测试通过解释为实际去广告率。
- 本仓库未提供贡献指南或现有 CI，沿用中文配置说明风格。原有规则来源、策略组及远程列表链接保留。

## 自动化检查及实机验收

在仓库根目录运行（只需 Python 3 和 Git）：

```sh
python3 -m unittest discover -s tests -v
```

本次 8 项 Python 检查通过；另在 macOS Foundation/ICU 上验证了三个模块的 27 个 URL 样例，均通过。可在有 Swift 的 Mac 上复验：

```sh
swift tests/validate_adblocking_icu.swift
```

Foundation 正则兼容检查不等于真实 iPhone 或 Shadowrocket 的导入/运行验证。

自动化检查新增格式、分区、顺序与关闭后的回退；移除新增广告和国内直连块后，应与上游基线 `9ff0cc1` 逐字一致，普通版保持不变。URL 样例检查覆盖广告端点、相似路径、主机伪装、查询参数顺序、正常登录/订单/推荐/图片请求，以及模块解密范围。这是 Python 静态匹配测试，不是 Shadowrocket 原生解析器，不验证远程列表或证明线上兼容。

发布前应在真实 Shadowrocket 导入并编译，确认策略组选项；在「测试规则」中验证五个广告主机命中 `REJECT`，指定国内业务域名命中 `DIRECT`，YouTube/X 等正常服务仍走原服务策略。分别开启模块、冷启动 App、滚动内容和进入登录/下单页，再禁用模块对比日志。未命中历史端点就记录“不适用”，不要扩大拦截范围。仅在取得当前版本验证记录后，才能宣称该版本受支持。
