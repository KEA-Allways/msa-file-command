import requests
import json
import urllib
from PIL import Image
from starlette.config import Config

# [내 애플리케이션] > [앱 키] 에서 확인한 REST API 키 값 입력
config = Config(".env")
REST_API_KEY = config('REST_API_KEY')

# 이미지 생성하기 요청
def t2i(prompt, negative_prompt):
    r = requests.post(
        'https://api.kakaobrain.com/v2/inference/karlo/t2i',
        json = {
            'prompt': prompt,
            'negative_prompt': negative_prompt
        },
        headers = {
            'Authorization': f'KakaoAK {REST_API_KEY}',
            'Content-Type': 'application/json'
        }
    )
    # 응답 JSON 형식으로 변환
    response = json.loads(r.content)
    return response

# 프롬프트에 사용할 제시어
prompt = "pizza with coke"
negative_prompt = ""

# 이미지 생성하기 REST API 호출
response = t2i(prompt, negative_prompt)

# 응답의 첫 번째 이미지 생성 결과 출력하기

result = Image.open(urllib.request.urlopen(response.get("images")[0].get("image")))
result.show()

