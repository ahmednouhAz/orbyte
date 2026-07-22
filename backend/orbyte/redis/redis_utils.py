from orbyte.redis.redis_connector_delete import RedisConnectorDelete
from orbyte.redis.redis_connector_doc_perm_sync import RedisConnectorPermissionSync
from orbyte.redis.redis_connector_prune import RedisConnectorPrune
from orbyte.redis.redis_document_set import RedisDocumentSet
from orbyte.redis.redis_usergroup import RedisUserGroup


def is_fence(key_bytes: bytes) -> bool:
    key_str = key_bytes.decode("utf-8")
    if key_str.startswith(RedisDocumentSet.FENCE_PREFIX):
        return True
    if key_str.startswith(RedisUserGroup.FENCE_PREFIX):
        return True
    if key_str.startswith(RedisConnectorDelete.FENCE_PREFIX):
        return True
    if key_str.startswith(RedisConnectorPrune.FENCE_PREFIX):
        return True
    if key_str.startswith(RedisConnectorPermissionSync.FENCE_PREFIX):
        return True

    return False
