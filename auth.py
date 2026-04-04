from fastapi import APIRouter, Header, HTTPException, status
import os, time, jwt
import responses

router = APIRouter()

algorithm = os.getenv("ALGORITHM")
secret_word = os.getenv("SECRET_WORD")
secure_token = os.getenv("SECURE_TOKEN")
expire_token_time = int(os.getenv("EXPIRE_TOKEN_TIME"))

def gen_token(token: str):
    payload = {"sub": token, "exp": int(time.time() + expire_token_time)}
    token_str = jwt.encode(payload, secret_word, algorithm=algorithm)
    return {"token": token_str}

def verify_token(token: str):
    try:
        decoded = jwt.decode(token, secret_word, algorithms=[algorithm])
        if decoded:
            return True
    except: pass
    return False

async def get_current_user(token: str = Header(..., alias="token")):
    if not verify_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    return True

@router.post(
    "/create-token", 
    responses={
        200: {"model": responses.CreateToken}
    }
)
async def create_token_endpoint(token: str = Header(..., alias="token")):
    if token == secure_token:
        token_data = gen_token(token)
        return responses.CreateToken(
            jwt=token_data["token"], 
            exp=int(time.time() + expire_token_time)
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token provided"
    )


# demo
# @router.get("/verify-token")
# async def verify_token_endpoint(token: str = Header(..., alias="token")):
#     if verify_token(token):
#         return {"valid": True}
#     raise HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Invalid or expired token"
#     )