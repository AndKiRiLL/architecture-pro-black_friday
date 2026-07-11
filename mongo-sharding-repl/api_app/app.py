import json
import logging
import os
import time
from typing import List, Optional

import motor.motor_asyncio
from bson import ObjectId
from fastapi import Body, FastAPI, HTTPException, status
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from logmiddleware import RouterLoggingMiddleware, logging_config
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.functional_validators import BeforeValidator
from pymongo import errors
from redis import asyncio as aioredis
from typing_extensions import Annotated

# Configure JSON logging
logging.config.dictConfig(logging_config)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    RouterLoggingMiddleware,
    logger=logger,
)

DATABASE_URL = os.environ["MONGODB_URL"]
DATABASE_NAME = os.environ["MONGODB_DATABASE_NAME"]
REDIS_URL = os.getenv("REDIS_URL", None)


def nocache(*args, **kwargs):
    def decorator(func):
        return func

    return decorator


if REDIS_URL:
    cache = cache
else:
    cache = nocache


client = motor.motor_asyncio.AsyncIOMotorClient(DATABASE_URL)
db = client[DATABASE_NAME]

# Represents an ObjectId field in the database.
# It will be represented as a `str` on the model so that it can be serialized to JSON.
PyObjectId = Annotated[str, BeforeValidator(str)]


@app.on_event("startup")
async def startup():
    if REDIS_URL:
        redis = aioredis.from_url(REDIS_URL, encoding="utf8", decode_responses=True)
        FastAPICache.init(RedisBackend(redis), prefix="api:cache")


class UserModel(BaseModel):
    """
    Container for a single user record.
    """

    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    age: int = Field(...)
    name: str = Field(...)


class UserCollection(BaseModel):
    """
    A container holding a list of `UserModel` instances.
    """

    users: List[UserModel]


