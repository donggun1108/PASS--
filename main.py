import aiohttp
import asyncio
import re
from typing import Dict, Optional
from dataclasses import dataclass
import platform

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@dataclass
class UserInfo:
    name: str
    birth: str
    phone: str

@dataclass
class ApiConfig:
    first_url: str = "https://sign-service.inicis.com/sample/request.php?reqSvcCd=02"
    second_url: str = "https://sa.inicis.com/auth"
    third_url: str = "https://kssa.inicis.com/api/request"
    fourth_url: str = "https://kssa.inicis.com/progress"
    fifth_url: str = "https://kssa.inicis.com/api/status"
    success_url: str = "https://sign-service.inicis.com/sample/result.php"
    fail_url: str = "https://sign-service.inicis.com/sample/result.php"
    logo_url: str = "/resources/images/logo_INICIS.png"

def get_headers() -> Dict[str, str]:
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    }

async def get_user_input() -> UserInfo:
    name = input("이름: ")
    birth = input("생년월일 (예: 20000101): ")
    phone = input("전화번호: ")
    return UserInfo(name=name, birth=birth, phone=phone)

def extract_form_data(html: str, keys: list) -> Dict[str, str]:
    data = {}
    for key in keys:
        match = re.search(rf'name=["\']{key}["\']\s*value=["\']([^"\']+)["\']', html)
        data[key] = match.group(1) if match else "none"
        print(f"{key}: {data[key]}")
    return data

async def first_request(session: aiohttp.ClientSession, config: ApiConfig) -> Optional[Dict[str, str]]:
    headers = get_headers()
    headers.update({"Host": "sign-service.inicis.com", "Referer": "https://sign-service.inicis.com/"})
    
    async with session.get(config.first_url, headers=headers) as response:
        if response.status != 200:
            print(f"첫 요청 실패: 상태 코드 {response.status}")
            return None
        html = await response.text()
        return extract_form_data(html, ["mid", "reqSvcCd", "mTxId", "authHash"])

async def second_request(session: aiohttp.ClientSession, config: ApiConfig, form_data: Dict[str, str], signature_text: str) -> Optional[str]:
    headers = get_headers()
    headers.update({"Host": "sa.inicis.com"})
    
    payload = {
        "mid": form_data["mid"],
        "reqSvcCd": form_data["reqSvcCd"],
        "mTxId": form_data["mTxId"],
        "authHash": form_data["authHash"],
        "flgFixedUser": "N",
        "userName": "",
        "userPhone": "",
        "userBirth": "",
        "userHash": "",
        "directAgency": "",
        "identifier": signature_text,
        "successUrl": config.success_url,
        "failUrl": config.fail_url,
    }
    
    async with session.post(config.second_url, headers=headers, data=payload) as response:
        html = await response.text()
        txId_match = re.search(r'<input[^>]+name=["\']txId["\'][^>]+value=["\']([^"\']+)["\']', html)
        txId = txId_match.group(1) if txId_match else "none"
        print(f"txId: {txId}")
        return txId

async def third_request(session: aiohttp.ClientSession, config: ApiConfig, user: UserInfo, txId: str, signature_text: str) -> Optional[Dict]:
    headers = get_headers()
    headers.update({"Host": "kssa.inicis.com"})
    
    payload = {
        "name": user.name,
        "birth": user.birth,
        "phone": user.phone,
        "all_check": "on",
        "terms_1": "on",
        "terms_2": "on",
        "isDirect": "false",
        "directAgency": "",
        "txId": txId,
        "reqSvcCd": "02",
        "sa_svc_cd": "AF",
        "agency": "PASS",
        "agencyDisplayName": "PASS",
        "myOS": "windows",
        "myBrowser": "chrome",
        "redirectUrl": "",
        "identifier": signature_text,
        "logoUrl": config.logo_url,
        "resultCode": "",
        "resultMsg": "",
        "schemeURL": "",
        "exceptionFlag": "",
        "flgFixedUser": "N",
        "userHash": "",
        "req_url": "https://sign-service.inicis.com/",
        "isBlockBack": "",
        "genderAndNation": "",
        "composite_key": "",
        "trx_key": "",
    }
    
    async with session.post(config.third_url, headers=headers, data=payload) as response:
        try:
            return await response.json()
        except Exception as e:
            print(f"JSON 파싱 실패: {e}")
            print(f"응답: {await response.text()}")
            return None

