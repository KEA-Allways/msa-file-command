import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import json
import requests
from starlette.config import Config



config = Config(".env")
REST_API_KEY = config('REST_API_KEY')


app = FastAPI()

#cors설정 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 리액트 앱의 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [내 애플리케이션] > [앱 키] 에서 확인한 REST API 키 값 입력
REST_API_KEY = 'dff46bfdc7a6817dc5799bfd78cdd0a6'

# 이미지 생성하기 요청
def t2i(prompt, negative_prompt):
    r = requests.post(
        'https://api.kakaobrain.com/v2/inference/karlo/t2i',
        json={
            'prompt': prompt,
            'negative_prompt': negative_prompt
        },
        headers={
            'Authorization': f'KakaoAK {REST_API_KEY}',
            'Content-Type': 'application/json'
        }
    )
     
    # 응답 JSON 형식으로 변환
    response = json.loads(r.content)
    return response


@app.post("/generate_image/")
# negative_prompt 값에 기본값을 넣어서 작성안해도 이미지 생성 가능하도록 
def generate_image(prompt: str = Form(...), negative_prompt: Optional[str] = Form(None)):
    # 이미지 생성하기 REST API 호출
     
    print(prompt)
    print(negative_prompt)
    response = t2i(prompt, negative_prompt)
     
    # 여기서 DB에 저장해야됨 
    if response and "images" in response and response["images"]:
        
        #cors 문제 예상 
        result_image_url = response["images"][0]["image"]
        return JSONResponse(content={"image_url": result_image_url})
    else:
        return JSONResponse(content={"message": "이미지 생성 실패. 응답에서 이미지 URL을 찾을 수 없습니다."})

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
