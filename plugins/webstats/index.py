# coding:utf-8

import sys
import io
import os
import time
import json

sys.path.append(os.getcwd() + "/class/core")
import mw


app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():
    return 'webstats'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


sys.path.append(getPluginDir() + "/class")
from LuaMaker import LuaMaker


def listToLuaFile(path, lists):
    content = LuaMaker.makeLuaTable(lists)
    content = "return " + content
    mw.writeFile(path, content)


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def getConf():
    conf = getServerDir() + "/lua/config.json"
    return conf


def getArgs():
    args = sys.argv[2:]
    tmp = {}
    args_len = len(args)

    if args_len == 1:
        t = args[0].strip('{').strip('}')
        t = t.split(':')
        tmp[t[0]] = t[1]
    elif args_len > 1:
        for i in range(len(args)):
            t = args[i].split(':')
            tmp[t[0]] = t[1]

    return tmp


def checkArgs(data, ck=[]):
    for i in range(len(ck)):
        if not ck[i] in data:
            return (False, mw.returnJson(False, '参数:(' + ck[i] + ')没有!'))
    return (True, mw.returnJson(True, 'ok'))


def luaConf():
    return mw.getServerDir() + '/web_conf/nginx/vhost/webstats.conf'


def status():
    path = luaConf()
    if not os.path.exists(path):
        return 'stop'
    return 'start'


def loadLuaLogFile():
    lua_dir = getServerDir() + "/lua"
    lua_dst = lua_dir + "/webstats_log.lua"

    lua_tpl = getPluginDir() + '/lua/webstats_log.lua'
    content = mw.readFile(lua_tpl)
    content = content.replace('{$SERVER_APP}', getServerDir())
    content = content.replace('{$ROOT_PATH}', mw.getServerDir())
    mw.writeFile(lua_dst, content)


def loadConfigFile():
    lua_dir = getServerDir() + "/lua"
    conf_tpl = getPluginDir() + "/conf/config.json"

    content = mw.readFile(conf_tpl)
    content = json.loads(content)

    dst_conf_json = getServerDir() + "/lua/config.json"
    mw.writeFile(dst_conf_json, json.dumps(content))

    dst_conf_lua = getServerDir() + "/lua/config.lua"
    listToLuaFile(dst_conf_lua, content)


def loadLuaSiteFile():
    lua_dir = getServerDir() + "/lua"

    content = makeSiteConfig()
    for index in range(len(content)):
        pSqliteDb('web_log', content[index]['name'])

    lua_site_json = lua_dir + "/sites.json"
    mw.writeFile(lua_site_json, json.dumps(content))

    # 设置默认列表
    default_json = lua_dir + "/default.json"
    ddata = {}
    dlist = []
    for i in content:
        dlist.append(i["name"])

    dlist.append('unset')
    ddata["list"] = dlist
    if len(ddata["list"]) < 1:
        ddata["default"] = "unset"
    else:
        ddata["default"] = dlist[0]
    mw.writeFile(default_json, json.dumps(ddata))

    lua_site = lua_dir + "/sites.lua"
    listToLuaFile(lua_site, content)


def loadDebugLogFile():
    debug_log = getServerDir() + "/debug.log"
    lua_dir = getServerDir() + "/lua"
    mw.writeFile(debug_log, '')


def pSqliteDb(dbname='web_logs', site_name='unset'):

    db_dir = getServerDir() + '/logs/' + site_name
    if not os.path.exists(db_dir):
        mw.execShell('mkdir -p ' + db_dir)

    name = 'logs'
    file = db_dir + '/' + name + '.db'

    if not os.path.exists(file):
        conn = mw.M(dbname).dbPos(db_dir, name)
        sql = mw.readFile(getPluginDir() + '/conf/init.sql')
        sql_list = sql.split(';')
        for index in range(len(sql_list)):
            conn.execute(sql_list[index], ())
    else:
        conn = mw.M(dbname).dbPos(db_dir, name)
    return conn


def makeSiteConfig():
    siteM = mw.M('sites')
    domainM = mw.M('domain')
    slist = siteM.field('id,name').where(
        'status=?', (1,)).order('id desc').select()

    data = []
    for s in slist:
        tmp = {}
        tmp['name'] = s['name']

        dlist = domainM.field('id,name').where(
            'pid=?', (s['id'],)).order('id desc').select()

        _t = []
        for d in dlist:
            _t.append(d['name'])

        tmp['domains'] = _t
        data.append(tmp)

    return data


def initDreplace():

    service_path = getServerDir()

    pSqliteDb()

    path = luaConf()
    path_tpl = getPluginDir() + '/conf/webstats.conf'
    if not os.path.exists(path):
        content = mw.readFile(path_tpl)
        content = content.replace('{$SERVER_APP}', service_path)
        content = content.replace('{$ROOT_PATH}', mw.getServerDir())
        mw.writeFile(path, content)

    lua_dir = getServerDir() + "/lua"
    if not os.path.exists(lua_dir):
        mw.execShell('mkdir -p ' + lua_dir)

    log_path = getServerDir() + "/logs"
    if not os.path.exists(log_path):
        mw.execShell('mkdir -p ' + log_path)

    loadLuaLogFile()
    loadConfigFile()
    loadLuaSiteFile()
    loadDebugLogFile()

    return 'ok'