@app.get("/")
async def root():
    collection_names = await db.list_collection_names()
    collections = {}
    for collection_name in collection_names:
        collection = db.get_collection(collection_name)
        collections[collection_name] = {
            "documents_count": await collection.count_documents({})
        }
    try:
        replica_status = await client.admin.command("replSetGetStatus")
        replica_status = json.dumps(replica_status, indent=2, default=str)
    except errors.OperationFailure:
        replica_status = "No Replicas"

    topology_description = client.topology_description
    read_preference = client.client_options.read_preference
    topology_type = topology_description.topology_type_name
    replicaset_name = topology_description.replica_set_name

    shards = None
    shards_detail = None
    if topology_type == "Sharded":
        shards_list = await client.admin.command("listShards")
        shards = {}
        shards_detail = {}
        for shard in shards_list.get("shards", {}):
            shard_id = shard["_id"]
            shard_host = shard["host"]
            shards[shard_id] = shard_host
            
            # Получаем информацию о репликах шарда
            shard_info = {
                "host": shard_host,
                "state": shard.get("state", "unknown"),
                "replicas": None
            }
            
            # Парсим хост для получения информации о репликах
            # shard_host выглядит как "shard1/shard1-primary:27018,shard1-secondary1:27018,shard1-secondary2:27018"
            try:
                if "/" in shard_host:
                    replicaset_name, hosts_string = shard_host.split("/", 1)
                    replica_hosts = hosts_string.split(",")
                    
                    replicas_info = []
                    for host in replica_hosts:
                        replicas_info.append({
                            "host": host.strip(),
                            "role": "unknown"  # Будет обновлено ниже
                        })
                    
                    shard_info["replicaset_name"] = replicaset_name
                    shard_info["replicas"] = replicas_info
                    
                    # Пытаемся подключиться к PRIMARY шарда для получения детальной информации
                    try:
                        # Берем первый хост (обычно PRIMARY)
                        primary_host = replica_hosts[0].strip()
                        shard_client = motor.motor_asyncio.AsyncIOMotorClient(f"mongodb://{primary_host}")
                        
                        # Получаем статус репликации
                        try:
                            repl_status = await shard_client.admin.command("replSetGetStatus")
                            
                            # Обновляем информацию о репликах
                            updated_replicas = []
                            for member in repl_status.get("members", []):
                                updated_replicas.append({
                                    "host": member.get("name", "unknown"),
                                    "role": member.get("stateStr", "unknown"),
                                    "health": member.get("health", 0),
                                    "uptime_seconds": member.get("uptime", 0),
                                    "is_primary": member.get("stateStr") == "PRIMARY"
                                })
                            
                            shard_info["replicas"] = updated_replicas
                            shard_info["primary"] = repl_status.get("primary", "unknown")
                            
                        except Exception as e:
                            shard_info["replicas_status"] = f"Could not get replica status: {str(e)}"
                        
                        # Получаем количество документов на этом шарде
                        shard_db = shard_client[DATABASE_NAME]
                        shard_collections = {}
                        total_docs = 0
                        
                        for collection_name in collection_names:
                            try:
                                shard_collection = shard_db.get_collection(collection_name)
                                count = await shard_collection.count_documents({})
                                shard_collections[collection_name] = count
                                total_docs += count
                            except:
                                shard_collections[collection_name] = "error"
                        
                        shard_info["collections"] = shard_collections
                        shard_info["total_documents"] = total_docs
                        
                        shard_client.close()
                        
                    except Exception as e:
                        shard_info["connection_error"] = f"Could not connect to shard: {str(e)}"
                
            except Exception as e:
                shard_info["parse_error"] = str(e)
            
            shards_detail[shard_id] = shard_info

    cache_enabled = False
    if REDIS_URL:
        cache_enabled = FastAPICache.get_enable()

    return {
        "mongo_topology_type": topology_type,
        "mongo_replicaset_name": replicaset_name,
        "mongo_db": DATABASE_NAME,
        "read_preference": str(read_preference),
        "mongo_nodes": client.nodes,
        "mongo_primary_host": client.primary,
        "mongo_secondary_hosts": client.secondaries,
        "mongo_is_primary": client.is_primary,
        "mongo_is_mongos": client.is_mongos,
        "collections": collections,
        "shards": shards,
        "shards_detail": shards_detail,
        "cache_enabled": cache_enabled,
        "status": "OK",
    }


@app.get("/{collection_name}/count")
async def collection_count(collection_name: str):
    collection = db.get_collection(collection_name)
    items_count = await collection.count_documents({})
    # status = await client.admin.command('replSetGetStatus')
    # import ipdb; ipdb.set_trace()
    return {"status": "OK", "mongo_db": DATABASE_NAME, "items_count": items_count}


@app.get(
    "/{collection_name}/users",
    response_description="List all users",
    response_model=UserCollection,
    response_model_by_alias=False,
)
@cache(expire=60 * 1)
async def list_users(collection_name: str):
    """
    List all of the user data in the database.
    The response is unpaginated and limited to 1000 results.
    """
    time.sleep(1)
    collection = db.get_collection(collection_name)
    return UserCollection(users=await collection.find().to_list(1000))


@app.get(
    "/{collection_name}/users/{name}",
    response_description="Get a single user",
    response_model=UserModel,
    response_model_by_alias=False,
)
async def show_user(collection_name: str, name: str):
    """
    Get the record for a specific user, looked up by `name`.
    """

    collection = db.get_collection(collection_name)
    if (user := await collection.find_one({"name": name})) is not None:
        return user

    raise HTTPException(status_code=404, detail=f"User {name} not found")


@app.post(
    "/{collection_name}/users",
    response_description="Add new user",
    response_model=UserModel,
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False,
)
async def create_user(collection_name: str, user: UserModel = Body(...)):
    """
    Insert a new user record.

    A unique `id` will be created and provided in the response.
    """
    collection = db.get_collection(collection_name)
    new_user = await collection.insert_one(
        user.model_dump(by_alias=True, exclude=["id"])
    )
    created_user = await collection.find_one({"_id": new_user.inserted_id})
    return created_user
