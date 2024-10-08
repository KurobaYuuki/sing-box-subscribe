from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse, Response
from fastapi.templating import Jinja2Templates
from urllib.parse import quote, unquote
import json
import os
import sys
import subprocess
import tempfile
import requests

app = FastAPI()
templates = Jinja2Templates(directory="templates")  # 模板文件在 'templates' 文件夹中

app.secret_key = os.urandom(24)  # 生成一个随机的密钥
data_json = {}
# 使用更具描述性的变量名
DEFAULT_SUBSCRIBES = [
    {"url":"URL","tag":"tag_1","enabled":True,"emoji":1,"subgroup":"","prefix":"","ex-node-name": "","User-Agent":"clashmeta"},
    {"url":"URL","tag":"tag_2","enabled":False,"emoji":1,"subgroup":"","prefix":"","ex-node-name": "","User-Agent":"clashmeta"},
    {"url":"URL","tag":"tag_3","enabled":False,"emoji":1,"subgroup":"","prefix":"","ex-node-name": "","User-Agent":"clashmeta"}
]
DEFAULT_TEMP_JSON_DATA = {
    "subscribes": DEFAULT_SUBSCRIBES,
    "auto_set_outbounds_dns": {"proxy": "", "direct": ""},
    "save_config_path": "./config.json",
    "auto_backup": False,
    "exclude_protocol": "ssr",
    "config_template": "",
    "Only-nodes": False
}
# 设置环境变量 TEMP_JSON_DATA 的初始值
os.environ['TEMP_JSON_DATA'] = json.dumps(DEFAULT_TEMP_JSON_DATA)
data_json['TEMP_JSON_DATA'] = json.dumps(DEFAULT_TEMP_JSON_DATA)

TEMP_DIR = tempfile.gettempdir()  # 获取临时目录

# 获取 TEMP_JSON_DATA 的内容
def get_temp_json_data():
    temp_json_data = os.environ.get('TEMP_JSON_DATA')
    if temp_json_data:
        try:
            return json.loads(temp_json_data)
        except json.JSONDecodeError:
            # 处理无效 JSON 数据
            return DEFAULT_TEMP_JSON_DATA
    return DEFAULT_TEMP_JSON_DATA

# 获取配置模板列表
def get_template_list():
    template_list = []
    config_template_dir = 'config_template'
    if os.path.exists(config_template_dir):
        template_files = os.listdir(config_template_dir)
        template_list = [os.path.splitext(file)[0] for file in template_files if file.endswith('.json')]
        template_list.sort()
    return template_list

# 读取 providers.json 文件
def read_providers_json():
    try:
        with open('providers.json', 'r', encoding='utf-8') as json_file:
            providers_data = json.load(json_file)
        return providers_data
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

# 写入 providers.json 文件
def write_providers_json(data):
    with open('providers.json', 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=4, ensure_ascii=False)

# 首页路由
@app.get("/")
async def index(request: Request):
    template_list = get_template_list()  # 获取模板列表
    template_options = [f"{index + 1}、{template}" for index, template in enumerate(template_list)]
    providers_data = read_providers_json()  # 读取提供者数据
    temp_json_data = get_temp_json_data()  # 获取临时 JSON 数据
    return templates.TemplateResponse("index.html", {"request": request, "template_options": template_options, "providers_data": json.dumps(providers_data, indent=4, ensure_ascii=False), "temp_json_data": json.dumps(temp_json_data, indent=4, ensure_ascii=False)})

# 更新 providers.json 的路由
@app.post("/update_providers")
async def update_providers(providers_data: str = Form(...)):
    try:
        new_providers_data = json.loads(providers_data)  # 解析提供者数据
        write_providers_json(new_providers_data)  # 写入提供者数据
        return JSONResponse(content={"message": "Providers.json 更新成功"}, status_code=200)
    except json.JSONDecodeError:
        return JSONResponse(content={"message": "无效的 JSON 数据"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"message": f"更新 Providers.json 时出错: {str(e)}"}, status_code=500)