def start():
    initDreplace()
    mw.restartWeb()
    return 'ok'


def stop():
    path = luaConf()
    os.remove(path)
    mw.restartWeb()
    return 'ok'


def restart():
    initDreplace()
    return 'ok'


def reload():
    initDreplace()

    loadLuaLogFile()
    loadDebugLogFile()
    mw.restartWeb()
    return 'ok'


def getGlobalConf():
    conf = getConf()
    content = mw.readFile(conf)
    content = json.loads(content)
    return mw.returnJson(True, 'ok', content)


def setGlobalConf():
    args = getArgs()

    conf = getConf()
    content = mw.readFile(conf)
    content = json.loads(content)

    for v in ['record_post_args', 'record_get_403_args']:
        data = checkArgs(args, [v])
        if data[0]:
            rval = False
            if args[v] == "true":
                rval = True
            content['global'][v] = rval

    for v in ['ip_top_num', 'uri_top_num', 'save_day']:
        data = checkArgs(args, [v])
        if data[0]:
            content['global'][v] = int(args[v])

    for v in ['cdn_headers', 'exclude_extension', 'exclude_status', 'exclude_ip']:
        data = checkArgs(args, [v])
        if data[0]:
            content['global'][v] = args[v].split("\\n")

    data = checkArgs(args, ['exclude_url'])
    if data[0]:
        exclude_url = args['exclude_url'].strip(";")
        exclude_url_val = []
        if exclude_url != "":
            exclude_url_list = exclude_url.split(";")
            for i in exclude_url_list:
                t = i.split("|")
                val = {}
                val['mode'] = t[0]
                val['url'] = t[1]
                exclude_url_val.append(val)
        content['global']['exclude_url'] = exclude_url_val

    mw.writeFile(conf, json.dumps(content))
    conf_lua = getServerDir() + "/lua/config.lua"
    listToLuaFile(conf_lua, content)
    mw.restartWeb()
    return mw.returnJson(True, '设置成功')


def getDefaultSite():
    lua_dir = getServerDir() + "/lua"
    path = lua_dir + "/default.json"
    data = mw.readFile(path)
    return mw.returnJson(True, 'OK', json.loads(data))


def setDefaultSite(name):
    lua_dir = getServerDir() + "/lua"
    path = lua_dir + "/default.json"
    data = mw.readFile(path)
    data = json.loads(data)
    data['default'] = name
    mw.writeFile(path, json.dumps(data))
    return mw.returnJson(True, 'OK')


def getLogsList():
    args = getArgs()
    check = checkArgs(args, ['page', 'page_size',
                             'site', 'method', 'status_code', 'spider_type'])
    if not check[0]:
        return check[1]

    page = int(args['page'])
    page_size = int(args['page_size'])
    domain = args['site']
    tojs = args['tojs']
    method = args['method']
    status_code = args['status_code']
    spider_type = args['spider_type']

    setDefaultSite(domain)

    limit = str(page_size) + ' offset ' + str(page_size * (page - 1))
    conn = pSqliteDb('web_logs', domain)

    field = 'time,ip,domain,server_name,method,status_code,request_time,uri,body_length'
    condition = ''
    conn = conn.field(field)

    if method != "all":
        conn = conn.where("method=?", (method,))

    if status_code != "all":
        conn = conn.where("status_code=?", (status_code,))

    if spider_type == "normal":
        pass
    elif spider_type == "only_spider":
        conn = conn.where("is_spider>?", (0,))
    elif spider_type == "no_spider":
        conn = conn.where("is_spider=?", (0,))
    elif int(spider_type) > 0:
        conn = conn.where("is_spider=?", (spider_type,))

    clist = conn.limit(limit).order('time desc').inquiry()

    count_key = "count(*) as num"
    count = conn.field(count_key).limit('').inquiry()
    count = count[0][count_key]

    data = {}
    _page = {}
    _page['count'] = count
    _page['p'] = page
    _page['row'] = page_size
    _page['tojs'] = tojs
    data['page'] = mw.getPage(_page)
    data['data'] = clist

    return mw.returnJson(True, 'ok', data)


if __name__ == "__main__":
    func = sys.argv[1]
    if func == 'status':
        print(status())
    elif func == 'start':
        print(start())
    elif func == 'stop':
        print(stop())
    elif func == 'restart':
        print(restart())
    elif func == 'reload':
        print(reload())
    elif func == 'run_info':
        print(runInfo())
    elif func == 'get_global_conf':
        print(getGlobalConf())
    elif func == 'set_global_conf':
        print(setGlobalConf())
    elif func == 'get_default_site':
        print(getDefaultSite())
    elif func == 'get_logs_list':
        print(getLogsList())
    else:
        print('error')
