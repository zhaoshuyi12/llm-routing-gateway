import hashlib
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from router.models import CacheItem


class SmartCache:
    def __init__(self,max_size:int=1000,default_ttl:int=3600):
        self.cache:Dict[str,CacheItem]={} #字典格式 只能存{str:CacheItem对象}
        self.max_size=max_size
        self.default_ttl=default_ttl
        self.hit_count=0
        self.miss_count=0
        self.lock=threading.RLock () #线程锁，防止多线程同时修改

    def _cleanup(self, cleanup_size: int = 100):
        """
        清理缓存，腾出空间
        策略：删除最老的和最不常用的
        类比：冰箱满了，把最旧和最没人吃的菜扔掉
        """
        if not self.cache:
            return

        print(f"🧹 缓存清理中... (当前大小: {len(self.cache)}/{self.max_size})")

        # 策略1：先删除所有过期的
        expired_keys = [k for k, v in self.cache.items() if v.is_expired()]
        for key in expired_keys:
            del self.cache[key]

        # 如果还不够，继续清理
        if len(self.cache) >= self.max_size:
            # 策略2：删除最不常用的（访问次数最少的）
            sorted_items = sorted(
                self.cache.items(),
                key=lambda x: (x[1].access_count, x[1].created_at)  # 按访问次数，再按创建时间
            )

            # 删除前N个
            to_delete = min(cleanup_size, len(sorted_items))
            for i in range(to_delete):
                key = sorted_items[i][0]
                del self.cache[key]

        print(f"清理完成，剩余缓存: {len(self.cache)}/{self.max_size}")

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        :param key: 缓存键
        :return: 缓存值，如果不存在或已过期则返回None
        类比：从冰箱拿菜
        """
        with self.lock:  # 加锁，保证线程安全
            if key not in self.cache:
                self.miss_count += 1
                return None  # 缓存没有这道菜

            item = self.cache[key]

            # 检查是否过期
            if item.is_expired():
                # 过期了，扔掉
                del self.cache[key]
                self.miss_count += 1
                return None  # 菜坏了，不能吃

            # 更新访问计数
            item.access_count += 1

            # 命中！
            self.hit_count += 1
            return item.values  # 返回菜

    def get_cache(self,key:str):
        with self.lock:
            item=self.cache.get(key)
            if item is None:
                self.miss_count+=1
                return None
            if item.is_expired():
                del self.cache[key]
                self.miss_count+=1
                return None
            item.access_count+=1
            self.hit_count+=1
            return item.values

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存
        :param key: 缓存键
        :param value: 要缓存的值
        :param ttl: 存活时间（秒），不传则用默认值
        类比：把做好的菜放进冰箱
        """
        with self.lock:  # 加锁
            # 如果缓存满了，先清理一些空间
            if len(self.cache) >= self.max_size:
                self._cleanup()

            # 计算过期时间
            expire_at = time.time() + (ttl or self.default_ttl)

            # 创建缓存项
            item = CacheItem(
                values=value,
                expires_at=expire_at,
                created_at=time.time(),
                access_count=0
            )

            # 存储
            self.cache[key] = item

    # ==================== 5. 缓存清理策略 ====================
    def cleanup(self, cleanup_size: int = 100):
        """
        清理缓存，腾出空间
        策略：删除最老的和最不常用的
        类比：冰箱满了，把最旧和最没人吃的菜扔掉
        """
        if not self.cache:
            return

        print(f"🧹 缓存清理中... (当前大小: {len(self.cache)}/{self.max_size})")

        # 策略1：先删除所有过期的
        expired_keys = [k for k, v in self.cache.items() if v.is_expired()]
        for key in expired_keys:
            del self.cache[key]

        # 如果还不够，继续清理
        if len(self.cache) >= self.max_size:
            # 策略2：删除最不常用的（访问次数最少的）
            sorted_items = sorted(
                self.cache.items(),
                key=lambda x: (x[1].access_count, x[1].created_at)  # 按访问次数，再按创建时间
            )

            # 删除前N个
            to_delete = min(cleanup_size, len(sorted_items))
            for i in range(to_delete):
                key = sorted_items[i][0]
                del self.cache[key]

        print(f"🧹 清理完成，剩余缓存: {len(self.cache)}/{self.max_size}")

    # ==================== 6. 辅助方法 ====================
    def delete(self, key: str) -> bool:
        """删除指定缓存"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    def clear(self) -> None:
        """清空所有缓存"""
        with self.lock:
            self.cache.clear()
            print("🧹 缓存已清空")

    def exists(self, key: str) -> bool:
        """检查键是否存在（即使没过期）"""
        with self.lock:
            if key not in self.cache:
                return False
            return not self.cache[key].is_expired()

    def get_with_info(self, key: str) -> Optional[Tuple[Any, Dict]]:
        """
        获取缓存值及其信息
        返回: (值, {命中率, 过期时间等})
        """
        value = self.get(key)
        if value is None:
            return None

        with self.lock:
            item = self.cache[key]
            info = {
                "access_count": item.access_count,
                "created_at": datetime.fromtimestamp(item.created_at).strftime("%H:%M:%S"),
                "expire_at": datetime.fromtimestamp(item.expire_at).strftime("%H:%M:%S"),
                "time_until_expire": item.time_until_expire(),
                "hit_rate": self.get_hit_rate()
            }
            return value, info

    # ==================== 7. 统计信息 ====================
    def get_stats(self) -> Dict:
        """获取缓存统计信息"""
        with self.lock:
            total = self.hit_count + self.miss_count
            hit_rate = self.hit_count / total if total > 0 else 0

            # 统计不同过期时间的项目
            expiring_soon = 0  # 5分钟内过期
            expired = 0
            for item in self.cache.values():
                if item.is_expired():
                    expired += 1
                elif item.time_until_expiration() < 300:  # 5分钟
                    expiring_soon += 1

            return {
                "total_items": len(self.cache),
                "max_size": self.max_size,
                "hit_count": self.hit_count,
                "miss_count": self.miss_count,
                "hit_rate": f"{hit_rate:.2%}",
                "expired_items": expired,
                "expiring_soon": expiring_soon,
                "memory_usage": f"{len(str(self.cache)) / 1024:.2f} KB"  # 粗略估算
            }

    def get_hit_rate(self) -> float:
        """获取命中率"""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0

    # ==================== 8. 高级功能：智能TTL ====================
    def set_with_intent(self, key: str, value: Any, intent: str) -> None:
        """
        根据意图设置不同的TTL
        不同问题类型，缓存时间不同
        """
        intent_ttl = {
            "code": 3600 * 24,  # 代码问题：缓存24小时（代码很少变）
            "general": 3600,  # 普通问题：1小时
            "chinese": 1800,  # 中文问题：30分钟
            "medical": 0,  # 医疗问题：不缓存（安全考虑）
            "emergency": 0,  # 紧急情况：不缓存
            "math": 3600 * 12,  # 数学问题：12小时
        }

        ttl = intent_ttl.get(intent, self.default_ttl)
        print(f"📝 设置缓存TTL: {ttl}秒")

        if ttl > 0:
            self.set(key, value, ttl)
            print(f"📝 根据意图 '{intent}' 设置缓存TTL: {ttl}秒")
        else:
            print(f"⚠️  意图 '{intent}' 不缓存")

    # ==================== 9. 定期清理任务 ====================
    def start_cleanup_task(self, interval: int = 300):
        """
        启动定期清理任务（后台线程）
        :param interval: 清理间隔（秒）
        """

        def cleanup_worker():
            while True:
                time.sleep(interval)
                self._cleanup()

        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()
        print(f"🔧 启动自动清理任务，每 {interval} 秒清理一次")


class CacheKeyGenerator:
    """
    缓存键生成器
    为什么要生成缓存键？因为不同用户的相同问题可以共享缓存
    比如：用户A问"今天天气如何"，用户B也问"今天天气如何"，可以共享答案
    """

    @staticmethod
    def generate_key(query: str, user_id: Optional[str] = None, **kwargs) -> str:
        """
        生成缓存键
        :param query: 用户问题
        :param user_id: 用户ID（可选，不传则所有用户共享）
        :param kwargs: 其他参数（如模型名称、温度等）
        """
        # 构建字符串内容
        parts = [query]

        if user_id:
            parts.append(user_id)  # 包含用户ID，则为用户专属缓存

        # 添加其他参数
        for key, value in sorted(kwargs.items()):
            parts.append(f"{key}={value}")

        # 组合成字符串
        content = ":".join(str(p) for p in parts)

        # 用MD5生成固定长度的键（避免键过长）
        key = hashlib.md5(content.encode()).hexdigest()

        # 添加前缀便于识别
        if user_id:
            return f"user:{user_id[:8]}:{key[:8]}"
        else:
            return f"shared:{key[:8]}"

    @staticmethod
    def generate_model_key(model_name: str, query: str, temperature: float = 0.7) -> str:
        """为模型调用生成专用键"""
        content = f"{model_name}:{query}:{temperature}"
        key = hashlib.md5(content.encode()).hexdigest()
        return f"model:{model_name[:10]}:{key[:8]}"