# 编辑临时 JSON 数据的路由
@app.post("/edit_temp_json")
async def edit_temp_json(temp_json_data: str = Form(...)):
    try:
        new_temp_json_data = json.loads(temp_json_data)  # 解析临时 JSON 数据
        os.environ['TEMP_JSON_DATA'] = json.dumps(new_temp_json_data, indent=4, ensure_ascii=False)
        return JSONResponse(content={"status": "success"}, status_code=200)
    except json.JSONDecodeError:
        return JSONResponse(content={"status": "error", "message": "无效的 JSON 数据"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

# 配置路由
@app.get("/config/{url:path}")
async def config(url: str, request: Request):
    user_agent = request.headers.get('User-Agent')  # 获取用户代理
    rua_values = os.getenv('RUA')  # 获取 RUA 环境变量
    if rua_values and any(rua_value in user_agent for rua_value in rua_values.split(',')):
        return JSONResponse(content={'status': 'error', 'message': 'block'}, status_code=403)  # 阻止请求
    substrings = os.getenv('STR')  # 获取 STR 环境变量
    if substrings and any(substring in url for substring in substrings.split(',')):
        return JSONResponse(content={'status': 'error', 'message': '填写参数不符合规范'}, status_code=403)  # 参数不符合规范

    # 使用默认的订阅数据
    temp_json_data = get_temp_json_data()
    subscribe = temp_json_data['subscribes'][0]
    subscribe2 = temp_json_data['subscribes'][1]
    subscribe3 = temp_json_data['subscribes'][2]
    query_string = request.query_params  # 获取查询参数
    
    encoded_url = unquote(url)  # 解码 URL

    # 处理查询参数 (简化逻辑)
    for key in ['prefix', 'eps', 'enn']:
        if request.query_params.get(key):
            request.query_params[key] = unquote(request.query_params[key])

    # 处理 file 参数 (简化逻辑)
    if request.query_params.get('file'):
        file_param = request.query_params['file']
        index = file_param.find(":")
        if index != -1:
            next_index = index + 2
            if next_index < len(file_param) and file_param[next_index] != "/":
                request.query_params['file'] = file_param[:next_index-1] + "/" + file_param[next_index-1:]

    # 处理 URL 中的冒号 (简化逻辑)
    index_of_colon = encoded_url.find(":")
    if index_of_colon != -1:
        next_char_index = index_of_colon + 2
        if next_char_index < len(encoded_url) and encoded_url[next_char_index] != "/":
            encoded_url = encoded_url[:next_char_index-1] + "/" + encoded_url[next_char_index-1:]

    # 构建完整的 URL (简化逻辑)
    full_url = f"{encoded_url}?{'&'.join([f'{k}={v}' for k, v in query_string.items()])}" if query_string else encoded_url

    # 获取查询参数
    emoji_param = request.query_params.get('emoji', '')
    file_param = request.query_params.get('file', '')
    tag_param = request.query_params.get('tag', '')
    ua_param = request.query_params.get('ua', '')
    UA_param = request.query_params.get('UA', '')
    pre_param = request.query_params.get('prefix', '')
    eps_param = request.query_params.get('eps', '')
    enn_param = request.query_params.get('enn', '')
    only_param = request.query_params.get('only' ,'')

    # 移除不必要的参数 (简化逻辑)
    params_to_remove = [
        f'&prefix={quote(pre_param)}',
        f'&ua={ua_param}',
        f'&UA={UA_param}',
        f'&file={file_param}',
        f'file={file_param}',
        f'&emoji={emoji_param}',
        f'&tag={tag_param}',
        f'&eps={quote(eps_param)}',
        f'&enn={quote(enn_param)}',
        f'&only={only_param}'
    ]

    full_url = full_url.replace(',', '%2C')  # 替换逗号
    for param in params_to_remove:
        full_url = full_url.replace(param, '')

    full_url = unquote(full_url) 
    if '/api/v4/projects/' in full_url:
        parts = full_url.split('/api/v4/projects/')
        full_url = parts[0] + '/api/v4/projects/' + parts[1].replace('/', '%2F', 1)

    # 处理订阅链接 (简化逻辑)
    url_parts = full_url.split('|')
    if len(url_parts) > 1:
        subscribe['url'] = url_parts[0]
        subscribe['ex-node-name'] = enn_param
        subscribe2['url'] = url_parts[1]
        subscribe2['emoji'] = 1
        subscribe2['enabled'] = True
        subscribe2['ex-node-name'] = enn_param
        if len(url_parts) == 3:
            subscribe3['url'] = url_parts[2]
            subscribe3['enabled'] = True
            subscribe3['ex-node-name'] = enn_param
    if len(url_parts) == 1:
        subscribe['url'] = full_url
        subscribe['emoji'] = int(emoji_param) if emoji_param.isdigit() else subscribe.get('emoji', '')
        subscribe['tag'] = tag_param if tag_param else subscribe.get('tag', '')
        subscribe['prefix'] = pre_param if pre_param else subscribe.get('prefix', '')
        subscribe['ex-node-name'] = enn_param
        subscribe['User-Agent'] = ua_param if ua_param else 'clashmeta'
    temp_json_data['Only-nodes'] = only_param if only_param == 'True' else temp_json_data.get('Only-nodes', '')
    temp_json_data['exclude_protocol'] = eps_param if eps_param else temp_json_data.get('exclude_protocol', '')
    temp_json_data['config_template'] = unquote(file_param) if file_param else temp_json_data.get('config_template', '')

    try:
        selected_template_index = '0'
        if file_param.isdigit():
            temp_json_data['config_template'] = ''
            selected_template_index = str(int(file_param) - 1)
        temp_json_data = json.dumps(json.dumps(temp_json_data, indent=4, ensure_ascii=False), indent=4, ensure_ascii=False)

        response = requests.get(full_url)  # 发送 GET 请求
        subscription_userinfo = response.headers.get('subscription-userinfo')

        # 调用外部脚本
        subprocess.check_call([sys.executable, 'main.py', '--template_index', selected_template_index, '--temp_json_data', temp_json_data])
        CONFIG_FILE_NAME = json.loads(os.environ['TEMP_JSON_DATA']).get("save_config_path", "config.json")
        if CONFIG_FILE_NAME.startswith("./"):
            CONFIG_FILE_NAME = CONFIG_FILE_NAME[2:]
        config_file_path = os.path.join('/tmp/', CONFIG_FILE_NAME)
        if not os.path.exists(config_file_path):
            config_file_path = CONFIG_FILE_NAME
        os.environ['TEMP_JSON_DATA'] = json.dumps(json.loads(data_json['TEMP_JSON_DATA']), indent=4, ensure_ascii=False)

        with open(config_file_path, 'r', encoding='utf-8') as config_file:
            config_content = config_file.read()  # 读取配置文件内容

        response = Response(content=config_content, media_type='text/json; charset=utf-8')
        if subscription_userinfo is not None:
            response.headers['subscription-userinfo'] = subscription_userinfo  # 添加用户信息到响应头
        return response
    except subprocess.CalledProcessError as e:
        os.environ['TEMP_JSON_DATA'] = json.dumps(json.loads(data_json['TEMP_JSON_DATA']), indent=4, ensure_ascii=False)
        return JSONResponse(content={'status': 'error','message': f'执行脚本时出错: {str(e)}'}, status_code=500)
    except Exception as e:
        return JSONResponse(content={'status': 'error', 'message': f'出现错误，请自行排查: {str(e)}'}, status_code=500)

# 生成配置的路由
@app.post("/generate_config")
async def generate_config(template_index: str = Form(...)):
    try:
        if not template_index:
            return JSONResponse(content={"message": "请选一个配置模板"}, status_code=400)
        temp_json_data = json.dumps(os.environ['TEMP_JSON_DATA'], indent=4, ensure_ascii=False)
        subprocess.check_call([sys.executable, 'main.py', '--template_index', template_index, '--temp_json_data', temp_json_data])
        CONFIG_FILE_NAME = json.loads(os.environ['TEMP_JSON_DATA']).get("save_config_path", "config.json")
        if CONFIG_FILE_NAME.startswith("./"):
            CONFIG_FILE_NAME = CONFIG_FILE_NAME[2:]
        config_file_path = os.path.join('/tmp/', CONFIG_FILE_NAME)
        if not os.path.exists(config_file_path):
            config_file_path = CONFIG_FILE_NAME
        os.environ['TEMP_JSON_DATA'] = json.dumps(json.loads(data_json['TEMP_JSON_DATA']), indent=4, ensure_ascii=False)

        with open(config_file_path, 'r', encoding='utf-8') as config_file:
            config_content = config_file.read()  # 读取配置文件内容

        return Response(content=config_content, media_type='text/json; charset=utf-8')
    except subprocess.CalledProcessError as e:
        os.environ['TEMP_JSON_DATA'] = json.dumps(json.loads(data_json['TEMP_JSON_DATA']), indent=4, ensure_ascii=False)
        return JSONResponse(content={'status': 'error','message': f'执行脚本时出错: {str(e)}'}, status_code=500)
    except Exception as e:
        return JSONResponse(content={'status': 'error', 'message': f'出现错误，请自行排查: {str(e)}'}, status_code=500)

# 清除临时 JSON 数据的路由
@app.post("/clear_temp_json_data")
async def clear_temp_json_data():
    try:
        os.environ['TEMP_JSON_DATA'] = json.dumps(DEFAULT_TEMP_JSON_DATA, indent=4, ensure_ascii=False)  # 清除临时 JSON 数据
        return JSONResponse(content={"message": "TEMP_JSON_DATA 清除成功"}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"message": f"清除 TEMP_JSON_DATA 时出错: {str(e)}"}, status_code=500)