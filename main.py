import uvicorn
from fastapi  import HTTPException
from fastapi import FastAPI, Form 
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from typing import Optional
import json
import requests
import boto3
from io import BytesIO
import uuid
from pydantic import BaseModel
from pydantic import ValidationError
from dotenv import load_dotenv
from pymongo import MongoClient
from translate import Translator
from elasticapm.contrib.starlette import make_apm_client, ElasticAPM
import py_eureka_client.eureka_client as eureka_client
 
import os
 

#경로 설정 
env_path = r'.env'
load_dotenv()

AWS_ACCESS_KEY_ID=os.getenv("AWS_ACCESS_KEY_ID")
AWS_REGION = os.getenv("AWS_REGION")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
REST_API_KEY = os.getenv("REST_API_KEY")
S3_BUCKET_NAME= os.getenv("S3_BUCKET_NAME")
MONGO_DB_COMMAND_URL=os.getenv("MONGO_DB_COMMAND_URL")
APM_SECRET_TOKEN=os.getenv("APM_SECRET_TOKEN")
APM_SERVER_URL=os.getenv("APM_SERVER_URL")
 

# Elastic APM 설정
apm = make_apm_client({
    'ENVIRONMENT' : 'msa-allways',
    'SERVICE_NAME': 'msa-file-command',
    'SECRET_TOKEN': APM_SECRET_TOKEN,
    'SERVER_URL': APM_SERVER_URL
}) 

app = FastAPI()

app.add_middleware(ElasticAPM, client=apm)
if MONGO_DB_COMMAND_URL is None:
    raise ValueError("MONGO_DB_URL is not set in the environment variables.")
#mongodb 연결 
mongo_client = MongoClient(MONGO_DB_COMMAND_URL)

#db 연결 
db = mongo_client.file

 
 
 
#cors설정 
app.add_middleware(
    CORSMiddleware,
    # allow_origins=["http://localhost:3000"],  # local 리액트 앱의 주소
    ### cloud front로 변경
    allow_origins=["http://gcu-kea-001-front.s3-website.ap-northeast-2.amazonaws.com"],  # dev 리액트 앱의 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [내 애플리케이션] > [앱 키] 에서 확인한 REST API 키 값 입력
 


class FastApiThemeDataRequest(BaseModel):
    themeSeq: int
    imageUrl: str

class FastApiThumbnailDataRequest(BaseModel):
    postSeq: int 
    imageUrl: str 

class FastApiUserProfileImgDataRequest(BaseModel):
    userSeq: int
    imageUrl: str

#s3 접근 
s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_REGION)

# 이미지 생성하기 요청
def t2i(positivePrompt, negativePrompt):
    
    r = requests.post(
        'https://api.kakaobrain.com/v2/inference/karlo/t2i',
        json={
            'prompt': positivePrompt,
            'negative_prompt': negativePrompt
        },
        headers={
            'Authorization': f'KakaoAK {REST_API_KEY}',
            'Content-Type': 'application/json'
        }
    )

    # 응답 JSON 형식으로 변환
    response = json.loads(r.content)
    return response

# 번역 
def translate_text(text, source_language='auto', target_language='en'):
    # Translator 객체 생성
    translator = Translator(from_lang=source_language, to_lang=target_language)

    # 번역 수행
    translation = translator.translate(text)

    # 번역된 텍스트 반환
    return translation

# 유저 프로필 이미지 저장
@app.post("/api/feign/profileImg")
async def saveProfileImgToFastApi(data: FastApiUserProfileImgDataRequest):
    collection = db.user
    try:
        userSeq = data.userSeq
        imageUrl = data.imageUrl

        print(f"Received data - User Seq: {userSeq}, Image URL: {imageUrl}")
        new_user ={"userSeq":userSeq , "imageUrl":imageUrl}
        collection.insert_one(new_user)


        return {"message": "Data received successfully"}

    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {e.errors()}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
        

