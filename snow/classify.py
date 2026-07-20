"""Snow Classification Engine — app category rule database.

This is the SINGLE source of truth for how applications are classified
into the six Snow Core categories. No other module may contain duplicate
classification logic.

Design: "我只分类，不执行" (I only classify, I do not execute)
"""

# ── Application keyword database ──
# Each category maps to space-separated keywords matched against
# .lnk filename and shortcut target path (case-insensitive).
APP_KEYWORDS = {
    "系统": "explorer taskmgr control cmd powershell computer recycle regedit devmgmt diskmgmt compmgmt "
            "sysdm.cpl appwiz.cpl hdwwiz.cpl firewall.cpl mmsys.cpl desk.cpl timedate.cpl "
            "msconfig dxdiag diskmgmt.msc services.msc eventvwr perfmon resmon "
            "windowsdefender securityhealth defender bitdefender malwarebytes "
            "cleanmgr defrag diskpart format chkdsk "
            "控制面板 注册表 设备管理器 任务管理器 资源管理器 磁盘管理 服务 事件查看器 "
            "防火墙 命令行 终端 计算机 回收站 磁盘清理 磁盘碎片整理 杀毒 "
            "360 360safe 360sd 360se 腾讯管家 电脑管家 火绒 huorong"
        ,
    "办公": "winword excel powerpnt acrobat notepad wps word office ppt pdf onenote "
            "outlook mail calendar teams skype zoom webex slack-standalone "
            "evernote onenote note joplin obsidian notion typora markdown "
            "visio project access publisher "
            "企业微信 wxwork wecom 飞书 feishu lark 钉钉 dingtalk "
            "腾讯会议 wemeet tencent-meeting 有道云笔记 youdaonote "
            "百度网盘 baidunetdisk 金山文档 石墨文档 shimo "
            "福昕 foxit phantom 迅雷 thunder xunlei 网盘 pan baidu "
            "chrome msedge firefox opera brave vivaldi tor edge chromium "
            "浏览器 网页 ie internet explorer"
        ,
    "社交": "wechat dingtalk telegram discord qq slack whatsapp "
            "微信 weixin 企业微信 wxwork 飞书 feishu 钉钉 dingtalk "
            "qq 腾讯qq tim telegram discord slack teams "
            "skype zoom webex line messenger signal "
            "微博 weibo 小红书 xiaohongshu red 知乎 zhihu 豆瓣 douban "
            "社交 聊天 通讯 im 即时通讯"
        ,
    "娱乐": "steam epicgames valorant minecraft game lol wow genshin pubg "
            "csgo dota counter-strike overwatch fortnite roblox apex rocket "
            "spotify netflix disney plex kodi vlc potplayer mpv foobar "
            "audacity audition premiere aftereffects davinci capcut "
            "xbox xboxgamebar gamebar nvidia geforce radeon amd adrenalin "
            "雷电 leidian ldplayer dnplayer ldconsole android emulator 模拟器 "
            "网易云 music163 cloudmusic netease 酷狗 kugou 酷我 kuwo "
            "qqmusic qq音乐 腾讯视频 qqlive tencent-video 爱奇艺 iqiyi "
            "哔哩哔哩 bilibili 抖音 douyin 快手 kuaishou 虎牙 huya 斗鱼 douyu "
            "西瓜 xigua youku 优酷 mgtv 芒果 hunantv "
            "播放器 视频 音乐 游戏 游戏平台"
        ,
    "创作": "chatgpt copilot claude codex deepseek cursor gemini perplexity ai "
            "photoshop blender gimp inkscape krita affinity illustrator "
            "vscode sublime textedit atom notepad++ pycharm intellij "
            "webstorm phpstorm rider androidstudio xcode visualstudio "
            "figma sketch invision framer webflow dreamweaver "
            "obs studio streamlabs twitch bandicam shadowplay "
            "unity unreal godot construct gamemaker blender maya 3dsmax "
            "flstudio ableton reaper bitwig cubase logic pro-tools "
            "剪映 jianying capcut 必剪 bijian 快影 "
            "墨刀 modao 蓝湖 lanhu 即时设计 jsdesign mastergo "
            "文心一言 讯飞星火 通义千问 豆包 kimi 元宝 "
            "编程 开发 设计 剪辑 建模 音频 编曲 画图 "
            "code visual studio"
        ,
    "此刻": "wechat dingtalk telegram discord qq slack whatsapp "
            "chrome msedge firefox opera brave vivaldi tor "
            "filezilla winscp putty mstsc remote-desktop "
            "aria2 idm qbittorrent transmission utorrent download "
            "snipaste sharex greenshot lightshot screenshot "
            "everything listary wox powertoys autohotkey "
            "7-zip winrar peazip bandizip rar "
            "keepass bitwarden lastpass 1password vault "
            "terminal windows-terminal conhost hyper alacritty "
            "calibre sumatra pdf-reader drawboard xodo "
            "mouse keyboard touchpad trackpad driver "
            "phone-link yourphone mobile connect "
            "微信 weixin qq 腾讯qq tim 浏览器 截图 下载 压缩 解压 "
            "输入法 sougou sogou 搜狗 密码 远程 连接"
        ,
}


def classify_app(name, target):
    """Classify an application by name/target into one of six categories.

    Args:
        name: The .lnk filename stem (e.g. "Visual Studio Code")
        target: The resolved shortcut target path (may be empty)

    Returns:
        One of: "系统", "办公", "社交", "娱乐", "创作", "此刻"
        Defaults to "系统" if no keyword matches.
    """
    nl = name.lower()
    tl = target.lower()
    for category, keyword_string in APP_KEYWORDS.items():
        for kw in keyword_string.split():
            if kw in nl or kw in tl:
                return category
    return "系统"