async def fourth_request(session: aiohttp.ClientSession, config: ApiConfig, user: UserInfo, txId: str, signature_text: str) -> Optional[str]:
    headers = get_headers()
    headers.update({
        "Host": "kssa.inicis.com",
        "Origin": "https://kssa.inicis.com",
        "Referer": "https://kssa.inicis.com/request",
        "Content-Type": "application/x-www-form-urlencoded",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": "\"Google Chrome\";v=\"137\", \"Chromium\";v=\"137\", \"Not/A)Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    })
    
    payload = {
        "name": user.name,
        "birth": user.birth,
        "phone": user.phone,
        "all_check": "on",
        "terms_1": "on",
        "terms_2": "on",
        "isDirect": "false",
        "directAgency": "",
        "txId": txId,
        "reqSvcCd": "02",
        "sa_svc_cd": "AF",
        "agency": "PASS",
        "agencyDisplayName": "PASS",
        "myOS": "windows",
        "myBrowser": "chrome",
        "redirectUrl": "",
        "identifier": signature_text,
        "logoUrl": config.logo_url,
        "resultCode": "0000",
        "resultMsg": "성공",
        "schemeURL": "",
        "exceptionFlag": "",
        "flgFixedUser": "N",
        "userHash": "",
        "req_url": "https://sign-service.inicis.com/",
        "isBlockBack": "",
        "genderAndNation": "",
        "composite_key": "",
        "trx_key": ""
    }
    
    async with session.post(config.fourth_url, headers=headers, data=payload) as response:
        html = await response.text()
        hex_txId_match = re.search(r'var\s+hex_txId\s*=\s*"([^"]+)"', html)
        hex_txId = hex_txId_match.group(1) if hex_txId_match else "none"
        print(f"hex_txId: {hex_txId}")
        return hex_txId

async def five_request(session: aiohttp.ClientSession, config: ApiConfig, user: UserInfo, txId: str, hex_txId: str) -> None:
    headers = get_headers()
    headers.update({
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Host": "kssa.inicis.com",
        "Origin": "https://kssa.inicis.com",
        "Referer": "https://kssa.inicis.com/progress",
        "X-Requested-With": "XMLHttpRequest",
    })
    
    payload = {
        "txId": txId,
        "reqSvcCd": "02",
        "sa_svc_cd": "AF",
        "agency": "PASS",
        "agencyDisplayName": "PASS",
        "name": user.name,
        "phone": user.phone,
        "birth": user.birth,
        "logoUrl": config.logo_url,
        "myOS": "windows",
        "myBrowser": "chrome",
        "resultCode": "",
        "resultMsg": "",
        "redirectUrl": "",
        "gender": "",
        "nation": "",
        "hex_txId": hex_txId,
        "signedData": "",
        "signedData2": "",
        "access_token": ""
    }
    
    async with session.post(config.fifth_url, headers=headers, data=payload) as response:
        try:
            json_response = await response.json()
            print("인증성공" if json_response.get("resultCode") == "0000" else "인증실패")
        except Exception as e:
            print(f"응답코드: {response.status}")
            print(f"응답: {await response.text()}")

async def main():
    signature_text = """
    여기에 전자서명 문구를 작성해보세요!
    """

    config = ApiConfig()
    user = await get_user_input()

    async with aiohttp.ClientSession() as session:
        form_data = await first_request(session, config)
        if not form_data:
            return
        
        txId = await second_request(session, config, form_data, signature_text)
        if not txId:
            return
        
        if not await third_request(session, config, user, txId, signature_text):
            return
        
        hex_txId = await fourth_request(session, config, user, txId, signature_text)
        if not hex_txId:
            return
        
        confirm = input("PASS 인증서 인증 요청을 완료했을 경우 '네'라고 입력해주세요: ")
        if confirm.strip() != "네":
            print("인증 확인이 되지 않아 요청을 중단합니다.")
            return
        
        await five_request(session, config, user, txId, hex_txId)

if __name__ == "__main__":
    asyncio.run(main())