@app.put("/api/feign/profileImg")
async def receive_userProfileImg(data: FastApiUserProfileImgDataRequest):
    collection = db.user
    result = None 
    try:
        userSeq = data.userSeq
        imageUrl = data.imageUrl

        existing_document = collection.find_one({"userSeq": userSeq})

        if existing_document:
            existing_image_url = existing_document.get("imageUrl", "")

            # 이미지 URL이 다를 경우에만 수정
            if existing_image_url != imageUrl:
                print(f"Updating document for post Seq: {userSeq}")
                result =collection.update_one({"userSeq": userSeq}, {"$set": {"imageUrl": imageUrl}})
                if result.modified_count == 0:
                    raise HTTPException(status_code=404, detail="User not found")

            else:
                print("Image URL is the same. No update needed.")
        else:
            print(f"Document not found for post Seq: {userSeq}")

        
        return {"message": "Profile image updated successfully"}

    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {e.errors()}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    
 

# 테마 생성
@app.post("/api/feign/theme")
async def saveThemeToFastApi(data: FastApiThemeDataRequest):

    #collection 연결 
    collection = db.theme
    print("receive_theme")
     
    
    try:
        themeSeq = data.themeSeq
        imageUrl = data.imageUrl

        print(f"Received data - Theme Seq: {themeSeq}, Image URL: {imageUrl}")
        new_theme={"themeSeq":themeSeq , "imageUrl":imageUrl}
        try:
            result = collection.insert_one(new_theme)
            print(f"Inserted document ID: {result.inserted_id}")
        except Exception as e:
            print(f"Error: {e}")

        return {"message": "Data received successfully"}

    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {e.errors()}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


# 썸네일 생성
@app.post("/api/feign/thumbnail")
async def saveThumbnailToFastApi(data: FastApiThumbnailDataRequest):
    collection = db.thumbnail
    try:
        postSeq = data.postSeq
        imageUrl = data.imageUrl

        print(f"Received data - Theme Seq: {postSeq}, Image URL: {imageUrl}")
        new_theme={"postSeq":postSeq , "imageUrl":imageUrl}
        collection.insert_one(new_theme) 
        

        return {"message": "Data received successfully"}

    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {e.errors()}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# 이미지 생성
@app.post("/api/file/create")
def generate_image(
    positivePrompt: str = Form(...), 
    negativePrompt: Optional[str] = Form(None)):
    positive_keyword =",high quality,Canon EF 24mm F2.8 IS USM"
    negative_keyword = ",low quality, worst quality,mutated,mutation,distorted,deformed,white frame"
    # 이미지 생성하기 REST API 호출
    try:
        # 번역 수행 
        positivePrompt=translate_text(positivePrompt,source_language='ko', target_language='en')
        negativePrompt=translate_text(negativePrompt,source_language='ko', target_language='en')
        
        positivePrompt+=positive_keyword
        negativePrompt+=negative_keyword
        
        s3_key_value = str(uuid.uuid1())
        # 칼로 생성해주는 곳 
        response = t2i(positivePrompt, negativePrompt)
        # 여기서 DB에 저장해야됨 
        if response and "images" in response and response["images"]:
            
            #cors 문제 예상 
            result_image_url = response["images"][0]["image"]
            result_image_content = requests.get(result_image_url).content
            print(result_image_url)
            print(result_image_content)
            image_key = f"{s3_key_value}_image.jpg"  # 이미지 파일의 S3 키, 고유하게 지정할 것
            s3_client.put_object(Body=result_image_content, Bucket=S3_BUCKET_NAME, Key=image_key)
            s3_image_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{image_key}"
            
            return JSONResponse(content={"s3_image_url": s3_image_url})
        
        else:
            return JSONResponse(content={"message": "이미지 생성 실패. 응답에서 이미지 URL을 찾을 수 없습니다."})
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return JSONResponse(content={"message": "서버 내부 오류가 발생했습니다."}, status_code=500)
 
if __name__ == "__main__":
     
     eureka_client.init(eureka_server="http://localhost:8761/eureka",
                    app_name="file-command-service",
                    instance_port=8087,
                    instance_ip="0.0.0.0",
                    )
    
    #dev 
    #  eureka_client.init(eureka_server="http://3.213.139.105:8761/eureka",
    #                 app_name="file-command-service",
    #                 instance_port=8087,
    #                 instance_ip="3.86.230.148",
    #                 instance_host="3.86.230.148"
    #                 )
    

     uvicorn.run(app, host="0.0.0.0", port=8087)
   

 




 
