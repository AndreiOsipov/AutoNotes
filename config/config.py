from environs import Env
from dataclasses import dataclass


@dataclass
class JWToken:
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int


@dataclass
class Config:
    jwtoken: JWToken


def load_config(path: str) -> Config:
    env = Env()
    env.read_env(path)
    return Config(
        jwtoken=JWToken(
            secret_key=env("SECRET_KEY"),
            algorithm=env("ALGORITHM"),
            access_token_expire_minutes=env("ACCESS_TOKEN_EXPIRE_MINUTES"),
        )
    )
