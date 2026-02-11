# QLApiProxy.py
#青龙脚本查询，新增，更新，删除环境变量接口代理
#
import http.server
import urllib.request
import urllib.parse
import ssl
import json
import sys
import re

# 忽略 SSL 证书
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def get_jdcookie(cokiestr): # 这个是用正则抓jd的ck
    pt_key_match = re.search(r'pt_key=([^;]+)', cokiestr)
    pt_pin_match = re.search(r'pt_pin=([^;]+)', cokiestr)
    pt_key = pt_key_match.group(1) if pt_key_match else None
    pt_pin = pt_pin_match.group(1) if pt_pin_match else None
    if pt_key and pt_pin:
     print(f"pt_key={pt_key}; pt_pin={pt_pin};")
     return f"pt_key={pt_key}; pt_pin={pt_pin};"
    else:
     print("未找到 pt_key 或 pt_pin")
     return cokiestr
def get_token():
    url = "http://127.0.0.1:5700/open/auth/token?client_id=gQN_q8k65zzR&client_secret=ienfCM_2go3s9hDAcoO5x-e2" # 获取token接口
    try:
        with urllib.request.urlopen(url, context=ssl_context) as response:
            data = response.read().decode('utf-8')
            json_data = json.loads(data)
            return json_data['data']['token']
    except Exception as e:
        print(f"❌ 获取 token 失败: {e}", file=sys.stderr)
        return None

def make_api_request(method, path, params=None, body=None):

    # 构造完整 URL
    base_url = "http://127.0.0.1:5700" # 青龙脚本地址
    if params:
        query = urllib.parse.urlencode(params)
        url = f"{base_url}{path}?{query}"
    else:
        url = f"{base_url}{path}"

    token = get_token()
    if not token:
        raise Exception("无法获取认证 token")

    # 准备 body
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        data = json.dumps(body).encode('utf-8')
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, context=ssl_context) as res:
            content = res.read()
            return {
                "status": res.status,
                "content": content,
                "content_type": res.headers.get_content_type()
            }
    except urllib.error.HTTPError as e:
        raise Exception(f"API 返回错误 {e.code}: {e.read().decode()}")

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = dict(urllib.parse.parse_qsl(parsed.query))

        try:
            if path == "/api/envs":
                
                result = make_api_request("GET", "/open/envs", params=query_params)
                
            elif path == "/api/create-env":
            
                name = query_params.get("name")
                value = get_jdcookie(query_params.get("value"))
                remark = query_params.get("remark")
                if not name or not value:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Missing name or value")
                    return
                body =  [{"name": name, "value": value,"remarks":remark}]
                result = make_api_request("POST", "/open/envs", body=body)

            elif path == "/api/update-env":
           
                env_id = query_params.get("id")
                name = query_params.get("name")
                remark = query_params.get("remark")
           
                value = get_jdcookie(query_params.get("value"))
                if not env_id:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Missing id")
                    return
           
                body =  {"id":env_id ,"name":name ,"value": value,"remarks":remark}
                
                if not body:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"No fields to update")
                    return
                
                make_api_request("PUT", f"/open/envs/enable",body=[env_id]) # 使环境变量启用，一般是禁用后才会更新所以更新后会直接启用。如果不用改为启用状态可以注释掉这行代码

                result = make_api_request("PUT", f"/open/envs", body=body)

            elif path == "/api/delete-env":
               
                env_id = query_params.get("id")
                body = [env_id]
                if not env_id:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Missing id")
                    return
                result = make_api_request("DELETE", f"/open/envs", body=body)

            else:
                self.send_response(404)
                self.end_headers()
                return

            self.send_response(result["status"])
            self.send_header("Content-Type", result["content_type"])
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(result["content"])

        except Exception as e:
            print(f"代理错误: {e}", file=sys.stderr)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

if __name__ == "__main__":
    http.server.HTTPServer(("localhost", 8000), Handler).serve_forever()
