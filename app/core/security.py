from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
from .config import settings
from ..models.user import User
from ..core.database import get_session
import bcrypt

# Contexto de hashing de contraseñas con configuración específica para evitar problemas de compatibilidad
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash_direct(password: str) -> str:
    """
    Genera el hash de una contraseña usando bcrypt directamente para evitar problemas de compatibilidad
    """
    # Bcrypt tiene un límite de 72 caracteres para la contraseña
    if len(password) > 72:
        password = password[:72]  # Truncar si es necesario
    
    # Codificar la contraseña a bytes
    password_bytes = password.encode('utf-8')
    
    # Generar el hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Decodificar a string para almacenamiento
    return hashed.decode('utf-8')

# Esquema OAuth2 para obtener token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica que la contraseña plana coincida con la contraseña hasheada
    """
    # Usar bcrypt directamente para evitar problemas de compatibilidad con passlib
    import bcrypt
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def get_password_hash(password: str) -> str:
    """
    Genera el hash de una contraseña
    """
    # Bcrypt tiene un límite de 72 caracteres para la contraseña
    if len(password) > 72:
        password = password[:72]  # Truncar si es necesario
    
    return pwd_context.hash(password)


def authenticate_user(user: User, password: str) -> bool:
    """
    Autentica a un usuario verificando su contraseña
    """
    if not verify_password(password, user.hashed_password):
        return False
    return True


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Crea un token JWT de acceso
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    """
    Obtiene el usuario actual a partir del token JWT
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = session.get(User, int(user_id))
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Obtiene el usuario activo actual
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user